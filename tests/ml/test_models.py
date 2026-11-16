import torch
import torch.nn as nn
import pytest

from ml.models.mlp import SpectralMLP
from ml.models.cnn2d import SpatialCNN2D
from ml.models.cnn3d import HyperspectralCNN3D
from ml.models.vit import ViTEncoder
from ml.models.hybrid import Hybrid3DCNNViT
from ml.models.losses import FocalLoss

def test_model_forward_shapes():
    batch_size = 4
    c_pca = 24
    patch_size = 11

    # Input tensor shape: (N, 1, C, H, W)
    x = torch.randn(batch_size, 1, c_pca, patch_size, patch_size)

    # 1. Spectral MLP
    mlp = SpectralMLP(in_features=c_pca, n_classes=2)
    out_mlp = mlp(x)
    assert out_mlp.shape == (batch_size, 2)

    # 2. Spatial CNN 2D
    cnn2d = SpatialCNN2D(in_channels=c_pca, n_classes=2)
    out_cnn2d = cnn2d(x)
    assert out_cnn2d.shape == (batch_size, 2)

    # 3. Hyperspectral CNN 3D
    cnn3d = HyperspectralCNN3D(in_channels=1, pca_components=c_pca, n_classes=2)
    out_cnn3d = cnn3d(x)
    assert out_cnn3d.shape == (batch_size, 2)

    # 4. ViT Encoder
    vit = ViTEncoder(seq_len=6, d_model=64, n_layers=2, n_heads=2)
    tokens = torch.randn(batch_size, 6, 64)
    cls_out, attn = vit(tokens, return_attn=True)
    assert cls_out.shape == (batch_size, 64)
    assert attn is not None

    # 5. Hybrid 3D-CNN + ViT
    hybrid = Hybrid3DCNNViT(
        in_channels=1,
        pca_components=c_pca,
        patch_size=patch_size,
        n_classes=2,
        token_mode="spectral_groups",
        d_model=64,
        n_layers=2,
        n_heads=2,
        predict_horizon=True
    )
    logits, risk, attn = hybrid(x, return_attn=True)
    assert logits.shape == (batch_size, 2)
    assert risk.shape == (batch_size, 1)
    assert attn is not None

def test_overfit_subset():
    """Verify model can easily overfit and reach near-zero loss on a 16-sample batch."""
    torch.manual_seed(42)
    x = torch.randn(16, 1, 24, 11, 11)
    y = torch.randint(0, 2, (16,))

    model = HyperspectralCNN3D(in_channels=1, pca_components=24, n_classes=2)
    criterion = FocalLoss(gamma=2.0)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)

    initial_loss = float(criterion(model(x), y))
    for _ in range(50):
        optimizer.zero_grad()
        out = model(x)
        loss = criterion(out, y)
        loss.backward()
        optimizer.step()

    final_loss = float(criterion(model(x), y))
    assert final_loss < 0.15, f"Model failed to overfit: initial {initial_loss:.4f}, final {final_loss:.4f}"
    assert final_loss < initial_loss * 0.2

def test_checkpoint_reproducibility(tmp_path):
    ckpt_path = tmp_path / "model_test.pt"
    model = SpectralMLP(in_features=24, n_classes=2)
    model.eval()
    x = torch.randn(4, 1, 24, 11, 11)

    out_orig = model(x).detach()
    torch.save({"model_state_dict": model.state_dict()}, str(ckpt_path))

    model_loaded = SpectralMLP(in_features=24, n_classes=2)
    model_loaded.eval()
    ckpt = torch.load(str(ckpt_path))
    model_loaded.load_state_dict(ckpt["model_state_dict"])
    out_loaded = model_loaded(x).detach()

    assert torch.allclose(out_orig, out_loaded, atol=1e-6)