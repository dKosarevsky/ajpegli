# Wheels and publishing

Wheel builds run through cibuildwheel. Pull requests smoke-test the Linux
x86_64 wheel path; tag and manual runs build the full release matrix:

- manylinux x86_64
- manylinux aarch64
- macOS x86_64
- macOS arm64
- Windows x64

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
