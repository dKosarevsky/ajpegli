# jpegli vendoring

The production package will vendor a pinned jpegli snapshot from upstream
`libjxl` and link it statically into `ajpegli._ajpegli`.

This foundation branch keeps the native extension boundary buildable before the
vendored source lands. The CMake target deliberately does not link a system
`libjpeg` or expose libjpeg-compatible symbols.

