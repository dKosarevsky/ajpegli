# ajpegli Production Roadmap

This repository is intentionally split into small MR-sized branches. Each branch
must preserve `just check` and keep pytest coverage at or above 98%.

## Branch Slices

1. `codex/foundation`
   - Package metadata, `uv`, `just`, `ruff`, `ty`, pytest coverage gate.
   - Stable Python facade for options, metadata, exceptions, and CLI version.
   - Buildable pybind11/CMake `_ajpegli` native extension boundary.

2. `codex/native-error-layer`
   - C++ `jpeg_error_mgr` wrapper with `setjmp`/`longjmp`.
   - Python exception translation for decode/encode errors.
   - Native tests proving invalid JPEG data never exits the process.

3. `codex/vendor-jpegli`
   - Vendored pinned jpegli snapshot or submodule from upstream `libjxl`.
   - Static linking into `_ajpegli`.
   - License files and symbol visibility checks.

4. `codex/core-decode`
   - `jpegli_mem_src`, header validation, `max_pixels`, NumPy allocation.
   - RGB/BGR/L/CMYK/native mode selection for `uint8`.

5. `codex/core-encode`
   - `jpegli_mem_dest`, shape/stride validation, uint8 grayscale/RGB encode.
   - Quality validation, alpha policy, contiguous-copy policy.

6. `codex/dtypes-options`
   - `uint16`, `float32`, `float16`, endianness.
   - distance/psnr/progressive/subsampling/xyb/adaptive quantization.

7. `codex/metadata-info`
   - ICC read/write, raw EXIF/XMP/COM markers, `info()` header path.

8. `codex/wheels-ci-hardening`
   - cibuildwheel matrix, sanitizer jobs, fuzz smoke, wheel dependency checks.
