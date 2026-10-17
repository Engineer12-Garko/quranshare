import pytest
from fastapi import HTTPException

from app.services.google_drive import _parse_range, _prefetch_first_chunk


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        ("bytes=0-9", (0, 9)),
        ("bytes=5-", (5, 99)),
        ("bytes=-10", (90, 99)),
        ("bytes=-500", (0, 99)),
        ("BYTES=10-200", (10, 99)),
    ],
)
def test_parse_supported_byte_ranges(header, expected):
    assert _parse_range(header, 100) == expected


@pytest.mark.parametrize(
    "header",
    ["items=0-9", "bytes=100-", "bytes=9-2", "bytes=-0", "bytes=0-1,4-5"],
)
def test_rejects_invalid_or_unsatisfiable_byte_ranges(header):
    with pytest.raises(HTTPException) as exc:
        _parse_range(header, 100)
    assert exc.value.status_code == 416
    assert exc.value.headers["Content-Range"] == "bytes */100"


def test_rejects_ranges_for_empty_file():
    with pytest.raises(HTTPException) as exc:
        _parse_range("bytes=0-", 0)
    assert exc.value.status_code == 416


def test_prefetch_keeps_first_chunk_and_remaining_stream_order():
    chunks = _prefetch_first_chunk(iter([b"first", b"second"]))
    assert list(chunks) == [b"first", b"second"]


def test_upstream_stream_failure_is_returned_as_gateway_error_before_streaming():
    def failed_stream():
        raise ConnectionError("upstream unavailable")
        yield b"unreachable"

    with pytest.raises(HTTPException) as exc:
        _prefetch_first_chunk(failed_stream())
    assert exc.value.status_code == 502
