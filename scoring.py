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
# landing around 60%). 1.15 keeps meaningful separation for bad matches
# while giving good-faith attempts a bit more breathing room (slightly
# more lenient across the board per user request).
SCORE_CURVE_EXPONENT = 1.15


def _load_image(image_bytes: bytes) -> Image.Image:
    return Image.open(io.BytesIO(image_bytes)).convert("RGB")


def _combined_hash(img: Image.Image) -> dict:
    return {
        "phash": imagehash.phash(img, hash_size=HASH_SIZE),
        "dhash": imagehash.dhash(img, hash_size=HASH_SIZE),
        "whash": imagehash.whash(img, hash_size=HASH_SIZE),
    }


def _spatial_color_histogram(img: Image.Image) -> np.ndarray:
    """Per-region color histograms, kept as a (n_cells, bins) array -- NOT
    flattened -- so mismatches can be scored per-region instead of averaged
    away by the whole image at once."""
    arr = np.array(img.resize((GRID * 40, GRID * 40)))
    h, w, _ = arr.shape
    cell_h, cell_w = h // GRID, w // GRID
    cells = []
    for row in range(GRID):
        for col in range(GRID):
            cell = arr[row * cell_h:(row + 1) * cell_h, col * cell_w:(col + 1) * cell_w]
            cell_vec = []
            for channel in range(3):
                hist, _ = np.histogram(cell[:, :, channel], bins=COLOR_BINS, range=(0, 255))
                cell_vec.extend(hist / (hist.sum() + 1e-8))
            cells.append(cell_vec)
    return np.array(cells)  # shape: (GRID*GRID, COLOR_BINS*3)


def _spatial_mean_color(img: Image.Image) -> np.ndarray:
    """Per-region average RGB (normalized 0-1), shape (n_cells, 3).

    A histogram alone is dominated by whichever pixel value is most common
    in a cell -- if most of a cell is dark background, the histogram barely
    reacts to a smaller, differently-colored subject sitting in that same
    cell (the subject's pixels are a minority vote in the bin counts).
    Average color doesn't have that blind spot: swap an orange fox for a
    blue one and the cell's mean RGB shifts immediately and proportionally,
    even with mostly-matching background around it.
    """
    arr = np.array(img.resize((GRID * 40, GRID * 40))).astype(np.float64) / 255.0
    h, w, _ = arr.shape
    cell_h, cell_w = h // GRID, w // GRID
    cells = []
    for row in range(GRID):
        for col in range(GRID):
            cell = arr[row * cell_h:(row + 1) * cell_h, col * cell_w:(col + 1) * cell_w]
            cells.append(cell.reshape(-1, 3).mean(axis=0))
    return np.array(cells)  # shape: (GRID*GRID, 3)


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
    """Bundles all signals for one image."""

    def __init__(self, hashes: dict, color_hist: np.ndarray, mean_color: np.ndarray, edge_density: np.ndarray):
        self.hashes = hashes
        self.color_hist = color_hist
        self.mean_color = mean_color
        self.edge_density = edge_density

    def to_dict(self) -> dict:
        return {
            "phash": str(self.hashes["phash"]),
            "dhash": str(self.hashes["dhash"]),
            "whash": str(self.hashes["whash"]),
            "color_hist": self.color_hist.tolist(),
            "mean_color": self.mean_color.tolist(),
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
            mean_color=np.array(d.get("mean_color", [])),
            edge_density=np.array(d["edge_density"]),
        )


def fingerprint_from_bytes(image_bytes: bytes) -> ImageFingerprint:
    img = _load_image(image_bytes)
    return ImageFingerprint(
        _combined_hash(img),
        _spatial_color_histogram(img),
        _spatial_mean_color(img),
        _spatial_edge_density(img),
    )


def fingerprint_from_url(url: str) -> ImageFingerprint:
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return fingerprint_from_bytes(resp.content)


def _cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    denom = (np.linalg.norm(a) * np.linalg.norm(b)) + 1e-8
    return max(0.0, float(np.dot(a, b)) / denom)


def _per_cell_hist_scores(target_cells: np.ndarray, generated_cells: np.ndarray) -> np.ndarray:
    return np.array([
        _cosine_sim(target_cells[i], generated_cells[i])
        for i in range(target_cells.shape[0])
    ])


def _per_cell_mean_color_scores(target_cells: np.ndarray, generated_cells: np.ndarray) -> np.ndarray:
    """1 - RGB distance between per-cell average color, normalized against a
    *realistic* color-difference scale rather than the theoretical extreme
    (pure black vs pure white, distance sqrt(3)).

    Normalizing against sqrt(3) badly under-penalizes real color swaps in
    darker/mid-brightness scenes: e.g. an orange subject vs a blue subject
    on the same night backdrop only produces a raw distance of ~0.12,
    which sqrt(3)-normalization scores as 93% similar despite being a
    completely different color. MEANINGFUL_COLOR_DISTANCE is calibrated to
    the kind of distance an actually-different color produces in practice,
    so that same swap scores as a clear, visible mismatch instead.
    """
    diffs = np.linalg.norm(target_cells - generated_cells, axis=1)
    return np.clip(1 - (diffs / MEANINGFUL_COLOR_DISTANCE), 0.0, 1.0)


# How much a badly-mismatched region should drag the score down, versus a
# plain average across all regions. 0.0 = pure average (the old behavior,
# which let a wrong subject hide behind a matching background/sky/ground).
# 1.0 = score is set entirely by the worst region. 0.5 is a middle ground:
# a genuinely wrong subject still tanks the score, but a little noise in
# one region (JPEG artifacts, a slightly different shadow) won't nuke an
# otherwise-accurate image.
WORST_REGION_PENALTY = 0.5
N_WORST_CELLS = 3  # average the N worst-matching regions, not just the single worst

# Within the color signal: histogram shape catches texture/variety within a
# region, but is dominated by whichever value is most common (usually
# background), so it barely reacts to a smaller, differently-colored
# subject. Mean color reacts immediately to exactly that case. Mean color
# gets the larger share since "did they get the right color object" matters
# more here than exact shading/texture distribution.
HIST_SHAPE_WEIGHT = 0.35
MEAN_COLOR_WEIGHT = 0.65
# Calibrated so a clear hue swap (e.g. orange subject -> blue subject) on a
# similar backdrop lands around a 0.4-0.5 cell score, not 0.9+. See the
# docstring on _per_cell_mean_color_scores for why sqrt(3) doesn't work here.
MEANINGFUL_COLOR_DISTANCE = 0.22


def _region_aware_score(cell_scores: np.ndarray) -> float:
    mean_score = float(cell_scores.mean())
    worst_n = np.sort(cell_scores)[:N_WORST_CELLS]
    worst_score = float(worst_n.mean())
    return (1 - WORST_REGION_PENALTY) * mean_score + WORST_REGION_PENALTY * worst_score


def similarity_score(target: ImageFingerprint, generated: ImageFingerprint) -> float:
    """0-100 score. 100 = identical, 0 = maximally different."""
    hash_distance = (
        (target.hashes["phash"] - generated.hashes["phash"])
        + (target.hashes["dhash"] - generated.hashes["dhash"])
        + (target.hashes["whash"] - generated.hashes["whash"])
    ) / 3.0
    structure_score = max(0.0, 1 - hash_distance / MAX_BITS)

    hist_cell_scores = _per_cell_hist_scores(target.color_hist, generated.color_hist)
    if target.mean_color.size and generated.mean_color.size:
        mean_color_cell_scores = _per_cell_mean_color_scores(target.mean_color, generated.mean_color)
        per_cell_color = HIST_SHAPE_WEIGHT * hist_cell_scores + MEAN_COLOR_WEIGHT * mean_color_cell_scores
    else:
        # Fingerprint predates the mean-color signal (old stored target) --
        # fall back to histogram-only rather than erroring out.
        per_cell_color = hist_cell_scores
    color_score = _region_aware_score(per_cell_color)

    edge_cell_scores = 1 - np.abs(target.edge_density - generated.edge_density)
    edge_cell_scores = np.clip(edge_cell_scores, 0.0, 1.0)
    edge_score = _region_aware_score(edge_cell_scores)

    combined = (
        STRUCTURE_WEIGHT * structure_score
        + COLOR_WEIGHT * color_score
        + EDGE_WEIGHT * edge_score
    )
    combined = combined ** SCORE_CURVE_EXPONENT

    return round(combined * 100, 2)