"""Validates and normalises uploaded recipe photos before they are sent to
the vision model.

A phone photo is typically 3-5 MB at 4000px wide, and base64-encoding it for
the API inflates that by a third — a batch of untouched uploads would be
tens of megabytes per request. Vision models downscale internally anyway, so
capping the long edge here costs no legible detail and buys back most of the
bandwidth and latency.
"""

import io
from collections.abc import Sequence

from PIL import Image, UnidentifiedImageError

MAX_IMAGES = 8
MAX_BYTES_PER_IMAGE = 10 * 1024 * 1024
MAX_LONG_EDGE_PIXELS = 1568
ACCEPTED_CONTENT_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})

_JPEG_QUALITY = 85


class ImageIntakeError(Exception):
    """Base exception for a recipe photo upload that can't be accepted."""


class NoImagesProvidedError(ImageIntakeError):
    """Raised when the submission contains no files at all."""


class TooManyImagesError(ImageIntakeError):
    """Raised when more images are submitted than a single recipe allows."""


class UnsupportedImageTypeError(ImageIntakeError):
    """Raised when a file isn't an image this app can read — either by its
    declared content type or because its bytes don't decode."""


class ImageTooLargeError(ImageIntakeError):
    """Raised when a single file exceeds the per-image byte limit."""


def prepare_images(uploads: Sequence[tuple[str | None, bytes]]) -> list[bytes]:
    """Validate `(content_type, bytes)` uploads and return them as JPEG
    bytes, downscaled, in the order received.

    Order is part of the contract: the images are the pages of one recipe,
    and the vision model is told to read them in sequence.

    Raises NoImagesProvidedError, TooManyImagesError,
    UnsupportedImageTypeError or ImageTooLargeError — the API layer is
    responsible for translating them into user-facing responses.
    """
    if not uploads:
        raise NoImagesProvidedError("No images were submitted")
    if len(uploads) > MAX_IMAGES:
        raise TooManyImagesError(f"{len(uploads)} images submitted, the limit is {MAX_IMAGES}")

    return [_prepare_one(content_type, data) for content_type, data in uploads]


def _prepare_one(content_type: str | None, data: bytes) -> bytes:
    if content_type not in ACCEPTED_CONTENT_TYPES:
        raise UnsupportedImageTypeError(f"Unsupported upload content type: {content_type!r}")
    # Checked before decoding: that is where a corrupt or hostile file would
    # cost the most memory.
    if len(data) > MAX_BYTES_PER_IMAGE:
        raise ImageTooLargeError(f"Image is {len(data)} bytes, the limit is {MAX_BYTES_PER_IMAGE}")

    try:
        image = Image.open(io.BytesIO(data))
        image.load()
    except (UnidentifiedImageError, OSError, ValueError) as error:
        # The declared content type is client-supplied, so bytes that don't
        # actually decode land here rather than at the check above.
        raise UnsupportedImageTypeError(f"Could not decode the uploaded image: {error}") from error

    return _to_downscaled_jpeg(image)


def _to_downscaled_jpeg(image: Image.Image) -> bytes:
    # JPEG has no alpha channel, so PNGs and WebPs carrying one (screenshots,
    # mostly) have to be flattened explicitly instead of failing on save.
    if image.mode != "RGB":
        image = image.convert("RGB")

    long_edge = max(image.size)
    if long_edge > MAX_LONG_EDGE_PIXELS:
        scale = MAX_LONG_EDGE_PIXELS / long_edge
        # round(), not int(): truncating makes the capped edge land one pixel
        # short of the limit.
        resized = (round(image.width * scale), round(image.height * scale))
        image = image.resize(resized, Image.Resampling.LANCZOS)

    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=_JPEG_QUALITY)
    return buffer.getvalue()
