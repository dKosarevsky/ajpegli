#include <pybind11/pybind11.h>

#include <jpeglib.h>

namespace py = pybind11;

extern "C" struct jpeg_error_mgr* jpegli_std_error(struct jpeg_error_mgr* err);

bool JpegliLinked() {
  jpeg_error_mgr err;
  return jpegli_std_error(&err) == &err && err.error_exit != nullptr;
}

PYBIND11_MODULE(_ajpegli, m) {
  m.doc() = "ajpegli native extension boundary";

  m.def("native_version", []() { return AJPEGLI_VERSION; });
  m.def("jpegli_commit", []() { return AJPEGLI_JPEGLI_COMMIT; });
  m.def("jpegli_linked", &JpegliLinked);
  m.def("features", []() {
    py::dict features;
    features["uint16"] = false;
    features["float32"] = false;
    features["float16"] = false;
    features["icc"] = false;
    features["exif"] = false;
    features["xyb"] = false;
    features["progressive"] = false;
    return features;
  });
}
