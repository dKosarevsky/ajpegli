# Releasing

This document is for maintainers. Users should install ajpegli from PyPI:

```bash
pip install ajpegli
```

## Wheels

Wheel builds run through cibuildwheel. Pull requests smoke-test the Linux
x86_64 wheel path; tag and manual runs build the full release matrix:

- manylinux x86_64
- manylinux aarch64
- macOS x86_64
- macOS arm64
- Windows x64

## Release checklist

Before tagging a release:

1. Bump `pyproject.toml` and `CMakeLists.txt` to the next release version.
2. Update `CHANGELOG.md` with user-facing changes and the vendored jpegli
   commit.
3. Run `just check`; it includes `tools.check_versions`, which verifies
   `pyproject.toml`, CMake `PROJECT_VERSION`, installed package metadata, and
   `_ajpegli.native_version()`.
4. Confirm the latest `main` CI run is green.
5. Confirm the benchmark smoke artifact exists for the latest `main` run.
6. For performance claims, update `docs/benchmark-results.md` and
   `docs/dataloader-results.md` from a reproducible run.
7. Create and push an annotated `v*` tag.
8. Watch the `Wheels` workflow until `Publish to PyPI` succeeds.
9. Verify PyPI visibility with `python -m pip index versions ajpegli`.

## Trusted publishing

To publish from GitHub Actions, configure PyPI Trusted Publishing for this
repository first:

1. On TestPyPI, create or claim the `ajpegli` project and add a trusted
   publisher for repository `dKosarevsky/ajpegli`, workflow
   `.github/workflows/wheels.yml`, environment `testpypi`.
2. In GitHub repository settings, create a `testpypi` environment.
3. Run the `Wheels` workflow manually with `publish=testpypi`.
4. On PyPI, add the same trusted publisher with environment `pypi`.
5. In GitHub repository settings, create a protected `pypi` environment.
6. Publish a real release by pushing a `v*` tag, or run the `Wheels` workflow
   manually with `publish=pypi`.

No long-lived PyPI token is required for that flow.
