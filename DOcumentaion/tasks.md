# Tasks — TerraSpectra (agent checklist)

Tick items as completed. IDs are stable so prompts can reference them (e.g., "do T1.4").

## Phase 0 — Setup
- [x] **T0.1** Create monorepo structure from `architecture.md` §6
- [x] **T0.2** Environment files (conda `environment.yml` or Docker) with pinned GDAL/rasterio/torch
- [x] **T0.3** Tooling: ruff, mypy, pytest, pre-commit, ESLint, Prettier, Makefile targets (`dev`, `test`, `lint`, `train`, `serve`)
- [x] **T0.4** Place `AGENTS.md` at repo root; docs under `docs/`
- [x] **T0.5** Write `configs/data.yaml`, `model.yaml`, `train.yaml` with defaults

## Phase 1 — Week 1
### Data / ML
- [x] **T1.1** Synthetic generator: spectra (healthy/soil/stress), spatial stress fields, noise, time series, labels, GCP metadata
- [x] **T1.2** Writers: tiled compressed GeoTIFF + chunked HDF5; deterministic seeding
- [x] **T1.3** Windowed readers (GeoTIFF, HDF5) with validation (CRS, dtype, nodata)
- [x] **T1.4** Preprocess: no-data mask, bad bands, scaling, per-band standardization (train-only stats)
- [x] **T1.5** IncrementalPCA fit/save/load + explained-variance report
- [x] **T1.6** Scene/block-level splits with leakage test
- [x] **T1.7** `HSIPatchDataset` + DataLoader (lazy file handles, balanced sampler, augmentations)
- [x] **T1.8** Spectral signature plots + PCA variance figure saved to `artifacts/reports/`
- [x] **T1.9** Tests: determinism, geotransform round trip, split disjointness
### Frontend / GIS
- [x] **T1.10** Vite + React + TS + Tailwind scaffold with layout shell
- [x] **T1.11** MapLibre + Deck.gl `MapView`, camera, pitch, terrain toggle
- [x] **T1.12** Farm boundary and grid layer from generator metadata GeoJSON
- [x] **T1.13** Mock API (MSW) matching `api-spec.md`
- [x] **T1.14** Layer toggle panel and `DataOriginBadge`

## Phase 2 — Week 2
### ML
- [x] **T2.1** Baselines: spectral MLP, 2D-CNN
- [x] **T2.2** 3D-CNN module (`ml/models/cnn3d.py`)
- [x] **T2.3** Training loop: AMP, class balance/focal loss, scheduler, early stopping, checkpoints, resume
- [x] **T2.4** Evaluation script and metrics (P/R/F1, AUROC, AUPRC, confusion matrix)
- [x] **T2.5** Memory instrumentation (peak RSS, CUDA peak, throughput) logged per epoch
- [x] **T2.6** Run on cube larger than RAM cap; record results
- [x] **T2.7** Draft model card
### Frontend
- [x] **T2.8** `RiskLayer` (tiles or grid) with colour ramp and opacity
- [x] **T2.9** Threshold control and `ZonesLayer` with hover tooltip
- [x] **T2.10** GCP debug overlay
### Mid-Project Gate
- [x] **T2.11** Write `memory_audit.md` (Extraction Audit)
- [x] **T2.12** Write `gis_validation.md` with screenshots and numeric error check (GIS Validation)
- [x] **T2.13** Review sign-off before Week 3

## Phase 3 — Week 3
### ML
- [x] **T3.1** ViT encoder and hybrid model (`vit.py`, `hybrid.py`) with token-mode config
- [x] **T3.2** Horizon risk head (21-day label from generator)
- [x] **T3.3** Train 3D-CNN and hybrid over 3 seeds; comparison table
- [x] **T3.4** Early-detection metrics: lead time, false-alarm rate, zone IoU
- [x] **T3.5** Stack-of-dates temporal input
- [x] **T3.6** Attention extraction + perturbation check for band-group importance
- [x] **T3.7** Calibration (reliability diagram, temperature scaling)
### Frontend
- [x] **T3.8** `AnalyticsPanel` (acres at risk, percent, zone count)
- [x] **T3.9** Zones table (sortable), click-to-fly, row highlight
- [x] **T3.10** `AnomalyChart` and `RiskHistogram`

## Phase 4 — Week 4
### ML / API
- [x] **T4.1** Tiled inference with overlap + Hann blending (`ml/infer.py`)
- [x] **T4.2** Seam test (border prediction difference under tolerance)
- [x] **T4.3** FastAPI app: health, scenes, jobs, results, tiles, analytics, timeline
- [x] **T4.4** Async job runner, SQLite persistence, restart recovery
- [x] **T4.5** Result publishing: risk GeoTIFF, XYZ tiles, zones GeoJSON, analytics JSON
- [x] **T4.6** Contract tests for all endpoints and error codes
- [x] **T4.7** Dockerfiles + `docker-compose.yml`
- [x] **T4.8** Final evaluation report and model card
### Frontend
- [x] **T4.9** Swap mocks for real API (env-configured base URL)
- [x] **T4.10** `TimelineSlider` with play/pause and `TrendSparkline`
- [x] **T4.11** Template-based natural-language summary
- [x] **T4.12** Responsive layout, a11y pass, empty/error/loading states
- [x] **T4.13** Playwright smoke test

## Phase 5 — Final Review
- [x] **T5.1** End-to-end demo script (`make demo`)
- [x] **T5.2** README with results and honest limitations
- [x] **T5.3** Demo GIF/video and screenshots
- [x] **T5.4** Final pass on `testing.md` acceptance checklist
