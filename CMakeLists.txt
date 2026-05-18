cmake_minimum_required(VERSION 3.24)

project(ajpegli VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

find_package(Python REQUIRED COMPONENTS Interpreter Development.Module)
find_package(pybind11 CONFIG REQUIRED)

pybind11_add_module(_ajpegli MODULE
  src/bindings.cpp
)

target_compile_definitions(_ajpegli PRIVATE
  AJPEGLI_VERSION="${PROJECT_VERSION}"
  AJPEGLI_JPEGLI_COMMIT="unvendored"
)

set_target_properties(_ajpegli PROPERTIES
  CXX_VISIBILITY_PRESET hidden
  VISIBILITY_INLINES_HIDDEN ON
)

install(TARGETS _ajpegli DESTINATION ajpegli)

