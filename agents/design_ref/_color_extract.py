"""Color extraction helper using Pillow + numpy K-means.

Pure helpers — no network here. Callers are responsible for fetching image
bytes (or passing a local path) before invocation.
"""
from __future__ import annotations

import io
from pathlib import Path
from typing import Iterable, List, Tuple

import numpy as np
from PIL import Image


def _to_hex(rgb: Tuple[int, int, int]) -> str:
    r, g, b = (int(max(0, min(255, c))) for c in rgb)
    return f"#{r:02x}{g:02x}{b:02x}"


def _load(source: bytes | str | Path) -> Image.Image:
    if isinstance(source, (bytes, bytearray)):
        return Image.open(io.BytesIO(source)).convert("RGB")
    return Image.open(source).convert("RGB")


def kmeans_palette(
    source: bytes | str | Path,
    k: int = 5,
    max_size: int = 128,
    iters: int = 8,
) -> List[str]:
    """Return up to *k* dominant hex colors from one image via tiny K-means.

    Resizes to *max_size* px on the long edge first (perf). Deterministic with
    a fixed seed so tests stay stable.
    """
    img = _load(source)
    img.thumbnail((max_size, max_size))
    pixels = np.asarray(img, dtype=np.float32).reshape(-1, 3)
    if pixels.shape[0] == 0:
        return []

    k = max(1, min(k, pixels.shape[0]))
    rng = np.random.default_rng(seed=42)
    centroids = pixels[rng.choice(pixels.shape[0], size=k, replace=False)].copy()

    for _ in range(iters):
        # assign
        dists = ((pixels[:, None, :] - centroids[None, :, :]) ** 2).sum(axis=2)
        labels = dists.argmin(axis=1)
        # update
        new_centroids = np.array(
            [
                pixels[labels == i].mean(axis=0) if (labels == i).any() else centroids[i]
                for i in range(k)
            ]
        )
        if np.allclose(new_centroids, centroids, atol=1.0):
            centroids = new_centroids
            break
        centroids = new_centroids

    # sort by cluster size descending
    counts = np.bincount(labels, minlength=k)
    order = np.argsort(-counts)
    return [_to_hex(tuple(centroids[i])) for i in order]


def aggregate_palettes(palettes: Iterable[List[str]]) -> List[str]:
    """Flatten per-image palettes, dedup by hex, preserve first-seen order."""
    seen: set[str] = set()
    out: List[str] = []
    for pal in palettes:
        for hex_color in pal:
            if hex_color not in seen:
                seen.add(hex_color)
                out.append(hex_color)
    return out
