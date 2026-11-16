import torch
import torch.nn as nn


class SpatialCNN2D(nn.Module):
    """Baseline 2: 2D-CNN treating C PCA components as channels."""

    def __init__(self, in_channels: int = 24, n_classes: int = 2, dropout: float = 0.1):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(in_channels, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32),
            nn.GELU(),
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64),
            nn.GELU(),
            nn.Conv2d(64, 128, kernel_size=3, padding=1),
            nn.BatchNorm2d(128),
            nn.GELU(),
            nn.AdaptiveAvgPool2d((1, 1)),
        )
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Dropout(dropout),
            nn.Linear(128, 64),
            nn.GELU(),
            nn.Linear(64, n_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (N, 1, C, H, W)
        if x.dim() == 5:
            x = x.squeeze(1)  # (N, C, H, W)
        feat = self.features(x)
        return self.classifier(feat)
