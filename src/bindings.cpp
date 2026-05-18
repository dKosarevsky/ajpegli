#include <pybind11/pybind11.h>

#include "lib/jpegli/common.h"

namespace py = pybind11;

namespace ajpegli {
void BindDecode(py::module_& m);
}

bool JpegliLinked() {
  jpeg_error_mgr err;
  return jpegli_std_error(&err) == &err && err.error_exit != nullptr;
}

PYBIND11_MODULE(_ajpegli, m) {
  m.doc() = "ajpegli native extension boundary";

  m.def("native_version", []() { return AJPEGLI_VERSION; });
  m.def("jpegli_commit", []() { return AJPEGLI_JPEGLI_COMMIT; });
  m.def("jpegli_linked", &JpegliLinked);
  ajpegli::BindDecode(m);
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
