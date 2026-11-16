import torch
import torch.nn as nn


class HyperspectralCNN3D(nn.Module):
    """
    Baseline 3 & CNN Stem: 3D-CNN over (spectral_depth, height, width) to capture
    local spatial-spectral features simultaneously.
    """

    def __init__(
        self,
        in_channels: int = 1,
        pca_components: int = 24,
        n_classes: int = 2,
        dropout: float = 0.1,
    ):
        super().__init__()
        # Conv3d blocks: kernels (k_spectral, k_h, k_w) with padding to preserve spatial-spectral grid
        self.block1 = nn.Sequential(
            nn.Conv3d(in_channels, 16, kernel_size=(7, 3, 3), padding=(3, 1, 1)),
            nn.BatchNorm3d(16),
            nn.GELU(),
        )
        self.block2 = nn.Sequential(
            nn.Conv3d(16, 32, kernel_size=(5, 3, 3), padding=(2, 1, 1)),
            nn.BatchNorm3d(32),
            nn.GELU(),
        )
        self.block3 = nn.Sequential(
            nn.Conv3d(32, 64, kernel_size=(3, 3, 3), padding=(1, 1, 1)),
            nn.BatchNorm3d(64),
            nn.GELU(),
        )

        self.pool = nn.AdaptiveAvgPool3d((1, 1, 1))
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Dropout(dropout),
            nn.Linear(64, 64),
            nn.GELU(),
            nn.Linear(64, n_classes),
        )

    def extract_features(self, x: torch.Tensor) -> torch.Tensor:
        """Runs the 3D-CNN stem. Returns feature map (N, 64, D, H, W)."""
        x1 = self.block1(x)
        x2 = self.block2(x1)
        x3 = self.block3(x2)
        return x3

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x is (N, 1, C, H, W)
        features = self.extract_features(x)
        pooled = self.pool(features)
        return self.classifier(pooled)
