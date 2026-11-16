import json
import os
from typing import List, Optional, Tuple

import numpy as np


def get_bad_band_indices(
    wavelengths: np.ndarray,
    water_vapor_ranges: Optional[List[List[float]]] = None,
    edge_drop: int = 4,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Identifies bad/noisy bands (atmospheric absorption and sensor edge noise).
    Returns:
        good_indices: 1D array of retained band indices
        bad_indices: 1D array of dropped band indices
    """
    if water_vapor_ranges is None:
        water_vapor_ranges = [[1350.0, 1450.0], [1800.0, 1950.0]]

    n_bands = len(wavelengths)
    bad_mask = np.zeros(n_bands, dtype=bool)

    # Edge bands
    if edge_drop > 0:
        bad_mask[:edge_drop] = True
        bad_mask[-edge_drop:] = True

    # Atmospheric water vapor bands
    for low, high in water_vapor_ranges:
        in_range = (wavelengths >= low) & (wavelengths <= high)
        bad_mask = bad_mask | in_range

    good_indices = np.where(~bad_mask)[0]
    bad_indices = np.where(bad_mask)[0]
    return good_indices, bad_indices


class HSIPreprocessor:
    """Preprocesses hyperspectral cubes: bad-band removal, scaling, and per-band standardization."""

    def __init__(
        self,
        wavelengths: np.ndarray,
        water_vapor_ranges: Optional[List[List[float]]] = None,
        edge_drop: int = 4,
        scale_factor: float = 1.0,
    ):
        self.wavelengths = np.array(wavelengths, dtype=np.float32)
        self.scale_factor = scale_factor
        self.good_band_indices, self.bad_band_indices = get_bad_band_indices(
            self.wavelengths, water_vapor_ranges, edge_drop
        )
        self.retained_bands = len(self.good_band_indices)
        self.mean: Optional[np.ndarray] = None
        self.std: Optional[np.ndarray] = None

    def fit_standardization(self, sample_pixels: np.ndarray) -> None:
        """
        Fit per-band mean and std on training-only sampled pixels.
        sample_pixels: shape (N, B_good) or (B_good, N)
        """
        if sample_pixels.ndim == 2 and sample_pixels.shape[0] == self.retained_bands:
            sample_pixels = sample_pixels.T

        # sample_pixels shape is (N, B_good)
        valid_mask = ~np.isnan(sample_pixels).any(axis=1)
        valid_data = sample_pixels[valid_mask] * self.scale_factor

        self.mean = np.mean(valid_data, axis=0).astype(np.float32)
        self.std = np.std(valid_data, axis=0).astype(np.float32)
        # Avoid division by zero
        self.std[self.std < 1e-6] = 1.0

    def transform_window(
        self, raw_window: np.ndarray, valid_mask: Optional[np.ndarray] = None
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Transform a raw window (B, H, W).
        Returns:
            clean_window: (B_good, H, W) normalized float32
            mask: (H, W) bool
        """
        # Select good bands
        clean = raw_window[self.good_band_indices] * self.scale_factor

        if valid_mask is None:
            mask = ~np.isnan(clean).any(axis=0)
        else:
            mask = valid_mask.copy()

        if self.mean is not None and self.std is not None:
            # Broadcast standardization across (B_good, H, W)
            clean = (clean - self.mean[:, None, None]) / self.std[:, None, None]

        # Fill invalid pixels with 0.0
        clean[:, ~mask] = 0.0
        return clean.astype(np.float32), mask

    def save_stats(self, path: str) -> None:
        """Persist normalization parameters to json."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        stats = {
            "scale_factor": self.scale_factor,
            "retained_bands": int(self.retained_bands),
            "good_band_indices": [int(i) for i in self.good_band_indices],
            "bad_band_indices": [int(i) for i in self.bad_band_indices],
            "mean": [float(m) for m in self.mean] if self.mean is not None else [],
            "std": [float(s) for s in self.std] if self.std is not None else [],
        }
        with open(path, "w") as f:
            json.dump(stats, f, indent=2)

    def load_stats(self, path: str) -> None:
        """Load normalization stats from json."""
        with open(path, "r") as f:
            stats = json.load(f)
        self.good_band_indices = np.array(stats["good_band_indices"], dtype=np.int64)
        self.bad_band_indices = np.array(stats["bad_band_indices"], dtype=np.int64)
        self.retained_bands = len(self.good_band_indices)
        self.mean = np.array(stats["mean"], dtype=np.float32) if stats["mean"] else None
        self.std = np.array(stats["std"], dtype=np.float32) if stats["std"] else None
