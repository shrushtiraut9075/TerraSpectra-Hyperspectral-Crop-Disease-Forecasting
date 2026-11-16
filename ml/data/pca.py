import os
from typing import Any, Dict

import joblib
import matplotlib
import numpy as np
from sklearn.decomposition import IncrementalPCA

matplotlib.use("Agg")
import matplotlib.pyplot as plt


class HSIPCATransformer:
    """Incremental PCA dimensionality reduction for hyperspectral data."""

    def __init__(self, n_components: int = 24, batch_size: int = 2048):
        self.n_components = n_components
        self.batch_size = batch_size
        self.ipca = IncrementalPCA(n_components=n_components, batch_size=batch_size)
        self.is_fitted = False

    def fit(self, training_pixels: np.ndarray) -> Dict[str, Any]:
        """
        Fit IncrementalPCA on training pixels.
        training_pixels: shape (N, B_good)
        """
        valid_mask = ~np.isnan(training_pixels).any(axis=1)
        clean_pixels = training_pixels[valid_mask]

        n_samples = clean_pixels.shape[0]
        for start_idx in range(0, n_samples, self.batch_size):
            end_idx = min(n_samples, start_idx + self.batch_size)
            batch = clean_pixels[start_idx:end_idx]
            if batch.shape[0] >= self.n_components:
                self.ipca.partial_fit(batch)

        self.is_fitted = True
        explained_var = self.ipca.explained_variance_ratio_
        cumulative_var = np.cumsum(explained_var)

        report = {
            "n_components": int(self.n_components),
            "total_explained_variance": float(cumulative_var[-1]),
            "component_variances": [float(v) for v in explained_var],
            "cumulative_variances": [float(v) for v in cumulative_var],
        }
        return report

    def transform_window(self, window: np.ndarray) -> np.ndarray:
        """
        Applies PCA transform to a spatial window (B_good, H, W).
        Returns:
            pca_window: shape (C, H, W) float32
        """
        if not self.is_fitted:
            raise RuntimeError("PCA transformer must be fitted before transforming.")

        b, h, w = window.shape
        # Reshape to (H*W, B_good)
        pixels = np.transpose(window, (1, 2, 0)).reshape(-1, b)
        # Transform to (H*W, C)
        transformed = self.ipca.transform(pixels)
        # Reshape back to (C, H, W)
        pca_window = np.transpose(transformed.reshape(h, w, self.n_components), (2, 0, 1))
        return pca_window.astype(np.float32)

    def save(self, path: str) -> None:
        """Save fitted IncrementalPCA model."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        joblib.dump(self.ipca, path)

    def load(self, path: str) -> None:
        """Load fitted IncrementalPCA model."""
        self.ipca = joblib.load(path)
        self.n_components = self.ipca.n_components_
        self.is_fitted = True

    def plot_variance(self, output_path: str) -> None:
        """Plot explained variance curve and save to file."""
        if not self.is_fitted:
            return
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        cum_var = np.cumsum(self.ipca.explained_variance_ratio_)
        plt.figure(figsize=(8, 5))
        plt.plot(range(1, len(cum_var) + 1), cum_var * 100.0, marker="o", color="#10b981", lw=2)
        plt.axhline(99.0, color="#ef4444", linestyle="--", label="99% Variance Threshold")
        plt.title(
            "Incremental PCA - Cumulative Explained Variance Ratio", fontsize=12, fontweight="bold"
        )
        plt.xlabel("Number of Principal Components", fontsize=10)
        plt.ylabel("Cumulative Explained Variance (%)", fontsize=10)
        plt.grid(True, alpha=0.3)
        plt.legend()
        plt.tight_layout()
        plt.savefig(output_path, dpi=200)
        plt.close()
