from typing import List, Optional, Tuple

import torch
import torch.nn as nn

from ml.models.cnn3d import HyperspectralCNN3D
from ml.models.vit import ViTEncoder


class Hybrid3DCNNViT(nn.Module):
    """
    Hybrid 3D-CNN + Vision Transformer Architecture.
    Combines 3D convolutions for local spatial-spectral geometric textures
    with Transformer self-attention across spectral bands to capture subtle
    cross-spectral chemical correlations (chlorophyll breakdown vs water stress).
    """

    def __init__(
        self,
        in_channels: int = 1,
        pca_components: int = 24,
        patch_size: int = 11,
        n_classes: int = 2,
        token_mode: str = "spectral_groups",  # 'spectral_groups' or 'spatial'
        d_model: int = 128,
        n_layers: int = 4,
        n_heads: int = 4,
        mlp_ratio: float = 2.0,
        dropout: float = 0.1,
        predict_horizon: bool = True,
    ):
        super().__init__()
        self.pca_components = pca_components
        self.patch_size = patch_size
        self.token_mode = token_mode
        self.predict_horizon = predict_horizon

        # 1. 3D-CNN Stem: outputs (N, 64, D', H', W')
        self.cnn_stem = HyperspectralCNN3D(
            in_channels=in_channels,
            pca_components=pca_components,
            n_classes=n_classes,
            dropout=dropout,
        )

        # 2. Tokenization projection
        # Input to stem has depth D = pca_components (24), spatial H = W = patch_size (11)
        # 3D convs use padding to maintain grid dimensions
        if token_mode == "spectral_groups":
            # Group into 6 spectral depth tokens (each 4 depth slices)
            self.n_tokens = 6
            slices_per_token = pca_components // self.n_tokens
            # Per token feature dim: 64 channels * slices_per_token * H * W
            token_raw_dim = 64 * slices_per_token * patch_size * patch_size
            self.token_proj = nn.Linear(token_raw_dim, d_model)
        else:  # spatial tokens
            self.n_tokens = patch_size * patch_size
            token_raw_dim = 64 * pca_components
            self.token_proj = nn.Linear(token_raw_dim, d_model)

        # 3. Vision Transformer Encoder
        self.vit = ViTEncoder(
            seq_len=self.n_tokens,
            d_model=d_model,
            n_layers=n_layers,
            n_heads=n_heads,
            mlp_ratio=mlp_ratio,
            dropout=dropout,
        )

        # 4. Classification & Horizon Risk Heads
        self.class_head = nn.Sequential(
            nn.LayerNorm(d_model), nn.Dropout(dropout), nn.Linear(d_model, n_classes)
        )

        if predict_horizon:
            self.risk_head = nn.Sequential(
                nn.LayerNorm(d_model), nn.Dropout(dropout), nn.Linear(d_model, 1), nn.Sigmoid()
            )

    def tokenize(self, cnn_feat: torch.Tensor) -> torch.Tensor:
        """
        cnn_feat: (N, 64, D, H, W) where D = pca_components (24), H = W = patch_size
        Returns: (N, n_tokens, d_model)
        """
        n, c, d, h, w = cnn_feat.shape
        if self.token_mode == "spectral_groups":
            # Reshape into (N, n_tokens, c, slices_per_token, H, W)
            slices = d // self.n_tokens
            tokens = cnn_feat.view(n, c, self.n_tokens, slices, h, w)
            tokens = tokens.permute(0, 2, 1, 3, 4, 5).contiguous()  # (N, n_tokens, c, slices, H, W)
            tokens = tokens.view(n, self.n_tokens, -1)  # (N, n_tokens, raw_dim)
        else:  # spatial tokens
            # Reshape into (N, H*W, C*D)
            tokens = cnn_feat.permute(0, 3, 4, 1, 2).contiguous()  # (N, H, W, C, D)
            tokens = tokens.view(n, h * w, -1)  # (N, H*W, C*D)

        return self.token_proj(tokens)

    def forward(
        self, x: torch.Tensor, return_attn: bool = False
    ) -> Tuple[torch.Tensor, Optional[torch.Tensor], Optional[torch.Tensor]]:
        """
        Forward pass.
        Returns:
            logits: (N, n_classes)
            risk: (N, 1) probability if predict_horizon else None
            attn_weights: (N, n_heads, seq_len+1, seq_len+1) if return_attn else None
        """
        # 1. 3D-CNN stem feature extraction
        cnn_features = self.cnn_stem.extract_features(x)  # (N, 64, D, H, W)

        # 2. Tokenize into sequence
        tokens = self.tokenize(cnn_features)  # (N, n_tokens, d_model)

        # 3. ViT Encoder
        cls_feat, attn = self.vit(tokens, return_attn=return_attn)  # (N, d_model)

        # 4. Prediction Heads
        logits = self.class_head(cls_feat)
        risk = self.risk_head(cls_feat) if self.predict_horizon else None

        return logits, risk, attn

    @torch.inference_mode()
    def compute_band_importance_perturbation(
        self, x: torch.Tensor, baseline_risk: torch.Tensor
    ) -> List[float]:
        """
        Perturbation check for band-group importance:
        Zeros out each spectral group in input x, measures the risk score delta,
        and normalizes to relative importance shares.
        """
        # x is (1, 1, C, H, W)
        c = x.shape[2]
        group_size = max(1, c // self.n_tokens)
        deltas = []

        for g in range(self.n_tokens):
            start = g * group_size
            end = min(c, start + group_size)
            x_perturbed = x.clone()
            x_perturbed[:, :, start:end, :, :] = 0.0

            _, risk_pert, _ = self.forward(x_perturbed)
            delta = float(torch.abs(baseline_risk - risk_pert).mean().item())
            deltas.append(delta)

        total = sum(deltas) + 1e-6
        return [round(d / total, 4) for d in deltas]
