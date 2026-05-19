#include <pybind11/numpy.h>
#include <pybind11/pybind11.h>

#include <algorithm>
#include <csetjmp>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <limits>
#include <optional>
#include <stdexcept>
#include <string>
#include <vector>

#include "error_mgr.h"
#include "lib/jpegli/encode.h"

namespace py = pybind11;

namespace ajpegli {
namespace {

constexpr JDIMENSION kScanlineBatchSize = 16;
constexpr JDIMENSION kMaxJpegDimension = 65535;
constexpr float kPsnrSearchTolerance = 0.01f;
constexpr float kMinPsnrSearchDistance = 0.1f;
constexpr float kMaxPsnrSearchDistance = 25.0f;

struct GilState {
  PyThreadState* thread_state = nullptr;
  bool released = false;
};

struct EncodeConfig {
  std::optional<int> quality;
  std::optional<float> distance;
  std::optional<float> psnr;
  int progressive;
  std::string subsampling;
  std::optional<std::string> mode;
  std::optional<std::string> dtype;
  bool adaptive_quantization;
  bool xyb;
  bool optimize;
  std::vector<uint8_t> icc_profile;
  std::vector<uint8_t> exif;
  std::vector<uint8_t> xmp;
  std::vector<std::string> comments;
};

struct ImageView {
  const uint8_t* data;
  JDIMENSION width;
  JDIMENSION height;
  int components;
  py::ssize_t row_stride;
  J_COLOR_SPACE color_space;
};

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

void FreeOutput(unsigned char** output_buffer) {
  if (*output_buffer != nullptr) {
    std::free(*output_buffer);
    *output_buffer = nullptr;
  }
}

void ThrowEncodeError(
    jpeg_compress_struct* cinfo,
    ErrorManager* err,
    GilState* gil,
    unsigned char** output_buffer) {
  RestoreGil(gil);
  jpegli_destroy_compress(cinfo);
  FreeOutput(output_buffer);
  throw std::runtime_error("jpegli encode failed: " + err->message);
}

std::optional<std::string> OptionalStringAttr(py::object options, const char* name) {
  py::object value = options.attr(name);
  if (value.is_none()) {
    return std::nullopt;
  }
  return value.cast<std::string>();
}

std::optional<int> OptionalIntAttr(py::object options, const char* name) {
  py::object value = options.attr(name);
  if (value.is_none()) {
    return std::nullopt;
  }
  return value.cast<int>();
}

std::optional<float> OptionalFloatAttr(py::object options, const char* name) {
  py::object value = options.attr(name);
  if (value.is_none()) {
    return std::nullopt;
  }
  return value.cast<float>();
}

std::vector<uint8_t> OptionalBytes(py::object value, const char* name) {
  if (value.is_none()) {
    return {};
  }
  if (!PyBytes_Check(value.ptr())) {
    throw std::runtime_error(std::string(name) + " must be bytes");
  }
  char* data = nullptr;
  Py_ssize_t size = 0;
  if (PyBytes_AsStringAndSize(value.ptr(), &data, &size) != 0) {
    throw py::error_already_set();
  }
  if (size < 0) {
    throw std::runtime_error(std::string(name) + " has invalid size");
  }
  return std::vector<uint8_t>(
      reinterpret_cast<uint8_t*>(data),
      reinterpret_cast<uint8_t*>(data) + static_cast<size_t>(size));
}

std::vector<std::string> CommentStrings(py::object comments) {
  std::vector<std::string> output;
  if (comments.is_none()) {
    return output;
  }
  for (py::handle item : comments) {
    output.push_back(py::str(item).cast<std::string>());
  }
  return output;
}

EncodeConfig MakeEncodeConfig(
    py::object options,
    py::object icc_profile,
    py::object exif,
    py::object xmp,
    py::object comments,
    bool optimize) {
  return EncodeConfig{
      OptionalIntAttr(options, "quality"),
      OptionalFloatAttr(options, "distance"),
      OptionalFloatAttr(options, "psnr"),
      options.attr("progressive").cast<int>(),
      options.attr("subsampling").cast<std::string>(),
      OptionalStringAttr(options, "mode"),
      OptionalStringAttr(options, "dtype"),
      options.attr("adaptive_quantization").cast<bool>(),
      options.attr("xyb").cast<bool>(),
      optimize,
      OptionalBytes(icc_profile, "icc_profile"),
      OptionalBytes(exif, "exif"),
      OptionalBytes(xmp, "xmp"),
      CommentStrings(comments),
  };
}

bool IsUint8Array(const py::buffer_info& info) {
  return info.itemsize == 1 &&
         info.format == py::format_descriptor<uint8_t>::format();
}

JDIMENSION Dimension(py::ssize_t value, const char* name) {
  if (value <= 0) {
    throw std::runtime_error(std::string(name) + " must be positive");
  }
  if (value > static_cast<py::ssize_t>(kMaxJpegDimension)) {
    throw std::runtime_error(std::string(name) + " exceeds JPEG dimension limit");
  }
  return static_cast<JDIMENSION>(value);
}

ImageView MakeImageView(py::array image, const EncodeConfig& config) {
  const py::buffer_info info = image.request();
  if (!IsUint8Array(info)) {
    throw std::runtime_error("only uint8 encode is implemented");
  }
  if (config.dtype.has_value() && *config.dtype != "uint8") {
    throw std::runtime_error("only uint8 encode is implemented");
  }
  if (config.xyb) {
    throw std::runtime_error("xyb encode is not implemented");
  }
  if (config.mode.has_value() && *config.mode == "CMYK") {
    throw std::runtime_error("CMYK encode is not implemented");
  }
  if ((image.flags() & py::array::c_style) == 0) {
    throw std::runtime_error("encode input must be C-contiguous");
  }
  if (info.ndim != 2 && info.ndim != 3) {
    throw std::runtime_error("expected image shape HxW, HxWx1, or HxWx3");
  }

  const JDIMENSION height = Dimension(info.shape[0], "height");
  const JDIMENSION width = Dimension(info.shape[1], "width");
  int components = 1;
  if (info.ndim == 3) {
    components = static_cast<int>(info.shape[2]);
  }
  if (components != 1 && components != 3) {
    throw std::runtime_error("expected image shape HxW, HxWx1, or HxWx3");
  }
  if (config.mode.has_value()) {
    if (*config.mode == "L" && components != 1) {
      throw std::runtime_error("mode does not match image components");
    }
    if (*config.mode == "RGB" && components != 3) {
      throw std::runtime_error("mode does not match image components");
    }
  }
  if (components == 3 && config.subsampling == "gray") {
    throw std::runtime_error("subsampling='gray' requires a grayscale image");
  }

  return ImageView{
      static_cast<const uint8_t*>(info.ptr),
      width,
      height,
      components,
      info.strides[0],
      components == 1 ? JCS_GRAYSCALE : JCS_RGB,
  };
}

void ApplySubsampling(jpeg_compress_struct* cinfo, const EncodeConfig& config) {
  if (cinfo->num_components < 3) {
    return;
  }
  if (config.subsampling == "444") {
    cinfo->comp_info[0].h_samp_factor = 1;
    cinfo->comp_info[0].v_samp_factor = 1;
  } else if (config.subsampling == "422") {
    cinfo->comp_info[0].h_samp_factor = 2;
    cinfo->comp_info[0].v_samp_factor = 1;
  } else if (config.subsampling == "420") {
    cinfo->comp_info[0].h_samp_factor = 2;
    cinfo->comp_info[0].v_samp_factor = 2;
  } else if (config.subsampling == "440") {
    cinfo->comp_info[0].h_samp_factor = 1;
    cinfo->comp_info[0].v_samp_factor = 2;
  } else {
    throw std::runtime_error("unsupported subsampling: " + config.subsampling);
  }
  for (int index = 1; index < cinfo->num_components; ++index) {
    cinfo->comp_info[index].h_samp_factor = 1;
    cinfo->comp_info[index].v_samp_factor = 1;
  }
}

std::vector<uint8_t> PrefixedMarkerData(
    const std::vector<uint8_t>& payload,
    const uint8_t* prefix,
    size_t prefix_size) {
  if (payload.empty()) {
    return {};
  }
  if (payload.size() >= prefix_size &&
      std::memcmp(payload.data(), prefix, prefix_size) == 0) {
    return payload;
  }
  std::vector<uint8_t> data(prefix, prefix + prefix_size);
  data.insert(data.end(), payload.begin(), payload.end());
  return data;
}

void WriteMetadata(jpeg_compress_struct* cinfo, const EncodeConfig& config) {
  if (!config.icc_profile.empty()) {
    jpegli_write_icc_profile(
        cinfo,
        reinterpret_cast<const JOCTET*>(config.icc_profile.data()),
        static_cast<unsigned int>(config.icc_profile.size()));
  }

  constexpr uint8_t kExifPrefix[] = {'E', 'x', 'i', 'f', '\0', '\0'};
  const std::vector<uint8_t> exif =
      PrefixedMarkerData(config.exif, kExifPrefix, sizeof(kExifPrefix));
  if (!exif.empty()) {
    jpegli_write_marker(
        cinfo,
        JPEG_APP0 + 1,
        reinterpret_cast<const JOCTET*>(exif.data()),
        static_cast<unsigned int>(exif.size()));
  }

  constexpr uint8_t kXmpPrefix[] = {
      'h', 't', 't', 'p', ':', '/', '/', 'n', 's', '.', 'a', 'd', 'o', 'b', 'e',
      '.', 'c', 'o', 'm', '/', 'x', 'a', 'p', '/', '1', '.', '0', '/', '\0'};
  const std::vector<uint8_t> xmp =
      PrefixedMarkerData(config.xmp, kXmpPrefix, sizeof(kXmpPrefix));
  if (!xmp.empty()) {
    jpegli_write_marker(
        cinfo,
        JPEG_APP0 + 1,
        reinterpret_cast<const JOCTET*>(xmp.data()),
        static_cast<unsigned int>(xmp.size()));
  }

  for (const std::string& comment : config.comments) {
    jpegli_write_marker(
        cinfo,
        JPEG_COM,
        reinterpret_cast<const JOCTET*>(comment.data()),
        static_cast<unsigned int>(comment.size()));
  }
}

py::bytes Encode(
    py::array image,
    py::object options,
    py::object icc_profile,
    py::object exif,
    py::object xmp,
    py::object comments,
    bool optimize) {
  const EncodeConfig config =
      MakeEncodeConfig(options, icc_profile, exif, xmp, comments, optimize);
  const ImageView view = MakeImageView(image, config);

  jpeg_compress_struct cinfo{};
  ErrorManager err{};
  cinfo.err = SetupErrorManager(&err);
  GilState gil{};
  unsigned char* output_buffer = nullptr;
  unsigned long output_size = 0;  // NOLINT

  if (setjmp(err.jump_buffer)) {
    ThrowEncodeError(&cinfo, &err, &gil, &output_buffer);
  }

  ReleaseGil(&gil);
  jpegli_create_compress(&cinfo);
  jpegli_mem_dest(&cinfo, &output_buffer, &output_size);
  cinfo.image_width = view.width;
  cinfo.image_height = view.height;
  cinfo.input_components = view.components;
  cinfo.in_color_space = view.color_space;
  jpegli_set_defaults(&cinfo);
  ApplySubsampling(&cinfo, config);
  jpegli_enable_adaptive_quantization(
      &cinfo, config.adaptive_quantization ? TRUE : FALSE);
  if (config.quality.has_value()) {
    jpegli_set_quality(&cinfo, *config.quality, TRUE);
  } else if (config.distance.has_value()) {
    jpegli_set_distance(&cinfo, *config.distance, TRUE);
  } else if (config.psnr.has_value()) {
    jpegli_set_psnr(
        &cinfo,
        *config.psnr,
        kPsnrSearchTolerance,
        kMinPsnrSearchDistance,
        kMaxPsnrSearchDistance);
  }
  jpegli_set_progressive_level(&cinfo, config.progressive);
  cinfo.optimize_coding = config.optimize ? TRUE : FALSE;
  jpegli_set_input_format(&cinfo, JPEGLI_TYPE_UINT8, JPEGLI_NATIVE_ENDIAN);
  jpegli_start_compress(&cinfo, TRUE);
  WriteMetadata(&cinfo, config);

  while (cinfo.next_scanline < cinfo.image_height) {
    JSAMPROW rows[kScanlineBatchSize];
    const JDIMENSION remaining = cinfo.image_height - cinfo.next_scanline;
    const JDIMENSION row_count =
        remaining < kScanlineBatchSize ? remaining : kScanlineBatchSize;
    for (JDIMENSION i = 0; i < row_count; ++i) {
      rows[i] = const_cast<JSAMPROW>(
          view.data + static_cast<size_t>(cinfo.next_scanline + i) *
                          static_cast<size_t>(view.row_stride));
    }
    jpegli_write_scanlines(&cinfo, rows, row_count);
  }
  jpegli_finish_compress(&cinfo);
  jpegli_destroy_compress(&cinfo);
  RestoreGil(&gil);

  py::bytes result(reinterpret_cast<const char*>(output_buffer), output_size);
  FreeOutput(&output_buffer);
  return result;
}

}  // namespace

void BindEncode(py::module_& m) {
  m.def(
      "encode",
      &Encode,
      py::arg("image"),
      py::kw_only(),
      py::arg("options"),
      py::arg("icc_profile") = py::none(),
      py::arg("exif") = py::none(),
      py::arg("xmp") = py::none(),
      py::arg("comments") = py::none(),
      py::arg("optimize") = true);
}

}  // namespace ajpegli
