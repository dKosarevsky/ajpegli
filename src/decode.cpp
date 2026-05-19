#include <pybind11/numpy.h>
#include <pybind11/pybind11.h>

#include <csetjmp>
#include <cstdio>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <limits>
#include <memory>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

#include "error_mgr.h"
#include "lib/jpegli/decode.h"

namespace py = pybind11;

namespace ajpegli {
namespace {

constexpr JDIMENSION kScanlineBatchSize = 16;

struct DecodeConfig {
  std::string mode;
  std::string dtype;
  std::string endianness;
  unsigned long max_width;
  unsigned long max_height;
  unsigned long max_pixels;
};

struct GilState {
  PyThreadState* thread_state = nullptr;
  bool released = false;
};

struct BytesView {
  const uint8_t* data;
  size_t size;
};

class BufferView {
 public:
  explicit BufferView(py::handle data) {
    if (PyObject_GetBuffer(data.ptr(), &view_, PyBUF_SIMPLE) != 0) {
      PyErr_Clear();
      throw std::runtime_error("JPEG input must be a contiguous bytes-like buffer");
    }
    acquired_ = true;
    if (view_.len < 0) {
      PyBuffer_Release(&view_);
      acquired_ = false;
      throw std::runtime_error("JPEG input has invalid size");
    }
  }

  BufferView(const BufferView&) = delete;
  BufferView& operator=(const BufferView&) = delete;

  ~BufferView() {
    if (acquired_) {
      PyBuffer_Release(&view_);
    }
  }

  const uint8_t* data() const { return static_cast<const uint8_t*>(view_.buf); }

  size_t size() const { return static_cast<size_t>(view_.len); }

 private:
  Py_buffer view_{};
  bool acquired_ = false;
};

struct MemSource {
  const uint8_t* data;
  unsigned long size;
};

class FileReadError : public std::runtime_error {
 public:
  FileReadError(std::string path, std::string message)
      : std::runtime_error(std::move(message)), path_(std::move(path)) {}

  const std::string& path() const { return path_; }

 private:
  std::string path_;
};

unsigned long PositiveLimit(long value, const char* name) {
  if (value <= 0) {
    throw std::runtime_error(std::string(name) + " must be positive");
  }
  return static_cast<unsigned long>(value);
}

DecodeConfig MakeDecodeConfig(
    const std::string& mode,
    const std::string& dtype,
    long max_pixels,
    long max_width,
    long max_height,
    const std::string& endianness) {
  return DecodeConfig{
      mode,
      dtype,
      endianness,
      PositiveLimit(max_width, "max_width"),
      PositiveLimit(max_height, "max_height"),
      PositiveLimit(max_pixels, "max_pixels"),
  };
}

BytesView GetBytesView(py::bytes data) {
  char* buffer = nullptr;
  Py_ssize_t size = 0;
  if (PyBytes_AsStringAndSize(data.ptr(), &buffer, &size) != 0) {
    throw py::error_already_set();
  }
  return BytesView{
      reinterpret_cast<const uint8_t*>(buffer),
      static_cast<size_t>(size),
  };
}

std::vector<uint8_t> ReadFile(const std::string& path) {
  std::ifstream file(path, std::ios::binary | std::ios::ate);
  if (!file) {
    throw FileReadError(path, "failed to open JPEG file: " + path);
  }

  const std::streamsize size = file.tellg();
  if (size < 0) {
    throw FileReadError(path, "failed to determine JPEG file size: " + path);
  }
  file.seekg(0, std::ios::beg);

  std::vector<uint8_t> input(static_cast<size_t>(size));
  if (size > 0 && !file.read(reinterpret_cast<char*>(input.data()), size)) {
    throw FileReadError(path, "failed to read JPEG file: " + path);
  }
  return input;
}

J_COLOR_SPACE OutputColorSpace(const std::string& mode) {
  if (mode == "RGB") return JCS_RGB;
  if (mode == "BGR") return JCS_EXT_BGR;
  if (mode == "L") return JCS_GRAYSCALE;
  if (mode == "CMYK") return JCS_CMYK;
  if (mode == "native") return JCS_UNKNOWN;
  throw std::runtime_error("unsupported decode mode: " + mode);
}

void ValidateOptions(const DecodeConfig& config) {
  if (config.dtype != "uint8") {
    throw std::runtime_error("only uint8 decode is implemented");
  }
  if (config.endianness != "native") {
    throw std::runtime_error("only native-endian uint8 decode is implemented");
  }
}

void ValidateDimensions(jpeg_decompress_struct* cinfo, const DecodeConfig& config) {
  const auto width = static_cast<unsigned long>(cinfo->image_width);
  const auto height = static_cast<unsigned long>(cinfo->image_height);

  if (width == 0 || height == 0) {
    throw std::runtime_error("JPEG dimensions must be positive");
  }
  if (width > config.max_width || height > config.max_height) {
    throw std::runtime_error("JPEG dimensions exceed configured limits");
  }
  if (height > std::numeric_limits<unsigned long>::max() / width ||
      width * height > config.max_pixels) {
    throw std::runtime_error("JPEG pixel count exceeds max_pixels");
  }
}

void ReleaseGil(GilState* gil) {
  if (!gil->released) {
    gil->thread_state = PyEval_SaveThread();
    gil->released = true;
  }
}

void RestoreGil(GilState* gil) {
  if (gil->released) {
    PyEval_RestoreThread(gil->thread_state);
    gil->thread_state = nullptr;
    gil->released = false;
  }
}

void ThrowDecodeError(jpeg_decompress_struct* cinfo, ErrorManager* err, GilState* gil) {
  RestoreGil(gil);
  jpegli_destroy_decompress(cinfo);
  throw std::runtime_error("jpegli decode failed: " + err->message);
}

void ValidateInputSize(size_t size) {
  if (size > std::numeric_limits<unsigned long>::max()) {
    throw std::runtime_error("JPEG input is too large");
  }
}

using SourceInitializer = void (*)(jpeg_decompress_struct*, void*);

void SetMemSource(jpeg_decompress_struct* cinfo, void* source) {
  const auto* input = static_cast<const MemSource*>(source);
  jpegli_mem_src(
      cinfo,
      reinterpret_cast<const unsigned char*>(input->data),
      input->size);
}

void SetStdioSource(jpeg_decompress_struct* cinfo, void* source) {
  jpegli_stdio_src(cinfo, static_cast<FILE*>(source));
}

FILE* OpenFile(const std::string& path) {
  FILE* file = std::fopen(path.c_str(), "rb");
  if (file == nullptr) {
    throw FileReadError(path, "failed to open JPEG file: " + path);
  }
  return file;
}

py::array DecodeFromSource(
    void* source,
    SourceInitializer source_initializer,
    const DecodeConfig& config) {
  ValidateOptions(config);
  jpeg_decompress_struct cinfo{};
  ErrorManager err{};
  cinfo.err = SetupErrorManager(&err);
  auto gil = std::make_unique<GilState>();

  if (setjmp(err.jump_buffer)) {
    ThrowDecodeError(&cinfo, &err, gil.get());
  }

  ReleaseGil(gil.get());
  jpegli_create_decompress(&cinfo);
  source_initializer(&cinfo, source);
  jpegli_read_header(&cinfo, TRUE);
  RestoreGil(gil.get());

  J_COLOR_SPACE color_space = JCS_UNKNOWN;
  try {
    ValidateDimensions(&cinfo, config);
    color_space = OutputColorSpace(config.mode);
  } catch (...) {
    jpegli_destroy_decompress(&cinfo);
    throw;
  }
  if (color_space != JCS_UNKNOWN) {
    cinfo.out_color_space = color_space;
  }

  if (setjmp(err.jump_buffer)) {
    ThrowDecodeError(&cinfo, &err, gil.get());
  }

  ReleaseGil(gil.get());
  jpegli_set_output_format(&cinfo, JPEGLI_TYPE_UINT8, JPEGLI_NATIVE_ENDIAN);
  jpegli_start_decompress(&cinfo);
  RestoreGil(gil.get());

  const auto height = static_cast<py::ssize_t>(cinfo.output_height);
  const auto width = static_cast<py::ssize_t>(cinfo.output_width);
  const auto components = static_cast<py::ssize_t>(cinfo.out_color_components);
  if (components <= 0) {
    jpegli_destroy_decompress(&cinfo);
    throw std::runtime_error("jpegli produced invalid component count");
  }

  py::array_t<uint8_t> output;
  try {
    output = components == 1 ? py::array_t<uint8_t>({height, width})
                             : py::array_t<uint8_t>({height, width, components});
  } catch (...) {
    jpegli_destroy_decompress(&cinfo);
    throw;
  }
  auto* pixels = static_cast<JSAMPLE*>(output.mutable_data());
  const auto stride = static_cast<size_t>(width * components);

  if (setjmp(err.jump_buffer)) {
    ThrowDecodeError(&cinfo, &err, gil.get());
  }

  ReleaseGil(gil.get());
  while (cinfo.output_scanline < cinfo.output_height) {
    JSAMPROW rows[kScanlineBatchSize];
    const JDIMENSION remaining = cinfo.output_height - cinfo.output_scanline;
    const JDIMENSION row_count =
        remaining < kScanlineBatchSize ? remaining : kScanlineBatchSize;
    for (JDIMENSION i = 0; i < row_count; ++i) {
      rows[i] = pixels + static_cast<size_t>(cinfo.output_scanline + i) * stride;
    }
    jpegli_read_scanlines(&cinfo, rows, row_count);
  }
  jpegli_finish_decompress(&cinfo);
  jpegli_destroy_decompress(&cinfo);
  RestoreGil(gil.get());
  return output;
}

py::array DecodeBuffer(const uint8_t* data, size_t size, const DecodeConfig& config) {
  ValidateInputSize(size);
  MemSource source{
      data,
      static_cast<unsigned long>(size),
  };
  return DecodeFromSource(&source, SetMemSource, config);
}

py::array DecodeStdioFile(FILE* file, const DecodeConfig& config) {
  return DecodeFromSource(file, SetStdioSource, config);
}

bool StartsWith(
    const JOCTET* data,
    unsigned int size,
    const uint8_t* prefix,
    size_t prefix_size) {
  return size >= prefix_size && std::memcmp(data, prefix, prefix_size) == 0;
}

std::string HeaderMode(const jpeg_decompress_struct& cinfo) {
  if (cinfo.num_components == 1 || cinfo.jpeg_color_space == JCS_GRAYSCALE) {
    return "L";
  }
  if (cinfo.num_components == 4 || cinfo.jpeg_color_space == JCS_CMYK ||
      cinfo.jpeg_color_space == JCS_YCCK) {
    return "CMYK";
  }
  if (cinfo.num_components == 3) {
    return "RGB";
  }
  return "native";
}

py::object HeaderSubsampling(const jpeg_decompress_struct& cinfo) {
  if (cinfo.num_components == 1) {
    return py::str("gray");
  }
  if (cinfo.num_components < 3 || cinfo.comp_info == nullptr) {
    return py::none();
  }
  const int h = cinfo.comp_info[0].h_samp_factor;
  const int v = cinfo.comp_info[0].v_samp_factor;
  if (h == 1 && v == 1) return py::str("444");
  if (h == 2 && v == 1) return py::str("422");
  if (h == 2 && v == 2) return py::str("420");
  if (h == 1 && v == 2) return py::str("440");
  return py::none();
}

py::object HeaderDensity(const jpeg_decompress_struct& cinfo) {
  if (!cinfo.saw_JFIF_marker || cinfo.X_density == 0 || cinfo.Y_density == 0) {
    return py::none();
  }
  return py::make_tuple(
      static_cast<int>(cinfo.X_density),
      static_cast<int>(cinfo.Y_density));
}

py::object BuildJpegInfo(const jpeg_decompress_struct& cinfo) {
  constexpr uint8_t kExifPrefix[] = {'E', 'x', 'i', 'f', '\0', '\0'};
  constexpr uint8_t kIccPrefix[] = {
      'I', 'C', 'C', '_', 'P', 'R', 'O', 'F', 'I', 'L', 'E', '\0'};
  constexpr uint8_t kXmpPrefix[] = {
      'h', 't', 't', 'p', ':', '/', '/', 'n', 's', '.', 'a', 'd', 'o', 'b', 'e',
      '.', 'c', 'o', 'm', '/', 'x', 'a', 'p', '/', '1', '.', '0', '/', '\0'};

  bool has_icc = false;
  bool has_exif = false;
  bool has_xmp = false;
  for (jpeg_saved_marker_ptr marker = cinfo.marker_list; marker != nullptr;
       marker = marker->next) {
    if (marker->marker == JPEG_APP0 + 1) {
      has_exif = has_exif ||
                 StartsWith(marker->data, marker->data_length, kExifPrefix,
                            sizeof(kExifPrefix));
      has_xmp = has_xmp ||
                StartsWith(marker->data, marker->data_length, kXmpPrefix,
                           sizeof(kXmpPrefix));
    } else if (marker->marker == JPEG_APP0 + 2) {
      has_icc = has_icc ||
                StartsWith(marker->data, marker->data_length, kIccPrefix,
                           sizeof(kIccPrefix));
    }
  }

  py::object jpeg_info = py::module_::import("ajpegli.metadata").attr("JpegInfo");
  return jpeg_info(
      py::arg("width") = static_cast<int>(cinfo.image_width),
      py::arg("height") = static_cast<int>(cinfo.image_height),
      py::arg("components") = cinfo.num_components,
      py::arg("mode") = HeaderMode(cinfo),
      py::arg("progressive") = static_cast<bool>(cinfo.progressive_mode),
      py::arg("subsampling") = HeaderSubsampling(cinfo),
      py::arg("density") = HeaderDensity(cinfo),
      py::arg("has_icc_profile") = has_icc,
      py::arg("has_exif") = has_exif,
      py::arg("has_xmp") = has_xmp);
}

py::object ReadJpegInfo(py::bytes data) {
  const BytesView input = GetBytesView(data);
  ValidateInputSize(input.size);
  jpeg_decompress_struct cinfo{};
  ErrorManager err{};
  cinfo.err = SetupErrorManager(&err);

  if (setjmp(err.jump_buffer)) {
    jpegli_destroy_decompress(&cinfo);
    throw std::runtime_error("jpegli decode failed: " + err.message);
  }

  jpegli_create_decompress(&cinfo);
  jpegli_mem_src(
      &cinfo,
      reinterpret_cast<const unsigned char*>(input.data),
      static_cast<unsigned long>(input.size));
  jpegli_save_markers(&cinfo, JPEG_APP0 + 1, 0xFFFF);
  jpegli_save_markers(&cinfo, JPEG_APP0 + 2, 0xFFFF);
  jpegli_read_header(&cinfo, TRUE);
  py::object info = BuildJpegInfo(cinfo);
  jpegli_destroy_decompress(&cinfo);
  return info;
}

py::array Decode(
    py::object data,
    const std::string& mode,
    const std::string& dtype,
    long max_pixels,
    long max_width,
    long max_height,
    const std::string& endianness) {
  const DecodeConfig config =
      MakeDecodeConfig(mode, dtype, max_pixels, max_width, max_height, endianness);
  const BufferView input(data);
  return DecodeBuffer(input.data(), input.size(), config);
}

py::array Imread(
    py::str path,
    const std::string& mode,
    const std::string& dtype,
    long max_pixels,
    long max_width,
    long max_height,
    const std::string& endianness) {
  const DecodeConfig config =
      MakeDecodeConfig(mode, dtype, max_pixels, max_width, max_height, endianness);
  const std::string file_path = path;
  std::vector<uint8_t> input;
  try {
    py::gil_scoped_release release;
    input = ReadFile(file_path);
  } catch (const FileReadError& exc) {
    PyErr_SetString(PyExc_FileNotFoundError, exc.what());
    throw py::error_already_set();
  }
  return DecodeBuffer(input.data(), input.size(), config);
}

py::array ImreadStdio(
    py::str path,
    const std::string& mode,
    const std::string& dtype,
    long max_pixels,
    long max_width,
    long max_height,
    const std::string& endianness) {
  const DecodeConfig config =
      MakeDecodeConfig(mode, dtype, max_pixels, max_width, max_height, endianness);
  const std::string file_path = path;
  FILE* file = nullptr;
  try {
    py::gil_scoped_release release;
    file = OpenFile(file_path);
  } catch (const FileReadError& exc) {
    PyErr_SetString(PyExc_FileNotFoundError, exc.what());
    throw py::error_already_set();
  }

  try {
    py::array output = DecodeStdioFile(file, config);
    std::fclose(file);
    return output;
  } catch (...) {
    std::fclose(file);
    throw;
  }
}

py::object Info(py::bytes data) {
  return ReadJpegInfo(data);
}

}  // namespace

void BindDecode(py::module_& m) {
  m.def(
      "decode",
      &Decode,
      py::arg("data"),
      py::kw_only(),
      py::arg("mode"),
      py::arg("dtype"),
      py::arg("max_pixels"),
      py::arg("max_width"),
      py::arg("max_height"),
      py::arg("endianness"));
  m.def(
      "imread",
      &Imread,
      py::arg("path"),
      py::kw_only(),
      py::arg("mode"),
      py::arg("dtype"),
      py::arg("max_pixels"),
      py::arg("max_width"),
      py::arg("max_height"),
      py::arg("endianness"));
  m.def(
      "imread_stdio",
      &ImreadStdio,
      py::arg("path"),
      py::kw_only(),
      py::arg("mode"),
      py::arg("dtype"),
      py::arg("max_pixels"),
      py::arg("max_width"),
      py::arg("max_height"),
      py::arg("endianness"));
  m.def("info", &Info, py::arg("data"));
}

}  // namespace ajpegli
