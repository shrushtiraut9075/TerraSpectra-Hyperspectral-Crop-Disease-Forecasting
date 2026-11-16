# Model Spec — 3D-CNN + Vision Transformer Hybrid

## 1. Task Definition

| Task | Output | Loss |
|---|---|---|
| **A. Stress classification (core, Week 2)** | Per-pixel: healthy (0) vs. chemically stressed (1) | Weighted CE or focal loss |
| **B. Risk score (Week 3)** | Per-pixel probability in `[0, 1]` that the pixel becomes visibly diseased within the horizon | BCE with horizon label |
| **C. Days-to-onset (stretch)** | Per-pixel regression of days until visible symptoms | Huber loss, masked to stressed pixels |

Horizon default: **21 days**. The label for B comes from the generator (`days_to_visible <= 21` while currently not visible).

## 2. Input

`x ∈ R^{N × 1 × C × h × w}` — N patches, one channel, `C` PCA components as the "depth" axis, `h×w` spatial window (default `11×11`). Optional: stack 2–3 consecutive dates as an extra dimension or channel for temporal change (see §7).

## 3. Architecture

### 3.1 Baselines (build first, report always)
1. **Spectral-only MLP** on the center pixel's PCA vector.
2. **2D-CNN** on `(C, h, w)` as channels.
3. **3D-CNN** only.
4. **Hybrid 3D-CNN + ViT** (the target).

The ViT contribution is only meaningful if reported against baselines 1–3.

### 3.2 Hybrid design

```
Input (N,1,C,h,w)
 └─ 3D Conv block 1: Conv3d(1→16, k=(7,3,3)) → BN → GELU
 └─ 3D Conv block 2: Conv3d(16→32, k=(5,3,3)) → BN → GELU
 └─ 3D Conv block 3: Conv3d(32→64, k=(3,3,3)) → BN → GELU      (padding keeps spatial size)
 └─ Reshape: (N, 64·D', h', w') → per-token features
 └─ Tokenization: spectral-group tokens (group D' depth slices) or spatial tokens (h'·w')
 └─ Linear projection → dim d (e.g., 128)
 └─ [CLS] token + learned positional embedding
 └─ Transformer encoder × L (L=4, heads=4, MLP ratio 2–4, dropout 0.1, pre-norm)
 └─ Head: LayerNorm → Linear(d → n_outputs)
```

Notes:
- **Why tokens over the spectral axis:** attention across spectral groups models correlations between wavelength regions (e.g., red-edge vs. SWIR water) — the exact claim in the assignment ("find complex correlations across different light spectrums").
- Keep parameters modest (~0.5–2M). Larger is not better on synthetic data and risks memorizing generator artefacts.
- Expose config in `configs/model.yaml`: depths, kernel sizes, `d`, `L`, `heads`, `token_mode`.

### 3.3 Attention extraction (Week 3–4 / stretch)
- Return attention weights from the last block when `return_attn=True`.
- Aggregate to a band-group importance vector per prediction for the dashboard's "anomalies" panel.
- Caution: attention is not a faithful explanation by itself; pair with a perturbation check (zero a band group, measure score drop) before claiming importance.

## 4. Training

| Setting | Default |
|---|---|
| Optimizer | AdamW, lr 3e-4, weight decay 0.05 |
| Schedule | 5-epoch warmup + cosine decay |
| Batch size | 256 (reduce for GPU memory); use gradient accumulation |
| Precision | `torch.autocast(dtype=bfloat16 or float16)` + GradScaler if fp16 |
| Epochs | 30–60 with early stopping on val F1 (patience 8) |
| Class imbalance | Class-balanced sampler **or** focal loss (γ=2); not both blindly |
| Regularization | Dropout 0.1, stochastic depth 0.1, augmentation per `data-pipeline.md` |
| Seed | Fixed; log it |
| Checkpointing | Best val F1 and last; save config + git hash + PCA/norm artefact hashes |
| Logging | CSV + TensorBoard (or Weights & Biases if available): loss, F1, precision, recall, AUROC, peak memory |

Training loop requirements:
- Mask no-data pixels from the loss.
- Evaluate on val each epoch; run test **once** at the end with the best checkpoint.
- Resume from checkpoint supported.

## 5. Evaluation

### Metrics
- Per-pixel: precision, recall, F1 (stressed class), AUROC, AUPRC, confusion matrix.
- **Early-detection metric:** for pixels that eventually become visible, the distribution of `lead_time = visible_date − first_date_predicted_stressed`. Report median and the fraction detected ≥ 14 and ≥ 21 days ahead.
- **False alarm rate** on pixels that never become diseased (this matters: a farmer will not trust a map full of false red).
- Spatial metrics: zone-level IoU between predicted risk polygons and ground-truth zones.

### Protocol
- Scene-level / block-level splits, as in `data-pipeline.md`.
- Report mean ± std over at least 3 seeds for the baselines and the hybrid.
- Ablations: no-PCA (if feasible on a small subset), different `C`, with/without ViT, token mode.
- Robustness: add extra noise, illumination shift, and a held-out "different soil background" scene.
- Calibration: reliability diagram and ECE; apply temperature scaling if needed so the UI's risk percentage means something.

### Reporting rules
- Always state data origin (synthetic vs. public).
- Never present the synthetic F1 as real-world performance.
- If the hybrid does not beat the 3D-CNN, say so and give the likely reason.

## 6. Inference

- `ml/infer.py` exposes `predict_scene(scene_path, ckpt, out_path, tile=256, overlap=32, batch=…)`.
- Pipeline: read window → mask → norm → PCA → extract per-pixel patches (unfold or strided conv) → model → write float32 risk window.
- Blend overlapping tile outputs with a 2D Hann window and accumulate a weight raster; divide at the end.
- Use `torch.inference_mode()`; sort tiles for spatial locality; keep a tile-level progress callback for the job API.
- Deterministic: same input and checkpoint give the same output (document the tolerance for GPU nondeterminism).

## 7. Temporal Extension (Week 3–4)

Pick one and document it:
1. **Stack-of-dates input:** concatenate PCA features of dates `t−1, t` along the depth axis (change-aware).
2. **Late fusion:** per-date embeddings → small temporal transformer or GRU → risk.
3. **Difference features:** `x_t − x_{t−1}` as an extra channel.

Start with (1) — simplest and usually sufficient for the review.

## 8. Model Card (write at the end)

Include: intended use, data, metrics with confidence intervals, known failure modes (cloud/shadow, mixed pixels, different crop type, different sensor), and limits of the synthetic evaluation.
