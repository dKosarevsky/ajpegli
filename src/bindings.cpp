#include <pybind11/pybind11.h>

namespace py = pybind11;

PYBIND11_MODULE(_ajpegli, m) {
  m.doc() = "ajpegli native extension boundary";

  m.def("native_version", []() { return AJPEGLI_VERSION; });
  m.def("jpegli_commit", []() { return AJPEGLI_JPEGLI_COMMIT; });
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

