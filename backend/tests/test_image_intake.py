"""Specifications for image_intake, the gate every uploaded recipe photo
passes through before reaching the vision model.

Its job is twofold: refuse what shouldn't be sent at all (too many files,
wrong format, oversized), and normalise what is accepted into modest JPEG
bytes — a phone photo is 3-5 MB and base64 inflates it by a third, so a
batch of raw uploads would be tens of megabytes on the wire for no gain
(the model downscales internally anyway).
"""

import io

import pytest
from PIL import Image

from app.services.image_intake import (
    MAX_BYTES_PER_IMAGE,
    MAX_IMAGES,
    MAX_LONG_EDGE_PIXELS,
    ImageTooLargeError,
    NoImagesProvidedError,
    TooManyImagesError,
    UnsupportedImageTypeError,
    prepare_images,
)


def _encoded(width: int, height: int, image_format: str = "JPEG", mode: str = "RGB") -> bytes:
    """An in-memory image of the given size, as uploaded bytes."""
    buffer = io.BytesIO()
    Image.new(mode, (width, height), color="white").save(buffer, format=image_format)
    return buffer.getvalue()


def _size_of(image_bytes: bytes) -> tuple[int, int]:
    return Image.open(io.BytesIO(image_bytes)).size


def test_given_a_jpeg_photo_when_prepared_then_it_comes_back_as_decodable_jpeg_bytes() -> None:
    """Given a single JPEG upload, when prepared, then one JPEG image comes
    back, ready to be base64-encoded into a vision request."""
    prepared = prepare_images([("image/jpeg", _encoded(800, 600))])

    assert len(prepared) == 1
    assert Image.open(io.BytesIO(prepared[0])).format == "JPEG"


def test_given_several_photos_when_prepared_then_their_order_is_preserved() -> None:
    """Given the pages of one recipe uploaded in order, when prepared, then
    they come back in the same order — the vision model reads them as page
    1, page 2, and swapping them would scramble the recipe."""
    uploads = [
        ("image/jpeg", _encoded(200, 100)),
        ("image/jpeg", _encoded(300, 100)),
        ("image/jpeg", _encoded(400, 100)),
    ]

    prepared = prepare_images(uploads)

    assert [_size_of(image)[0] for image in prepared] == [200, 300, 400]


def test_given_a_photo_larger_than_the_limit_when_prepared_then_it_is_downscaled() -> None:
    """Given a full-resolution phone photo, when prepared, then its longest
    edge is capped and the aspect ratio is kept."""
    prepared = prepare_images([("image/jpeg", _encoded(4000, 3000))])

    width, height = _size_of(prepared[0])
    assert width == MAX_LONG_EDGE_PIXELS
    assert height == pytest.approx(MAX_LONG_EDGE_PIXELS * 3 / 4, abs=1)


def test_given_a_photo_smaller_than_the_limit_when_prepared_then_it_is_not_upscaled() -> None:
    """Given an already-small image, when prepared, then it keeps its size —
    upscaling would only add bytes without adding legible detail."""
    prepared = prepare_images([("image/jpeg", _encoded(640, 480))])

    assert _size_of(prepared[0]) == (640, 480)


def test_given_a_png_with_transparency_when_prepared_then_it_becomes_an_opaque_jpeg() -> None:
    """Given a screenshot saved as PNG with an alpha channel, when prepared,
    then it is converted to JPEG — which has no alpha, so the conversion
    must be explicit rather than blowing up on save."""
    prepared = prepare_images([("image/png", _encoded(300, 300, image_format="PNG", mode="RGBA"))])

    assert Image.open(io.BytesIO(prepared[0])).mode == "RGB"


def test_given_no_files_at_all_when_preparing_then_it_is_rejected() -> None:
    """Given a submission with no files, when preparing, then it is rejected
    rather than reaching the AI with nothing to read."""
    with pytest.raises(NoImagesProvidedError):
        prepare_images([])


def test_given_more_files_than_allowed_when_preparing_then_it_is_rejected() -> None:
    """Given more images than a single recipe can plausibly need, when
    preparing, then it is rejected — each one costs tokens and latency."""
    uploads = [("image/jpeg", _encoded(100, 100))] * (MAX_IMAGES + 1)

    with pytest.raises(TooManyImagesError):
        prepare_images(uploads)


def test_given_a_file_that_is_not_an_image_when_preparing_then_it_is_rejected() -> None:
    """Given a PDF (a plausible mistake when scanning a cookbook), when
    preparing, then it is rejected by content type."""
    with pytest.raises(UnsupportedImageTypeError):
        prepare_images([("application/pdf", b"%PDF-1.4")])


def test_given_bytes_that_do_not_decode_when_preparing_then_it_is_rejected() -> None:
    """Given bytes that claim to be a JPEG but aren't, when preparing, then
    it is rejected — the declared content type is client-supplied and can't
    be trusted on its own."""
    with pytest.raises(UnsupportedImageTypeError):
        prepare_images([("image/jpeg", b"definitely not an image")])


def test_given_a_file_over_the_size_limit_when_preparing_then_it_is_rejected() -> None:
    """Given an upload past the per-file byte limit, when preparing, then it
    is rejected before being decoded — decoding is where a hostile or
    corrupt file would cost the most memory."""
    oversized = b"\xff\xd8" + b"0" * MAX_BYTES_PER_IMAGE

    with pytest.raises(ImageTooLargeError):
        prepare_images([("image/jpeg", oversized)])
