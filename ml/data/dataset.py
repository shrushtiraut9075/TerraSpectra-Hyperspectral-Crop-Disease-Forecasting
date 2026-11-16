import os
import random
from typing import List, Tuple, Dict, Any, Optional

import numpy as np
import torch
from torch.utils.data import Dataset, Sampler
import rasterio
from rasterio.windows import Window

from ml.data.preprocess import HSIPreprocessor
from ml.data.pca import HSIPCATransformer

class HSIPatchDataset(Dataset):
    """
    Hyperspectral patch dataset reading windowed patches lazily per worker.
    Caches PCA-transformed spatial rasters (per data-pipeline.md §8) to accelerate training.
    Returns:
        patch: torch.Tensor shape (1, C, patch_size, patch_size) float32
        label: torch.Tensor (int64 classification target: 0 healthy, 1 stressed)
        meta: dict with metadata
    """

    # Class-level cache across workers/epochs to avoid recomputing PCA
    _scene_pca_cache: Dict[str, np.ndarray] = {}

    def __init__(
        self,
        samples: List[Dict[str, Any]],
        preprocessor: HSIPreprocessor,
        pca_transformer: HSIPCATransformer,
        patch_size: int = 11,
        augment: bool = False,
        horizon_days: int = 21,
        cache_pca: bool = True
    ):
        self.samples = samples
        self.preprocessor = preprocessor
        self.pca_transformer = pca_transformer
        self.patch_size = patch_size
        self.half_size = patch_size // 2
        self.augment = augment
        self.horizon_days = horizon_days
        self.cache_pca = cache_pca

    def __len__(self) -> int:
        return len(self.samples)

    def _get_pca_raster(self, tif_path: str) -> np.ndarray:
        if self.cache_pca and tif_path in self._scene_pca_cache:
            return self._scene_pca_cache[tif_path]

        # Read raster using windowed blocks
        with rasterio.open(tif_path) as src:
            h, w = src.height, src.width
            # Read block-by-block
            raw_cube = np.zeros((src.count, h, w), dtype=np.float32)
            block_size = 128
            for r in range(0, h, block_size):
                for c in range(0, w, block_size):
                    bw = min(block_size, w - c)
                    bh = min(block_size, h - r)
                    win = Window(c, r, bw, bh)
                    raw_cube[:, r:r+bh, c:c+bw] = src.read(window=win)

        clean_cube, _ = self.preprocessor.transform_window(raw_cube)
        pca_cube = self.pca_transformer.transform_window(clean_cube) # (C, H, W)

        if self.cache_pca:
            self._scene_pca_cache[tif_path] = pca_cube

        return pca_cube

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor, Dict[str, Any]]:
        sample = self.samples[idx]
        tif_path = sample["tif_path"]
        r = sample["row"]
        c = sample["col"]

        pca_raster = self._get_pca_raster(tif_path) # (C, H, W)
        c_dim, h, w = pca_raster.shape

        # Slicing patch with border clamping
        r_start = max(0, r - self.half_size)
        r_end = min(h, r + self.half_size + 1)
        c_start = max(0, c - self.half_size)
        c_end = min(w, c + self.half_size + 1)

        patch = np.zeros((c_dim, self.patch_size, self.patch_size), dtype=np.float32)
        pr_start = 0 if r >= self.half_size else (self.half_size - r)
        pc_start = 0 if c >= self.half_size else (self.half_size - c)
        actual_h = r_end - r_start
        actual_w = c_end - c_start

        patch[:, pr_start:pr_start + actual_h, pc_start:pc_start + actual_w] = pca_raster[:, r_start:r_end, c_start:c_end]

        # Augmentation (train only)
        if self.augment:
            if random.random() > 0.5:
                patch = np.flip(patch, axis=2).copy()
            if random.random() > 0.5:
                patch = np.flip(patch, axis=1).copy()
            k = random.randint(0, 3)
            if k > 0:
                patch = np.rot90(patch, k, axes=(1, 2)).copy()
            jitter = np.random.normal(0.0, 0.02, (patch.shape[0], 1, 1)).astype(np.float32)
            patch = patch + jitter

        patch_tensor = torch.from_numpy(patch).unsqueeze(0).float() # (1, C, H, W)

        label_val = sample["label"]
        if "days_to_visible" in sample and sample["days_to_visible"] >= 0:
            if sample["days_to_visible"] <= self.horizon_days:
                label_val = 1

        label_tensor = torch.tensor(label_val, dtype=torch.long)
        return patch_tensor, label_tensor, sample

class BalancedClassSampler(Sampler):
    """Balanced sampler that oversamples the minority (stressed) class."""

    def __init__(self, labels: List[int]):
        self.labels = np.array(labels)
        self.classes = np.unique(self.labels)
        self.class_indices = {c: np.where(self.labels == c)[0] for c in self.classes}
        self.max_class_count = max(len(indices) for indices in self.class_indices.values())
        self.total_samples = self.max_class_count * len(self.classes)

    def __iter__(self):
        balanced_indices = []
        for c in self.classes:
            indices = self.class_indices[c]
            oversampled = np.random.choice(indices, self.max_class_count, replace=True)
            balanced_indices.extend(oversampled)
        np.random.shuffle(balanced_indices)
        return iter(balanced_indices)

    def __len__(self) -> int:
        return self.total_samples