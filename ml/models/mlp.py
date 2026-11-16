import torch
import torch.nn as nn


class SpectralMLP(nn.Module):
    """Baseline 1: Spectral-only MLP operating on the center pixel's PCA spectral vector."""

    def __init__(
        self, in_features: int = 24, hidden_dim: int = 128, n_classes: int = 2, dropout: float = 0.1
    ):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_features, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.BatchNorm1d(hidden_dim // 2),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim // 2, n_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x is (N, 1, C, H, W) or (N, C)
        if x.dim() == 5:
            # Extract center pixel
            _, _, c, h, w = x.shape
            center_x = x[:, 0, :, h // 2, w // 2]  # (N, C)
        elif x.dim() == 4:
            _, c, h, w = x.shape
            center_x = x[:, :, h // 2, w // 2]
        else:
            center_x = x
        return self.net(center_x)
