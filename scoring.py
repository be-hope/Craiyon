import io

import imagehash
import numpy as np
import requests
from PIL import Image, ImageFilter

HASH_SIZE = 16
MAX_BITS = HASH_SIZE * HASH_SIZE
COLOR_BINS = 6
GRID = 3  # 3x3 spatial grid for both color and edge-density comparison

# Three independent signals, each catching something the others miss:
#  - structure: combined phash+dhash+whash distance (shape/composition)
#  - color: spatial (per-region) color histogram match
#  - edge: spatial "how much fine detail is in each region" match
# A global color histogram alone can't tell WHERE colors sit, and a single
# hash algorithm has blind spots -- combining three signals plus spatial
# awareness gives real separation between genuine matches and mismatches
# instead of everything clustering in the 50-60 range.
#
# Weighting note: structure (perceptual hash) is the least forgiving signal
# for this use case -- two independently-generated images of the same
# concept (e.g. "a blue fox at night") can differ a lot in composition and
# framing even when the prompt was accurate, so leaning too hard on
# structure systematically underscores honest matches. Color is the most
# reliable indicator that the right *content* was described, so it now
# carries the most weight.
STRUCTURE_WEIGHT = 0.30
COLOR_WEIGHT = 0.45
EDGE_WEIGHT = 0.25
# Curve exponent: still >1 so real mismatches get pushed down, but 2.0 was
# crushing decent-but-imperfect matches too (a solid 0.78 raw score was
# landing around 60%). 1.3 keeps meaningful separation for bad matches
# while no longer punishing good-faith accurate prompts this hard.
SCORE_CURVE_EXPONENT = 1.3


def _load_image(image_bytes: bytes) -> Image.Image:
    return Image.open(io.BytesIO(image_bytes)).convert("RGB")


def _combined_hash(img: Image.Image) -> dict:
    return {
        "phash": imagehash.phash(img, hash_size=HASH_SIZE),
        "dhash": imagehash.dhash(img, hash_size=HASH_SIZE),
        "whash": imagehash.whash(img, hash_size=HASH_SIZE),
    }


def _spatial_color_histogram(img: Image.Image) -> np.ndarray:
    arr = np.array(img.resize((GRID * 40, GRID * 40)))
    h, w, _ = arr.shape
    cell_h, cell_w = h // GRID, w // GRID
    out = []
    for row in range(GRID):
        for col in range(GRID):
            cell = arr[row * cell_h:(row + 1) * cell_h, col * cell_w:(col + 1) * cell_w]
            for channel in range(3):
                hist, _ = np.histogram(cell[:, :, channel], bins=COLOR_BINS, range=(0, 255))
                out.extend(hist / (hist.sum() + 1e-8))
    return np.array(out)


def _spatial_edge_density(img: Image.Image) -> np.ndarray:
    edges = img.convert("L").filter(ImageFilter.FIND_EDGES)
    arr = np.array(edges.resize((GRID * 40, GRID * 40)))
    h, w = arr.shape
    cell_h, cell_w = h // GRID, w // GRID
    out = []
    for row in range(GRID):
        for col in range(GRID):
            cell = arr[row * cell_h:(row + 1) * cell_h, col * cell_w:(col + 1) * cell_w]
            out.append(cell.mean() / 255.0)
    return np.array(out)


class ImageFingerprint:
    """Bundles all three signals for one image."""

    def __init__(self, hashes: dict, color_hist: np.ndarray, edge_density: np.ndarray):
        self.hashes = hashes
        self.color_hist = color_hist
        self.edge_density = edge_density

    def to_dict(self) -> dict:
        return {
            "phash": str(self.hashes["phash"]),
            "dhash": str(self.hashes["dhash"]),
            "whash": str(self.hashes["whash"]),
            "color_hist": self.color_hist.tolist(),
            "edge_density": self.edge_density.tolist(),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ImageFingerprint":
        return cls(
            hashes={
                "phash": imagehash.hex_to_hash(d["phash"]),
                "dhash": imagehash.hex_to_hash(d["dhash"]),
                "whash": imagehash.hex_to_hash(d["whash"]),
            },
            color_hist=np.array(d["color_hist"]),
            edge_density=np.array(d["edge_density"]),
        )


def fingerprint_from_bytes(image_bytes: bytes) -> ImageFingerprint:
    img = _load_image(image_bytes)
    return ImageFingerprint(_combined_hash(img), _spatial_color_histogram(img), _spatial_edge_density(img))


def fingerprint_from_url(url: str) -> ImageFingerprint:
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return fingerprint_from_bytes(resp.content)


def _cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    denom = (np.linalg.norm(a) * np.linalg.norm(b)) + 1e-8
    return max(0.0, float(np.dot(a, b)) / denom)


def similarity_score(target: ImageFingerprint, generated: ImageFingerprint) -> float:
    """0-100 score. 100 = identical, 0 = maximally different."""
    hash_distance = (
        (target.hashes["phash"] - generated.hashes["phash"])
        + (target.hashes["dhash"] - generated.hashes["dhash"])
        + (target.hashes["whash"] - generated.hashes["whash"])
    ) / 3.0
    structure_score = max(0.0, 1 - hash_distance / MAX_BITS)

    color_score = _cosine_sim(target.color_hist, generated.color_hist)

    edge_diff = np.abs(target.edge_density - generated.edge_density).mean()
    edge_score = max(0.0, 1 - edge_diff)

    combined = (
        STRUCTURE_WEIGHT * structure_score
        + COLOR_WEIGHT * color_score
        + EDGE_WEIGHT * edge_score
    )
    combined = combined ** SCORE_CURVE_EXPONENT

    return round(combined * 100, 2)
