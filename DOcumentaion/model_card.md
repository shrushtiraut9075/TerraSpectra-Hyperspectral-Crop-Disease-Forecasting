# Model Card — TerraSpectra Hybrid 3D-CNN + ViT

## Model Details
- **Model Name:** TerraSpectra Hybrid 3D-CNN + Vision Transformer (`hybrid-v1`)
- **Version:** 1.0.0
- **Developers:** Shrushti Raut · Infotact Solutions
- **Release Date:** November 2026
- **Architecture:**
  - 3D-CNN Stem: 3 cascaded 3D convolution layers (kernel sizes (7,3,3), (5,3,3), (3,3,3)) capturing localized spatial-spectral geometry simultaneously.
  - Tokenizer: Depth slicing into 6 spectral-group tokens (modeling red-edge, NIR, and SWIR bands).
  - ViT Encoder: 4-layer Transformer with 4-head self-attention and learned [CLS] token.
  - Multi-task Output Heads: Binary classification (Healthy vs Stressed) and continuous 21-day disease onset probability.
- **Dimensionality Reduction:** 224 raw bands (400–2500 nm) reduced to 24 principal components using `IncrementalPCA` fitted exclusively on training scenes.

---

## Intended Use
- **Primary Domain:** Precision agriculture and computer vision for early detection of fungal blight and crop pathogens ~3 weeks before visible symptoms appear.
- **Target Users:** Agricultural analysts, farm managers, and research agronomists.
- **Out of Scope:** Automated chemical pesticide application without ground agronomic scouting; medical or forestry analysis.

---

## Factors & Evaluation Data
- **Data Origin:** Synthetic canopy radiative simulation (224 bands over 400–2500 nm) simulating red-edge blue-shift, mesophyll structure collapse (NIR plateau drop), and leaf water loss (SWIR absorption change).
- **Split Protocol:** Scene-level hold-out split (Train: `scene_000, 001, 002, 005`; Val: `scene_004`; Test: `scene_003`). No spatial pixel leakage.
- **Metrics on Held-Out Test Set:**
  - **F1 Score:** `0.9897` (Stressed class)
  - **Precision:** `0.9864`
  - **Recall:** `0.9931`
  - **AUROC:** `0.9997`
  - **False Alarm Rate:** `1.36%` on healthy crop pixels
  - **Median Early Warning Lead Time:** `21.0 days` prior to visible chlorosis

---

## Limitations & Honest Reporting
1. **Simulation Boundaries:** Ground truth is derived from a physical radiative approximation rather than multi-year longitudinal field trials. Metrics reflect synthetic simulation conditions.
2. **Atmospheric & Cloud Interference:** Cloud shadows and heavy haze will disrupt top-of-canopy reflectance. Atmospheric correction and cloud masking must precede inference.
3. **Soil Background Variation:** Strong deviations in soil mineralogy (e.g. high salinity or extreme iron content) require domain-specific fine-tuning.

