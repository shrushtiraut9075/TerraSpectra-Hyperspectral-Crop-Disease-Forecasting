# Testing & Acceptance — TerraSpectra

## 1. Test Pyramid

| Level | Tools | What |
|---|---|---|
| Unit (ML) | pytest | Generator determinism, readers, preprocessing, PCA, splits, model shapes, losses |
| Unit (API) | pytest + httpx | Services, schema validation, path safety |
| Unit (Web) | Vitest + RTL | Hooks, state, formatters, summary sentence |
| Integration | pytest + FastAPI TestClient | register → job → results on a tiny scene |
| Contract | OpenAPI + MSW fixtures | Frontend mocks equal real API shapes |
| Smoke / E2E | Playwright | Select field → move timeline → acres value changes |
| Performance | scripts in `ml/utils/bench.py` | Memory, throughput, tile latency |

Tiny fixtures: a 64×64×32-band synthetic scene committed to `tests/fixtures/` (under ~5 MB). Never commit large rasters.

## 2. Must-Pass Tests

### Data
- [ ] Same seed → identical cube and masks.
- [ ] Round trip: tile → stitch preserves CRS, transform, shape.
- [ ] No pixel from a test block appears in train.
- [ ] Normalization and PCA fitted on train only (assert via artefact metadata).
- [ ] Bad-band list length matches band metadata.

### Model
- [ ] Forward pass shape for each model variant.
- [ ] Overfit test: model reaches near-zero loss on a 64-patch subset.
- [ ] Loss ignores masked/no-data pixels.
- [ ] Checkpoint save/load reproduces outputs within tolerance.

### Inference
- [ ] Seam test: prediction difference at tile borders under 2% of range.
- [ ] Full-scene stitched output equals single-pass output on a small scene (within tolerance).
- [ ] Deterministic on CPU.

### API
- [ ] Happy path.
- [ ] Every error code in `api-spec.md` is triggered by a test.
- [ ] Path traversal in `source_ref` rejected.
- [ ] Jobs left `running` at startup become `failed`.

### Frontend
- [ ] Threshold change debounces and refetches once.
- [ ] Anomaly chart hidden for empty list.
- [ ] Timeline keyboard navigation works.
- [ ] No hardcoded coordinates (lint rule or grep test).

## 3. Review-Gate Evidence

### Extraction Audit (Mid-Project)
File: `artifacts/reports/memory_audit.md`
- Cube on disk (GB) vs. peak RSS (GB) during preprocessing and training
- Batch shape, dtype, per-batch bytes
- CUDA peak memory; AMP on/off comparison
- Run with an enforced RAM cap on data larger than the cap, completed
- Throughput (patches/s)

### GIS Validation (Mid-Project)
File: `artifacts/reports/gis_validation.md`
- GCP table: lat/lon, expected raster row/col, observed row/col, error in pixels
- Screenshots: 3 zoom levels × 2 pitches
- Statement on CRS and pixel-center convention

### Final Review
- Comparative metrics table (MLP, 2D-CNN, 3D-CNN, hybrid) mean ± std over 3 seeds
- Lead-time distribution plot; false-alarm rate
- Seam test results and tiled-vs-single-pass equivalence
- Demo GIF, screenshots, README limitations section

## 4. Acceptance Criteria (project-level)

| # | Criterion | Pass condition |
|---|---|---|
| A1 | Memory-safe pipeline | Completes on data larger than RAM cap |
| A2 | Hyperspectral ingest | GeoTIFF and HDF5 both read via windows |
| A3 | PCA | ≥ 99% variance retained (or documented tradeoff) |
| A4 | Classification | Stressed-class F1 ≥ 0.85 on held-out synthetic scenes |
| A5 | ViT value | Hybrid vs. 3D-CNN reported honestly with std |
| A6 | Early warning | Median lead time meets the generator horizon target or the gap is explained |
| A7 | Tiling | No visible seams; tolerance test passes |
| A8 | API | All endpoints and error codes covered |
| A9 | Geo alignment | GCP error under one raster pixel |
| A10 | Dashboard | Heatmap, analytics, timeline all working with real API |
| A11 | Honesty | Data-origin badge visible; limitations documented |

## 5. Commands (expected Makefile)

```
make test        # pytest + vitest
make lint        # ruff + mypy + eslint
make synth       # generate synthetic dataset
make train       # train hybrid with configs/
make eval        # evaluate best checkpoint on test split
make serve       # run FastAPI
make web         # run dashboard
make demo        # end-to-end demo on a fresh synthetic scene
make audit       # produce memory_audit.md numbers
```

## 6. CI (optional but recommended)

GitHub Actions: lint → unit tests (CPU only, tiny fixtures) → web build. GPU training is not run in CI.
