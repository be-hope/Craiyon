import io

import imagehash
import numpy as np
import requests
from PIL import Image

HASH_SIZE = 16  # bigger = more precise structural comparison, slightly slower
MAX_BITS = HASH_SIZE * HASH_SIZE
COLOR_BINS = 8

# Weighting: structure (shapes/composition) vs color match.
# Pure perceptual hash barely notices color at all (a solid red and solid
# blue image hash almost identically), so we blend in a color histogram
# to make sure color differences actually move the score.
STRUCTURE_WEIGHT = 0.6
COLOR_WEIGHT = 0.4


def _load_image(image_bytes: bytes) -> Image.Image:
    return Image.open(io.BytesIO(image_bytes)).convert("RGB")


def _phash(img: Image.Image) -> imagehash.ImageHash:
    return imagehash.phash(img, hash_size=HASH_SIZE)


def _color_histogram(img: Image.Image) -> np.ndarray:
    arr = np.array(img)
    hist = []
    for channel in range(3):  # R, G, B
        h, _ = np.histogram(arr[:, :, channel], bins=COLOR_BINS, range=(0, 255))
        hist.extend(h / (h.sum() + 1e-8))
    return np.array(hist)


class ImageFingerprint:
    """Bundles the structural hash + color histogram for one image."""

    def __init__(self, phash: imagehash.ImageHash, color_hist: np.ndarray):
        self.phash = phash
        self.color_hist = color_hist

    def to_dict(self) -> dict:
        return {
            "phash": str(self.phash),
            "color_hist": self.color_hist.tolist(),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ImageFingerprint":
        return cls(
            phash=imagehash.hex_to_hash(d["phash"]),
            color_hist=np.array(d["color_hist"]),
        )


def fingerprint_from_bytes(image_bytes: bytes) -> ImageFingerprint:
    img = _load_image(image_bytes)
    return ImageFingerprint(_phash(img), _color_histogram(img))


def fingerprint_from_url(url: str) -> ImageFingerprint:
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return fingerprint_from_bytes(resp.content)


def similarity_score(target: ImageFingerprint, generated: ImageFingerprint) -> float:
    """0-100 score. 100 = identical, 0 = maximally different."""
    hash_distance = target.phash - generated.phash
    structure_score = max(0.0, 1 - hash_distance / MAX_BITS)

    denom = (np.linalg.norm(target.color_hist) * np.linalg.norm(generated.color_hist)) + 1e-8
    color_score = max(0.0, float(np.dot(target.color_hist, generated.color_hist)) / denom)

    combined = STRUCTURE_WEIGHT * structure_score + COLOR_WEIGHT * color_score
    return round(combined * 100, 2)
