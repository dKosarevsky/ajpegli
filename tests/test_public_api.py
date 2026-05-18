from __future__ import annotations

import runpy
import string
import subprocess
import sys
from typing import Any

import ajpegli
import ajpegli._native as native
import numpy as np
import pytest
from ajpegli import api
from ajpegli.cli import main
from numpy.typing import NDArray


def test_version_and_jpegli_commit_are_public() -> None:
    assert ajpegli.__version__ == "0.1.0"
    assert isinstance(ajpegli.__jpegli_commit__, str)
    assert len(ajpegli.__jpegli_commit__) == 40
    assert set(ajpegli.__jpegli_commit__) <= set(string.hexdigits)
    assert ajpegli.jpegli_commit() == ajpegli.__jpegli_commit__


def test_features_returns_stable_boolean_map() -> None:
    feature_map = ajpegli.features()
    assert feature_map == {
        "uint16": False,
        "float32": False,
        "float16": False,
        "icc": False,
        "exif": False,
        "xyb": False,
        "progressive": False,
    }
    feature_map["uint16"] = True
    assert ajpegli.features()["uint16"] is False


@pytest.mark.parametrize(
    "name",
    [
        "AjpegliError",
        "DecodeError",
        "EncodeError",
        "InvalidInputError",
        "UnsupportedModeError",
        "MetadataError",
        "SecurityError",
    ],
)
def test_public_exceptions_are_exported(name: str) -> None:
    assert issubclass(getattr(ajpegli, name), ajpegli.AjpegliError)


def test_decode_invalid_input_raises_decode_error(invalid_jpeg_bytes: bytes) -> None:
    with pytest.raises(ajpegli.DecodeError, match="jpegli decode failed"):
        ajpegli.decode(invalid_jpeg_bytes)


def test_encode_rejects_alpha_without_explicit_drop(rgba_uint8: NDArray[np.uint8]) -> None:
    with pytest.raises(ajpegli.InvalidInputError, match="JPEG does not support alpha"):
        ajpegli.encode(rgba_uint8)


def test_encode_drops_alpha_when_requested(rgba_uint8: NDArray[np.uint8]) -> None:
    with pytest.raises(ajpegli.EncodeError, match="native jpegli extension is not available"):
        ajpegli.encode(rgba_uint8, alpha="drop")


def test_encode_rejects_non_numpy_input() -> None:
    with pytest.raises(ajpegli.InvalidInputError, match=r"image must be a numpy\.ndarray"):
        ajpegli.encode([[0, 1], [2, 3]])


def test_encode_accepts_non_contiguous_input_when_copy_allowed(
    rgb_uint8: NDArray[np.uint8],
) -> None:
    transposed = np.swapaxes(rgb_uint8, 0, 1)
    with pytest.raises(ajpegli.EncodeError, match="native jpegli extension is not available"):
        ajpegli.encode(transposed, allow_copy=True)


def test_encode_rejects_non_contiguous_input_when_copy_forbidden(
    rgb_uint8: NDArray[np.uint8],
) -> None:
    transposed = np.swapaxes(rgb_uint8, 0, 1)
    with pytest.raises(
        ajpegli.InvalidInputError,
        match="non-contiguous arrays require allow_copy=True",
    ):
        ajpegli.encode(transposed, allow_copy=False)


def test_info_invalid_input_raises_decode_error(invalid_jpeg_bytes: bytes) -> None:
    with pytest.raises(ajpegli.DecodeError, match="jpegli decode failed"):
        ajpegli.info(invalid_jpeg_bytes)


def test_module_cli_info_without_args_exits_cleanly() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "ajpegli", "--version"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "ajpegli 0.1.0" in result.stdout


def test_decode_accepts_bytearray_then_reaches_native_boundary() -> None:
    with pytest.raises(ajpegli.DecodeError, match="jpegli decode failed"):
        ajpegli.decode(bytearray(b"not a jpeg"))


def test_decode_accepts_memoryview_then_reaches_native_boundary() -> None:
    with pytest.raises(ajpegli.DecodeError, match="jpegli decode failed"):
        ajpegli.decode(memoryview(b"not a jpeg"))


def test_decode_rejects_non_buffer_input() -> None:
    with pytest.raises(ajpegli.DecodeError, match="JPEG input must be bytes-like"):
        ajpegli.decode(object())


@pytest.mark.parametrize(
    "image",
    [
        np.zeros((1,), dtype=np.uint8),
        np.zeros((1, 2, 2, 1), dtype=np.uint8),
        np.zeros((1, 2, 2), dtype=np.uint8),
    ],
)
def test_encode_rejects_invalid_shapes(image: NDArray[np.uint8]) -> None:
    with pytest.raises(ajpegli.InvalidInputError, match="expected image shape"):
        ajpegli.encode(image)


def test_native_fallback_paths_are_stable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(native, "_ext", None)

    assert native.native_available() is False
    assert native.jpegli_linked() is False
    assert native.jpegli_commit() == "unvendored"
    assert native.features()["uint16"] is False
    with pytest.raises(ajpegli.DecodeError, match="native jpegli extension is not available"):
        native.decode(b"not a jpeg")
    with pytest.raises(ajpegli.DecodeError, match="native jpegli extension is not available"):
        native.info(b"not a jpeg")


def test_native_available_reflects_extension_state(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(native, "_ext", object())

    assert native.native_available() is True


def test_native_extension_is_linked_to_jpegli() -> None:
    assert native.jpegli_linked() is True


def test_cli_main_prints_version(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--version"]) == 0
    assert "ajpegli 0.1.0" in capsys.readouterr().out


def test_cli_main_prints_help(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([]) == 0
    assert "usage: ajpegli" in capsys.readouterr().out


def test_module_main_runs_in_process(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["ajpegli", "--version"])
    with pytest.raises(SystemExit) as exc_info:
        runpy.run_module("ajpegli.__main__", run_name="__main__")

    assert exc_info.value.code == 0


def test_public_exception_hierarchy_accepts_value_error() -> None:
    assert issubclass(ajpegli.InvalidInputError, ValueError)


def test_decode_options_are_passed_to_native(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def fake_decode(data: bytes, **kwargs: Any) -> NDArray[np.uint8]:
        captured["args"] = (data, kwargs)
        return np.zeros((1, 1, 3), dtype=np.uint8)

    monkeypatch.setattr(api._native, "decode", fake_decode)

    result = ajpegli.decode(
        b"jpeg",
        mode="BGR",
        dtype="uint16",
        max_pixels=123,
        max_width=45,
        max_height=67,
        endianness="little",
    )

    assert result.shape == (1, 1, 3)
    data, kwargs = captured["args"]
    assert data == b"jpeg"
    assert kwargs == {
        "mode": "BGR",
        "dtype": "uint16",
        "max_pixels": 123,
        "max_width": 45,
        "max_height": 67,
        "endianness": "little",
    }


def test_imread_options_are_passed_to_native(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def fake_imread(path: str, **kwargs: Any) -> NDArray[np.uint8]:
        captured["args"] = (path, kwargs)
        return np.zeros((1, 1, 3), dtype=np.uint8)

    monkeypatch.setattr(api._native, "imread", fake_imread)

    result = ajpegli.imread(
        "image.jpg",
        mode="BGR",
        dtype="uint8",
        max_pixels=123,
        max_width=45,
        max_height=67,
        endianness="native",
    )

    assert result.shape == (1, 1, 3)
    path, kwargs = captured["args"]
    assert path == "image.jpg"
    assert kwargs == {
        "mode": "BGR",
        "dtype": "uint8",
        "max_pixels": 123,
        "max_width": 45,
        "max_height": 67,
        "endianness": "native",
    }


def test_info_accepts_bytearray(monkeypatch: pytest.MonkeyPatch) -> None:
    expected = ajpegli.JpegInfo(
        width=1,
        height=1,
        components=3,
        mode="RGB",
        progressive=False,
        subsampling="444",
        density=None,
        has_icc_profile=False,
        has_exif=False,
        has_xmp=False,
    )

    def fake_info(_data: bytes) -> ajpegli.JpegInfo:
        return expected

    monkeypatch.setattr(api._native, "info", fake_info)

    assert ajpegli.info(bytearray(b"jpeg")) is expected


def test_encode_passes_validated_image_to_native(
    monkeypatch: pytest.MonkeyPatch,
    rgb_uint8: NDArray[np.uint8],
) -> None:
    captured: dict[str, Any] = {}

    def fake_encode(image: NDArray[np.uint8], **kwargs: Any) -> bytes:
        captured["shape"] = image.shape
        captured["kwargs"] = kwargs
        return b"jpeg"

    monkeypatch.setattr(api._native, "encode", fake_encode)

    assert ajpegli.encode(rgb_uint8, quality=90, comments=["ok"]) == b"jpeg"
    assert captured["shape"] == rgb_uint8.shape
    assert captured["kwargs"]["comments"] == ["ok"]
