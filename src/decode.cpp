#include <pybind11/numpy.h>
#include <pybind11/pybind11.h>

#include <csetjmp>
#include <cstdint>
#include <fstream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

#include "error_mgr.h"
#include "lib/jpegli/decode.h"

namespace py = pybind11;

namespace ajpegli {
namespace {

std::string ToString(py::bytes data) {
  return data;
}

std::string GetStringAttr(py::object object, const char* name) {
  return py::str(py::getattr(object, name));
}

long GetLongAttr(py::object object, const char* name) {
  return py::cast<long>(py::getattr(object, name));
}

std::vector<uint8_t> ReadFile(const std::string& path) {
  std::ifstream file(path, std::ios::binary | std::ios::ate);
  if (!file) {
    PyErr_SetFromErrnoWithFilename(PyExc_FileNotFoundError, path.c_str());
    throw py::error_already_set();
  }

  const std::streamsize size = file.tellg();
  if (size < 0) {
    throw std::runtime_error("failed to determine JPEG file size");
  }
  file.seekg(0, std::ios::beg);

  std::vector<uint8_t> input(static_cast<size_t>(size));
  if (size > 0 && !file.read(reinterpret_cast<char*>(input.data()), size)) {
    throw std::runtime_error("failed to read JPEG file");
  }
  return input;
}

J_COLOR_SPACE OutputColorSpace(const std::string& mode) {
  if (mode == "RGB") return JCS_RGB;
  if (mode == "L") return JCS_GRAYSCALE;
  if (mode == "CMYK") return JCS_CMYK;
  if (mode == "native") return JCS_UNKNOWN;
  throw std::runtime_error("unsupported decode mode: " + mode);
}

void ValidateOptions(py::object options) {
  const std::string dtype = GetStringAttr(options, "dtype");
  const std::string endianness = GetStringAttr(options, "endianness");
  if (dtype != "uint8") {
    throw std::runtime_error("only uint8 decode is implemented");
  }
  if (endianness != "native") {
    throw std::runtime_error("only native-endian uint8 decode is implemented");
  }
}

void ValidateDimensions(jpeg_decompress_struct* cinfo, py::object options) {
  const auto width = static_cast<unsigned long>(cinfo->image_width);
  const auto height = static_cast<unsigned long>(cinfo->image_height);
  const auto max_width = static_cast<unsigned long>(GetLongAttr(options, "max_width"));
  const auto max_height = static_cast<unsigned long>(GetLongAttr(options, "max_height"));
  const auto max_pixels = static_cast<unsigned long>(GetLongAttr(options, "max_pixels"));

  if (width == 0 || height == 0) {
    throw std::runtime_error("JPEG dimensions must be positive");
  }
  if (width > max_width || height > max_height) {
    throw std::runtime_error("JPEG dimensions exceed configured limits");
  }
  if (height > std::numeric_limits<unsigned long>::max() / width ||
      width * height > max_pixels) {
    throw std::runtime_error("JPEG pixel count exceeds max_pixels");
  }
}

py::array DecodeBuffer(const uint8_t* data, size_t size, py::object options) {
  ValidateOptions(options);
  const std::string mode = GetStringAttr(options, "mode");
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
      reinterpret_cast<const unsigned char*>(data),
      static_cast<unsigned long>(size));
  jpegli_read_header(&cinfo, TRUE);
  ValidateDimensions(&cinfo, options);
  const J_COLOR_SPACE color_space = OutputColorSpace(mode);
  if (color_space != JCS_UNKNOWN) {
    cinfo.out_color_space = color_space;
  }
  jpegli_set_output_format(&cinfo, JPEGLI_TYPE_UINT8, JPEGLI_NATIVE_ENDIAN);
  jpegli_start_decompress(&cinfo);

  const auto height = static_cast<py::ssize_t>(cinfo.output_height);
  const auto width = static_cast<py::ssize_t>(cinfo.output_width);
  const auto components = static_cast<py::ssize_t>(cinfo.out_color_components);
  if (components <= 0) {
    throw std::runtime_error("jpegli produced invalid component count");
  }

  py::array_t<uint8_t> output =
      components == 1 ? py::array_t<uint8_t>({height, width})
                      : py::array_t<uint8_t>({height, width, components});
  auto* pixels = static_cast<JSAMPLE*>(output.mutable_data());
  const auto stride = static_cast<size_t>(width * components);
  while (cinfo.output_scanline < cinfo.output_height) {
    JSAMPROW row = pixels + static_cast<size_t>(cinfo.output_scanline) * stride;
    jpegli_read_scanlines(&cinfo, &row, 1);
  }
  jpegli_finish_decompress(&cinfo);
  jpegli_destroy_decompress(&cinfo);
  return output;
}

void ProbeJpegHeader(py::bytes data) {
  const std::string input = ToString(data);
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
      reinterpret_cast<const unsigned char*>(input.data()),
      static_cast<unsigned long>(input.size()));
  jpegli_read_header(&cinfo, TRUE);
  jpegli_destroy_decompress(&cinfo);
}

py::array Decode(py::bytes data, py::object options) {
  const std::string input = ToString(data);
  return DecodeBuffer(reinterpret_cast<const uint8_t*>(input.data()), input.size(), options);
}

py::array Imread(py::str path, py::object options) {
  const std::string file_path = path;
  const std::vector<uint8_t> input = ReadFile(file_path);
  return DecodeBuffer(input.data(), input.size(), options);
}

py::object Info(py::bytes data) {
  ProbeJpegHeader(data);
  throw std::runtime_error("jpegli info output is not implemented");
}

}  // namespace

void BindDecode(py::module_& m) {
  m.def("decode", &Decode, py::arg("data"), py::kw_only(), py::arg("options"));
  m.def("imread", &Imread, py::arg("path"), py::kw_only(), py::arg("options"));
  m.def("info", &Info, py::arg("data"));
}

}  // namespace ajpegli
