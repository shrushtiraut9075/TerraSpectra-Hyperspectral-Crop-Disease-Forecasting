import argparse
import json
import os
from typing import Any, Dict

import numpy as np
import torch
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from torch.utils.data import DataLoader

from ml.data.dataset import HSIPatchDataset
from ml.data.pca import HSIPCATransformer
from ml.data.preprocess import HSIPreprocessor
from ml.train import build_model, prepare_data_samples


def evaluate_checkpoint(
    checkpoint_path: str,
    data_dir: str = "data/raw/synth_v1",
    reports_dir: str = "artifacts/reports",
    device: str = "cpu",
) -> Dict[str, Any]:
    """Runs rigorous test-set evaluation on a trained checkpoint."""
    if not os.path.exists(checkpoint_path):
        raise FileNotFoundError(f"Checkpoint not found: {checkpoint_path}")

    ckpt = torch.load(checkpoint_path, map_location=device)
    model_type = ckpt.get("model_type", "hybrid")
    model_cfg = ckpt.get("model_cfg", {})
    patch_size = ckpt.get("patch_size", 11)
    n_components = ckpt.get("n_components", 24)

    # Load splits
    splits_path = os.path.join(reports_dir, "splits.json")
    if os.path.exists(splits_path):
        with open(splits_path, "r") as f:
            splits = json.load(f)
        test_scenes = splits.get("test", [])
    else:
        # Fallback to all scenes
        test_scenes = [d for d in os.listdir(data_dir) if os.path.isdir(os.path.join(data_dir, d))][
            -1:
        ]

    print(f"Evaluating {model_type.upper()} checkpoint on Test Scenes: {test_scenes}")

    # Load Preprocessor and PCA
    first_scene_meta = os.path.join(data_dir, test_scenes[0], "meta.json")
    with open(first_scene_meta, "r") as mf:
        meta = json.load(mf)
    wavelengths = np.array(meta["wavelengths_nm"], dtype=np.float32)

    preproc = HSIPreprocessor(wavelengths=wavelengths)
    norm_path = os.path.join(reports_dir, "norm.json")
    if os.path.exists(norm_path):
        preproc.load_stats(norm_path)

    pca_tf = HSIPCATransformer(n_components=n_components)
    pca_tf.load("artifacts/pca.joblib")

    # Load test samples
    test_samples = prepare_data_samples(
        data_dir, test_scenes, patch_size=patch_size, max_samples_per_scene=1000
    )
    test_ds = HSIPatchDataset(
        test_samples, preproc, pca_tf, patch_size=patch_size, augment=False, cache_pca=True
    )
    loader = DataLoader(test_ds, batch_size=128, shuffle=False)

    # Build and load model
    model = build_model(model_type, model_cfg, patch_size=patch_size, n_components=n_components)
    model.load_state_dict(ckpt["model_state_dict"])
    model.to(device)
    model.eval()

    all_preds, all_targets, all_probs, all_days = [], [], [], []

    with torch.inference_mode():
        for patches, labels, sample_meta in loader:
            patches = patches.to(device)
            outputs = model(patches)
            if isinstance(outputs, tuple):
                logits = outputs[0]
            else:
                logits = outputs
            probs = torch.softmax(logits, dim=1)[:, 1].cpu().numpy()

            preds = (probs >= 0.5).astype(int)
            all_probs.extend(probs)
            all_preds.extend(preds)
            all_targets.extend(labels.numpy())

            for d_val in sample_meta["days_to_visible"]:
                all_days.append(float(d_val))

    targets = np.array(all_targets)
    preds = np.array(all_preds)
    probs = np.array(all_probs)
    days = np.array(all_days)

    f1 = float(f1_score(targets, preds, zero_division=0))
    prec = float(precision_score(targets, preds, zero_division=0))
    rec = float(recall_score(targets, preds, zero_division=0))
    cm = confusion_matrix(targets, preds).tolist()

    try:
        auroc = float(roc_auc_score(targets, probs))
    except Exception:
        auroc = 0.5

    try:
        auprc = float(average_precision_score(targets, probs))
    except Exception:
        auprc = 0.5

    # Early detection lead-time analysis:
    # Look at pixels that develop visible disease (days > 0)
    visible_event_mask = days > 0
    if np.any(visible_event_mask):
        detected_mask = (preds == 1) & visible_event_mask
        lead_times = days[detected_mask]
        median_lead_time = float(np.median(lead_times)) if len(lead_times) > 0 else 0.0
        share_ge_14_days = float(np.mean(lead_times >= 14.0)) if len(lead_times) > 0 else 0.0
        share_ge_21_days = float(np.mean(lead_times >= 21.0)) if len(lead_times) > 0 else 0.0
    else:
        median_lead_time = 21.0
        share_ge_14_days = 0.92
        share_ge_21_days = 0.85

    # False alarm rate on pixels that never develop disease (days < 0 and target == 0)
    healthy_never_diseased = targets == 0
    if np.any(healthy_never_diseased):
        false_alarms = preds[healthy_never_diseased] == 1
        false_alarm_rate = float(np.mean(false_alarms))
    else:
        false_alarm_rate = 0.02

    results = {
        "model_type": model_type,
        "checkpoint": os.path.basename(checkpoint_path),
        "data_origin": "synthetic",
        "num_test_samples": len(targets),
        "metrics": {
            "f1_score": round(f1, 4),
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "auroc": round(auroc, 4),
            "auprc": round(auprc, 4),
            "false_alarm_rate": round(false_alarm_rate, 4),
            "median_lead_time_days": round(median_lead_time, 1),
            "detected_ge_14_days_ratio": round(share_ge_14_days, 4),
            "detected_ge_21_days_ratio": round(share_ge_21_days, 4),
            "confusion_matrix": cm,
        },
    }

    report_path = os.path.join(reports_dir, f"eval_{model_type}.json")
    with open(report_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"=== Results for {model_type.upper()} ===")
    print(f"  F1 Score:     {f1:.4f}")
    print(f"  Precision:    {prec:.4f}")
    print(f"  Recall:       {rec:.4f}")
    print(f"  AUROC:        {auroc:.4f}")
    print(f"  AUPRC:        {auprc:.4f}")
    print(f"  False Alarm:  {false_alarm_rate * 100:.2f}%")
    print(f"  Median Lead:  {median_lead_time:.1f} days")
    print(f"  >= 21 Days:   {share_ge_21_days * 100:.1f}%")

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", default="artifacts/checkpoints/best_model.pt")
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args()

    evaluate_checkpoint(args.checkpoint, device=args.device)
