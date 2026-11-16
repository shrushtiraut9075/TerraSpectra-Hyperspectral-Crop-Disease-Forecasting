# PRD — TerraSpectra: Hyperspectral Crop Disease Forecasting

**Version:** 1.0 · **Owner:** Shrushti Raut (@shrushtiraut9075) · **Program:** Infotact Solutions, Advanced DS & ML Engineering (Vol. II) · **Duration:** 4 weeks + 2 review gates

---

## 1. Problem Statement

Conventional satellite crop monitoring relies on RGB or simple infrared imagery (e.g., NDVI). These approaches detect disease only **after** leaves turn yellow or brown, which is too late to save the harvest. Standard 2D CNNs cannot exploit the depth of information in 200+ spectral bands, where subtle chemical changes (chlorophyll, water, pigment content) appear well before visible symptoms.

## 2. Vision

An agricultural analyst opens TerraSpectra, sees a 1,000-acre farm in 3D, and finds a specific ~5-acre zone highlighted in red with a prediction: **fungal blight likely in ~3 weeks**, before any visible symptom. The analyst can target pesticide application to that zone only.

## 3. Target Users

| Persona | Need |
|---|---|
| Agricultural analyst (primary) | See which zones are at risk, how many acres, and why |
| Farm manager | Decide where and when to apply preventative treatment |
| ML reviewer / mentor (Infotact) | Verify the pipeline, model, and dashboard meet the review gates |

## 4. Goals

1. Ingest multi-gigabyte hyperspectral cubes (GeoTIFF / HDF5) without running out of memory.
2. Reduce 200+ bands to a tractable representation (PCA) while keeping the signal.
3. Train a hybrid **3D-CNN + Vision Transformer** to classify healthy vs. chemically stressed pixels and forecast disease risk.
4. Serve inference through a **FastAPI** service that tiles large rasters and stitches results.
5. Render predictions as a heatmap on a **React + Deck.gl** 3D map, with an analytics panel and a historical timeline slider.

## 5. Non-Goals

- Real-time satellite acquisition or orbit tasking.
- Pesticide dosage recommendations or agronomic advice beyond highlighting risk zones.
- Mobile app, multi-tenant accounts, billing.
- Claiming validated real-world 3-week lead time without real longitudinal labelled data.

## 6. Scope

### In scope (MVP)
- Synthetic hyperspectral cube generator with controllable disease onset (the "mock data" the assignment allows).
- Optional benchmark on a public hyperspectral dataset (Indian Pines / Salinas) for model sanity.
- Data pipeline: read, normalize, PCA, patch/tile extraction.
- Model: 3D-CNN, then 3D-CNN + ViT hybrid; training, evaluation, checkpoints.
- API: health, upload/register scene, run inference (async job), fetch result as GeoJSON/PNG tiles, fetch analytics.
- Dashboard: 3D map, heatmap overlay, analytics sidebar (acreage at risk, anomaly types), timeline slider.

### Stretch
- Attention-map / band-importance explanation overlay.
- Cloud-Optimized GeoTIFF (COG) output and server-side tile serving.
- Docker Compose one-command run.

## 7. Functional Requirements

| ID | Requirement | Priority |
|---|---|---|
| FR-1 | Read hyperspectral cubes from GeoTIFF and HDF5 with windowed (chunked) reads | Must |
| FR-2 | Normalize reflectance, mask invalid/no-data and noisy water-absorption bands | Must |
| FR-3 | Apply PCA (fit on train set only) and persist the fitted transform | Must |
| FR-4 | Generate synthetic cubes with ground-truth stress masks and onset dates | Must |
| FR-5 | Train hybrid model; log metrics; save best checkpoint | Must |
| FR-6 | Tiling inference with overlap and seamless stitching | Must |
| FR-7 | REST API with async job status for large scenes | Must |
| FR-8 | Heatmap overlay aligned to real GPS coordinates (CRS-correct) | Must |
| FR-9 | Analytics panel: total acres at risk, per-class anomaly breakdown | Must |
| FR-10 | Timeline slider across multiple acquisition dates | Must |
| FR-11 | Risk threshold control in UI | Should |
| FR-12 | Explainability (attention / band importance) | Could |

## 8. Non-Functional Requirements

- **Memory:** Training and inference never load a full cube into RAM; use windowed reads and batch generators. Peak RAM target documented in the mid-project audit.
- **Performance:** Inference on a 1,000-acre synthetic scene completes within a documented time on the available GPU (CPU fallback allowed but slower).
- **Reproducibility:** Fixed seeds, pinned dependencies, config-driven runs.
- **Accuracy of geo-alignment:** Overlay error under one pixel at the scene's native resolution.
- **Honesty:** UI and reports label synthetic vs. real data.

## 9. Success Metrics

| Metric | Target (synthetic data) |
|---|---|
| Pixel-level F1 (stressed class) | ≥ 0.85 on held-out scenes |
| ViT-hybrid vs. 3D-CNN-only | Measurable improvement, reported honestly even if small |
| Early-warning lead time | Detect stress ≥ N days before ground-truth visible onset (N set by generator, default 21) |
| Tiling stitch seam error | No visible seams; max prediction difference at tile borders under 2% |
| Dashboard | Smooth pan/zoom with heatmap of ≥ 1M cells using Deck.gl layers |

## 10. Review Gates

**Mid-Project Review (end of Week 2):**
- *Extraction Audit (ML):* prove the pipeline handles the memory requirements of 3D tensor batches.
- *GIS Validation (Frontend):* prove the Deck.gl overlay aligns with real-world GPS coordinates.

**Final Review (end of Week 4):**
- ML: advanced fusion of geospatial data engineering and multi-dimensional deep learning.
- Frontend: professional, visually polished agricultural intelligence platform.

## 11. Assumptions & Risks

| Risk | Mitigation |
|---|---|
| No real labelled disease data | Synthetic generator + public benchmark; label honestly |
| Cubes too large for memory | Windowed reads, memory-mapped arrays, chunked HDF5 |
| 3D-CNN GPU memory blowup | Small patch sizes, mixed precision, gradient accumulation |
| CRS/projection misalignment | Single source of truth for CRS (EPSG:4326 at the API boundary), tests with known GCPs |
| Overfitting synthetic artefacts | Vary noise, illumination, soil background; include a public-dataset check |
| Deck.gl performance | Aggregate or use binary attributes and tiled layers |

## 12. Deliverables

1. Source code (monorepo: `ml/`, `api/`, `web/`).
2. Trained checkpoint(s) and evaluation report.
3. Running demo (local or Docker Compose).
4. Mid-project and final review evidence (see `testing.md`).
5. Short technical report / README with results and limitations.
