import argparse
import json
import os
import time
from typing import Any, Dict, List, Tuple

import numpy as np
import torch
import torch.nn as nn
import yaml
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score
from torch.utils.data import DataLoader

from ml.data.dataset import HSIPatchDataset
from ml.data.pca import HSIPCATransformer
from ml.data.preprocess import HSIPreprocessor
from ml.data.readers import HSIReader
from ml.data.splits import create_scene_splits
from ml.models.cnn2d import SpatialCNN2D
from ml.models.cnn3d import HyperspectralCNN3D
from ml.models.hybrid import Hybrid3DCNNViT
from ml.models.losses import FocalLoss
from ml.models.mlp import SpectralMLP
from ml.utils.profiler import MemoryTracker
from ml.utils.seed import set_seed


def prepare_data_samples(
    data_dir: str, scene_ids: List[str], patch_size: int = 11, max_samples_per_scene: int = 1200
) -> List[Dict[str, Any]]:
    """Gathers patch coordinate samples from scenes."""
    samples = []
    half = patch_size // 2

    for scene_id in scene_ids:
        s_dir = os.path.join(data_dir, scene_id)
        if not os.path.exists(s_dir):
            continue

        meta_path = os.path.join(s_dir, "meta.json")
        with open(meta_path, "r") as mf:
            meta = json.load(mf)

        h = meta["dimensions"]["height"]
        w = meta["dimensions"]["width"]
        t_count = meta["dimensions"]["time_steps"]

        for t in range(t_count):
            tif_file = os.path.join(s_dir, f"t{t:02d}.tif")
            lbl_file = os.path.join(s_dir, f"labels_t{t:02d}.tif")
            days_file = os.path.join(s_dir, f"days_t{t:02d}.tif")

            lbl_reader = HSIReader(lbl_file)
            # Read labels window
            lbl_arr, _ = lbl_reader.read_window(0, 0, w, h)
            labels_grid = lbl_arr[0]  # (H, W)

            days_reader = HSIReader(days_file)
            days_arr, _ = days_reader.read_window(0, 0, w, h)
            days_grid = days_arr[0]  # (H, W)

            # Sample interior valid pixels
            valid_rows = np.arange(half, h - half, 4)
            valid_cols = np.arange(half, w - half, 4)

            # Stratify by class
            healthy_coords = []
            stressed_coords = []

            for r in valid_rows:
                for c in valid_cols:
                    lbl = int(labels_grid[r, c])
                    if lbl == 0:
                        healthy_coords.append((r, c))
                    else:
                        stressed_coords.append((r, c))

            # Subsample to keep dataset balanced and manageable
            n_per_class = min(
                len(healthy_coords), len(stressed_coords), max_samples_per_scene // (t_count * 2)
            )
            if n_per_class == 0 and stressed_coords:
                n_per_class = min(len(stressed_coords), 50)

            chosen_healthy = (
                [
                    healthy_coords[i]
                    for i in np.random.choice(
                        len(healthy_coords),
                        min(len(healthy_coords), max(10, n_per_class)),
                        replace=False,
                    )
                ]
                if healthy_coords
                else []
            )
            chosen_stressed = (
                [
                    stressed_coords[i]
                    for i in np.random.choice(
                        len(stressed_coords),
                        min(len(stressed_coords), max(10, n_per_class)),
                        replace=False,
                    )
                ]
                if stressed_coords
                else []
            )

            for r, c in chosen_healthy + chosen_stressed:
                samples.append(
                    {
                        "scene_id": scene_id,
                        "t": t,
                        "tif_path": tif_file,
                        "row": int(r),
                        "col": int(c),
                        "label": 1 if int(labels_grid[r, c]) > 0 else 0,
                        "days_to_visible": float(days_grid[r, c]),
                    }
                )

    return samples


def build_model(
    model_type: str, model_cfg: Dict[str, Any], patch_size: int = 11, n_components: int = 24
) -> nn.Module:
    """Instantiates model according to type."""
    if model_type == "mlp":
        return SpectralMLP(in_features=n_components, n_classes=model_cfg.get("n_classes", 2))
    elif model_type == "cnn2d":
        return SpatialCNN2D(in_channels=n_components, n_classes=model_cfg.get("n_classes", 2))
    elif model_type == "cnn3d":
        return HyperspectralCNN3D(
            in_channels=1, pca_components=n_components, n_classes=model_cfg.get("n_classes", 2)
        )
    else:  # hybrid
        vit_cfg = model_cfg.get("vit", {})
        return Hybrid3DCNNViT(
            in_channels=1,
            pca_components=n_components,
            patch_size=patch_size,
            n_classes=model_cfg.get("n_classes", 2),
            token_mode=vit_cfg.get("token_mode", "spectral_groups"),
            d_model=vit_cfg.get("d_model", 128),
            n_layers=vit_cfg.get("n_layers", 4),
            n_heads=vit_cfg.get("n_heads", 4),
            mlp_ratio=vit_cfg.get("mlp_ratio", 2.0),
            dropout=vit_cfg.get("dropout", 0.1),
            predict_horizon=model_cfg.get("head", {}).get("predict_horizon", True),
        )


def train_epoch(
    model: nn.Module,
    loader: DataLoader,
    optimizer: torch.optim.Optimizer,
    criterion: nn.Module,
    device: torch.device,
) -> Tuple[float, float]:
    model.train()
    total_loss = 0.0
    all_preds, all_targets = [], []

    for patches, labels, _ in loader:
        patches = patches.to(device)
        labels = labels.to(device)

        optimizer.zero_grad()
        outputs = model(patches)

        if isinstance(outputs, tuple):
            logits = outputs[0]
        else:
            logits = outputs

        loss = criterion(logits, labels)
        loss.backward()
        optimizer.step()

        total_loss += loss.item() * patches.size(0)
        preds = torch.argmax(logits, dim=1).detach().cpu().numpy()
        all_preds.extend(preds)
        all_targets.extend(labels.detach().cpu().numpy())

    avg_loss = total_loss / len(loader.dataset)
    f1 = f1_score(all_targets, all_preds, zero_division=0)
    return avg_loss, float(f1)


@torch.inference_mode()
def evaluate_epoch(
    model: nn.Module, loader: DataLoader, criterion: nn.Module, device: torch.device
) -> Dict[str, float]:
    model.eval()
    total_loss = 0.0
    all_preds, all_targets, all_probs = [], [], []

    for patches, labels, _ in loader:
        patches = patches.to(device)
        labels = labels.to(device)

        outputs = model(patches)
        if isinstance(outputs, tuple):
            logits = outputs[0]
        else:
            logits = outputs

        loss = criterion(logits, labels)
        total_loss += loss.item() * patches.size(0)

        probs = torch.softmax(logits, dim=1)[:, 1].cpu().numpy()
        preds = torch.argmax(logits, dim=1).cpu().numpy()

        all_probs.extend(probs)
        all_preds.extend(preds)
        all_targets.extend(labels.cpu().numpy())

    targets = np.array(all_targets)
    preds = np.array(all_preds)
    probs = np.array(all_probs)

    f1 = float(f1_score(targets, preds, zero_division=0))
    prec = float(precision_score(targets, preds, zero_division=0))
    rec = float(recall_score(targets, preds, zero_division=0))

    try:
        auroc = float(roc_auc_score(targets, probs))
    except Exception:
        auroc = 0.5

    return {
        "val_loss": total_loss / max(1, len(loader.dataset)),
        "val_f1": f1,
        "val_precision": prec,
        "val_recall": rec,
        "val_auroc": auroc,
    }


def run_training(
    model_type: str = "hybrid",
    model_cfg_path: str = "configs/model.yaml",
    train_cfg_path: str = "configs/train.yaml",
    data_cfg_path: str = "configs/data.yaml",
    seed: int = 42,
) -> Dict[str, Any]:
    set_seed(seed)
    with open(model_cfg_path, "r") as f:
        model_cfg = yaml.safe_load(f)
    with open(train_cfg_path, "r") as f:
        train_cfg = yaml.safe_load(f)
    with open(data_cfg_path, "r") as f:
        data_cfg = yaml.safe_load(f)

    device = torch.device(
        "cuda" if torch.cuda.is_available() and train_cfg.get("device") == "cuda" else "cpu"
    )
    print(f"=== Starting Training [{model_type.upper()}] on {device} (seed={seed}) ===")

    # Setup directories
    os.makedirs(train_cfg["checkpoint_dir"], exist_ok=True)
    os.makedirs(train_cfg["log_dir"], exist_ok=True)

    # 1. Discover scenes
    raw_dir = "data/raw/synth_v1"
    scene_ids = sorted([d for d in os.listdir(raw_dir) if os.path.isdir(os.path.join(raw_dir, d))])
    if not scene_ids:
        raise RuntimeError("No scenes found in data/raw/synth_v1. Run generator first.")

    # 2. Scene splits (Train / Val / Test)
    splits = create_scene_splits(
        scene_ids,
        train_ratio=data_cfg["splits"]["train_ratio"],
        val_ratio=data_cfg["splits"]["val_ratio"],
        test_ratio=data_cfg["splits"]["test_ratio"],
        seed=seed,
    )
    print(f"Splits: Train={splits['train']}, Val={splits['val']}, Test={splits['test']}")

    # Save splits manifest
    with open(os.path.join(train_cfg["log_dir"], "splits.json"), "w") as sf:
        json.dump(splits, sf, indent=2)

    # 3. Read metadata from first train scene for wavelengths
    first_train_meta = os.path.join(raw_dir, splits["train"][0], "meta.json")
    with open(first_train_meta, "r") as mf:
        first_meta = json.load(mf)
    wavelengths = np.array(first_meta["wavelengths_nm"], dtype=np.float32)

    # 4. Preprocessor fit
    preproc = HSIPreprocessor(
        wavelengths=wavelengths,
        water_vapor_ranges=data_cfg["bad_bands"]["water_vapor_ranges_nm"],
        edge_drop=data_cfg["bad_bands"]["edge_drop_bands"],
    )

    # Sample random pixels from train scenes to fit standardization
    print("Fitting standardization and IncrementalPCA on train scenes...")
    sample_pixels = []
    for s_id in splits["train"]:
        sample_tif = os.path.join(raw_dir, s_id, "t00.tif")
        reader = HSIReader(sample_tif)
        # Windowed read of central patch
        w_arr, _ = reader.read_window(20, 20, 80, 80)
        # Select good bands
        clean_w = w_arr[preproc.good_band_indices]  # (B_good, 80, 80)
        sample_pixels.append(np.transpose(clean_w, (1, 2, 0)).reshape(-1, preproc.retained_bands))

    train_pixel_matrix = np.vstack(sample_pixels)
    preproc.fit_standardization(train_pixel_matrix)
    norm_path = os.path.join(train_cfg["log_dir"], "norm.json")
    preproc.save_stats(norm_path)

    # 5. IncrementalPCA fit
    n_components = data_cfg["pca"]["n_components"]
    pca_tf = HSIPCATransformer(n_components=n_components)
    pca_report = pca_tf.fit(train_pixel_matrix)
    pca_model_path = "artifacts/pca.joblib"
    pca_tf.save(pca_model_path)
    pca_tf.plot_variance(os.path.join(train_cfg["log_dir"], "pca_variance.png"))
    print(
        f"PCA Fitted: {n_components} components explain {pca_report['total_explained_variance'] * 100:.2f}% variance"
    )

    # 6. Build Datasets
    patch_size = data_cfg["patches"]["train_size"]
    train_samples = prepare_data_samples(raw_dir, splits["train"], patch_size=patch_size)
    val_samples = prepare_data_samples(raw_dir, splits["val"], patch_size=patch_size)

    print(f"Dataset samples: Train={len(train_samples)}, Val={len(val_samples)}")

    train_ds = HSIPatchDataset(
        train_samples, preproc, pca_tf, patch_size=patch_size, augment=True, cache_pca=True
    )
    val_ds = HSIPatchDataset(
        val_samples, preproc, pca_tf, patch_size=patch_size, augment=False, cache_pca=True
    )

    train_loader = DataLoader(
        train_ds, batch_size=train_cfg["batch_size"], shuffle=True, num_workers=0, pin_memory=False
    )
    val_loader = DataLoader(
        val_ds, batch_size=train_cfg["batch_size"], shuffle=False, num_workers=0, pin_memory=False
    )

    # 7. Model, Loss, Optimizer
    model = build_model(model_type, model_cfg, patch_size=patch_size, n_components=n_components).to(
        device
    )

    if train_cfg.get("loss") == "focal":
        criterion = FocalLoss(
            gamma=train_cfg.get("focal_gamma", 2.0), alpha=train_cfg.get("focal_alpha", 0.65)
        )
    else:
        criterion = nn.CrossEntropyLoss()

    optimizer = torch.optim.AdamW(
        model.parameters(), lr=train_cfg["lr"], weight_decay=train_cfg["weight_decay"]
    )
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=train_cfg["epochs"])

    # 8. Training Loop
    profiler = MemoryTracker()
    profiler.start()

    best_val_f1 = -1.0
    patience = train_cfg.get("patience", 8)
    patience_counter = 0
    history = []

    best_ckpt_path = os.path.join(train_cfg["checkpoint_dir"], f"best_{model_type}_seed{seed}.pt")

    for epoch in range(1, train_cfg["epochs"] + 1):
        t0 = time.time()
        train_loss, train_f1 = train_epoch(model, train_loader, optimizer, criterion, device)
        val_metrics = evaluate_epoch(model, val_loader, criterion, device)
        scheduler.step()

        elapsed = time.time() - t0
        mem_stats = profiler.stats()

        epoch_record = {
            "epoch": epoch,
            "train_loss": round(train_loss, 4),
            "train_f1": round(train_f1, 4),
            "val_loss": round(val_metrics["val_loss"], 4),
            "val_f1": round(val_metrics["val_f1"], 4),
            "val_precision": round(val_metrics["val_precision"], 4),
            "val_recall": round(val_metrics["val_recall"], 4),
            "val_auroc": round(val_metrics["val_auroc"], 4),
            "peak_rss_mb": mem_stats["rss_mb"],
            "cuda_peak_mb": mem_stats["cuda_peak_mb"],
            "throughput_patches_per_sec": round(len(train_samples) / max(0.01, elapsed), 1),
        }
        history.append(epoch_record)

        print(
            f"Epoch {epoch:02d}/{train_cfg['epochs']:02d} | "
            f"Train Loss: {train_loss:.4f} F1: {train_f1:.4f} | "
            f"Val Loss: {val_metrics['val_loss']:.4f} F1: {val_metrics['val_f1']:.4f} AUROC: {val_metrics['val_auroc']:.4f} | "
            f"RAM: {mem_stats['rss_mb']:.1f}MB | {elapsed:.1f}s"
        )

        # Checkpointing
        if val_metrics["val_f1"] > best_val_f1:
            best_val_f1 = val_metrics["val_f1"]
            patience_counter = 0
            torch.save(
                {
                    "model_type": model_type,
                    "model_state_dict": model.state_dict(),
                    "epoch": epoch,
                    "val_f1": best_val_f1,
                    "val_metrics": val_metrics,
                    "model_cfg": model_cfg,
                    "n_components": n_components,
                    "patch_size": patch_size,
                    "seed": seed,
                },
                best_ckpt_path,
            )
            # Also save canonical best_model.pt
            if model_type == "hybrid":
                torch.save(
                    torch.load(best_ckpt_path),
                    os.path.join(train_cfg["checkpoint_dir"], "best_model.pt"),
                )
        else:
            patience_counter += 1
            if patience_counter >= patience:
                print(f"Early stopping triggered at epoch {epoch} (patience={patience}).")
                break

    # Save training history
    log_file = os.path.join(train_cfg["log_dir"], f"training_log_{model_type}_seed{seed}.json")
    with open(log_file, "w") as f:
        json.dump(history, f, indent=2)

    print(f"Finished {model_type} (seed={seed}). Best Val F1: {best_val_f1:.4f}")
    return {
        "model_type": model_type,
        "seed": seed,
        "best_val_f1": best_val_f1,
        "best_checkpoint": best_ckpt_path,
        "history": history,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model-type", default="hybrid", choices=["mlp", "cnn2d", "cnn3d", "hybrid"]
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--model-config", default="configs/model.yaml")
    parser.add_argument("--train-config", default="configs/train.yaml")
    parser.add_argument("--data-config", default="configs/data.yaml")
    args = parser.parse_args()

    run_training(
        model_type=args.model_type,
        model_cfg_path=args.model_config,
        train_cfg_path=args.train_config,
        data_cfg_path=args.data_config,
        seed=args.seed,
    )
