#include <pybind11/pybind11.h>

#include <csetjmp>
#include <stdexcept>
#include <string>

#include "error_mgr.h"
#include "lib/jpegli/decode.h"

namespace py = pybind11;

namespace ajpegli {
namespace {

std::string ToString(py::bytes data) {
  return data;
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

py::object Decode(py::bytes data, py::object /* options */) {
  ProbeJpegHeader(data);
  throw std::runtime_error("jpegli decode image output is not implemented");
}

py::object Info(py::bytes data) {
  ProbeJpegHeader(data);
  throw std::runtime_error("jpegli info output is not implemented");
}

}  // namespace

void BindDecode(py::module_& m) {
  m.def("decode", &Decode, py::arg("data"), py::kw_only(), py::arg("options"));
  m.def("info", &Info, py::arg("data"));
}

}  // namespace ajpegli

