# Plan — TerraSpectra (4 Weeks + Review Gates)

Two parallel tracks, as in the Infotact brief: **ML Engineering & Data Pipeline** (PyTorch, Rasterio) and **Frontend & GIS** (React, Deck.gl). The API in Week 4 joins them, so agree on the contract in Week 1 and use mock JSON until then.

## Timeline Overview

| Phase | ML / Data track | Frontend / GIS track | Gate |
|---|---|---|---|
| **Week 0 (setup, 0.5 day)** | Repo, env, GDAL, configs, seeds | Vite app, lint, CI | — |
| **Week 1** | Data preparation: parse mock cubes (HDF5/GeoTIFF), PCA on 200+ bands | Map scaffolding: React + Deck.gl + base map, farm layers | — |
| **Week 2** | Hybrid 3D-CNN: classify healthy vs. chemically stressed pixels | Heatmap rendering from mock JSON/tiles | — |
| **Mid-Project Review** | **Extraction Audit** (memory of 3D tensor batches) | **GIS Validation** (overlay vs. real GPS) | ✅ Gate 1 |
| **Week 3** | Add Vision Transformer, compare against baselines | Analytics panel: acreage at risk, anomalies | — |
| **Week 4** | FastAPI + tiling/stitching | Timeline slider, polish, wire to real API | — |
| **Final Review** | Geospatial data engineering + multi-dimensional deep learning | Professional agricultural intelligence platform | ✅ Gate 2 |

---

## Week 0 — Setup (half a day)

**Deliverables**
- Monorepo with `ml/`, `api/`, `web/`, `configs/`, `docs/`, `tests/`.
- Environment reproducible: `environment.yml` (conda recommended for GDAL) or Dockerfile; `pyproject.toml` pinned; `package.json` lockfile.
- `ruff`, `mypy`, `pytest`, ESLint, Prettier, pre-commit.
- `AGENTS.md` in repo root; docs in `docs/`.
- Decide and write down: pixel size, scene size, UTM zone, number of bands, number of dates, split policy.

**Exit check:** `make test` runs (even with placeholder tests) and `make dev` starts web + api stubs.

---

## Week 1 — Data & Map Scaffolding

### ML track: Data Preparation
1. Synthetic generator v1 (`ml/data/synth.py`) with healthy / stressed / visible labels and GCPs.
2. Write GeoTIFFs (tiled, compressed) and one HDF5 variant to prove both readers.
3. Windowed readers for GeoTIFF and HDF5.
4. Preprocessing: no-data mask, bad-band removal, scaling, standardization stats (train only).
5. PCA (IncrementalPCA) with explained-variance report; persist artefacts.
6. Patch extraction + `HSIPatchDataset` + DataLoader; split by scene/block.
7. Notebook or report: spectral signature plots (healthy vs. stressed vs. visibly diseased), PCA variance curve.

**Exit check:** can iterate one full epoch of patches from a cube larger than a configured RAM cap; PCA transform round-trips.

### Frontend track: Map Scaffolding
1. React + Vite + Tailwind scaffold; layout shell (top bar, side panels, bottom timeline placeholder).
2. Integrate Deck.gl + MapLibre; camera, 3D pitch, base layers.
3. Render the farm boundary polygon and field grid from a static GeoJSON derived from the generator metadata.
4. Mock API layer (MSW or a static JSON server) following `api-spec.md`.

**Exit check:** map shows the farm at the right location, tilted 3D, with layer toggles.

---

## Week 2 — Model & Heatmap

### ML track: Model Architecture
1. Baselines: spectral MLP, 2D-CNN.
2. 3D-CNN in PyTorch; training loop with AMP, class balancing, logging, checkpointing.
3. Evaluation script: P/R/F1, AUROC, confusion matrix; scene-level split.
4. Memory instrumentation (peak RSS, CUDA peak) → feeds the Extraction Audit.
5. First model card draft.

**Exit check:** 3D-CNN beats the spectral MLP on held-out scenes or you document why not.

### Frontend track: Heatmap Rendering
1. `RiskLayer` consuming mock tiles/JSON grid.
2. Colour ramp, opacity slider, threshold control.
3. Zones layer with hover tooltip.
4. Ground-control-point debug overlay.

**Exit check:** coloured pixel grid overlays the 3D map from mock backend responses.

---

## 🔶 Mid-Project Review (end of Week 2)

### Extraction Audit (ML) — prove memory handling
Evidence pack in `artifacts/reports/memory_audit.md`:
- Cube size vs. peak RAM during preprocessing and training.
- Batch tensor shapes/dtype and measured GPU peak.
- A run on data larger than the RAM cap completing successfully.
- Throughput numbers and the knobs used (patch size, batch size, AMP, workers, chunking).

### GIS Validation (Frontend) — prove alignment
Evidence pack in `artifacts/reports/gis_validation.md`:
- Screenshots with GCP markers on the overlay at 3 zoom levels and at pitch 0° and 60°.
- A numeric check: GCP lat/lon → map pixel → raster pixel error under one raster pixel.
- Statement of CRS handling (native UTM → EPSG:4326 at the API).

**Go / no-go:** do not start Week 3 until both audits are written and reviewed.

---

## Week 3 — Vision Transformer & Analytics

### ML track
1. Implement hybrid 3D-CNN + ViT (token mode configurable).
2. Train, tune lightly, run 3 seeds for hybrid and the 3D-CNN baseline.
3. Add the risk-score/horizon head (21-day lead-time target).
4. Early-detection metrics: lead time, false-alarm rate.
5. Temporal input extension (stack-of-dates).
6. Attention/perturbation analysis for band-group importance.

**Exit check:** comparative results table (MLP, 2D-CNN, 3D-CNN, hybrid) with mean ± std.

### Frontend track: Analytics Panel
1. Acres-at-risk headline, zones table (sortable), risk histogram.
2. Anomaly chart wired to mock analytics (hidden when empty).
3. Zone click → fly-to + table highlight.

**Exit check:** analytics reflect threshold changes instantly.

---

## Week 4 — API, Tiling, Polish

### ML track: API & Tiling
1. `ml/infer.py` tiled inference with overlap and Hann blending; seam test.
2. FastAPI endpoints per `api-spec.md`; async jobs; SQLite persistence.
3. Result publishing: risk GeoTIFF, XYZ tiles, zones GeoJSON, analytics JSON.
4. Dockerfile(s) and `docker-compose.yml`.
5. Final evaluation, model card, technical report.

### Frontend track: Refine & Polish
1. Replace mocks with the real API.
2. Timeline slider with play/pause and trend sparkline.
3. Natural-language summary sentence (template-based).
4. Responsive layout, accessibility pass, empty/error/loading states.
5. Playwright smoke test.

---

## 🔷 Final Review

- **ML:** demo of end-to-end flow: huge synthetic scene → tiled inference → stitched risk map, with comparative metrics and lead-time results.
- **Frontend:** polished dashboard demo with 3D map, analytics, timeline.
- **Artefacts:** README with results and honest limitations, model card, memory audit, GIS validation, short demo video or GIF.

---

## Definition of Done (per task)

1. Code merged with tests passing.
2. Lint and type checks clean.
3. Relevant doc updated (`tasks.md` ticked, any spec change reflected).
4. Evidence artefact saved when the task belongs to a review gate.

## Risk Watchlist

| Risk | Early signal | Response |
|---|---|---|
| GDAL install trouble | Day 1 failures | Use conda-forge or the GDAL Docker image |
| OOM in 3D conv | CUDA OOM, killed worker | Smaller patch, fewer PCA comps, AMP, grad accumulation |
| Synthetic data too easy | Near-100% F1 | Add noise, mixed pixels, soil variety, domain shift test |
| Overlay misalignment | GCP markers off by pixels | Check axis order (lat/lon vs. lon/lat), CRS, pixel-center vs. corner convention |
| Scope creep | Explainability, compare mode eat Week 4 | Mark as stretch; protect tiling + API + timeline |
