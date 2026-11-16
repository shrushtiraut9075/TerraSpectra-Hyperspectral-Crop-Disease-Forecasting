# prompt.md — TerraSpectra Prompts for Antigravity

Paste the **Master Prompt** first. Then use one **Phase Prompt** at a time. Do not move to the next phase until the exit check passes.

---

## MASTER PROMPT (paste once at the start)

```
You are a senior ML + full-stack engineer building "TerraSpectra: Hyperspectral Crop Disease Forecasting" for an Infotact Solutions DS/ML engineering project.

GOAL
Predict crop disease ~3 weeks before visible symptoms from hyperspectral imagery (200+ bands) using a hybrid 3D-CNN + Vision Transformer, serve it through FastAPI, and show it as a 3D disease-risk heatmap on a React + Deck.gl dashboard with analytics and a historical timeline.

READ FIRST (in /docs)
PRD.md, architecture.md, data-pipeline.md, model-spec.md, api-spec.md, frontend-spec.md, plan.md, tasks.md, testing.md, dos-and-donts.md. AGENTS.md is in the repo root. These files are the source of truth. If you want to deviate, ask me first and update the doc.

STACK
Python 3.11, PyTorch 2.x, rasterio/GDAL, h5py, zarr, scikit-learn, FastAPI, Pydantic v2.
React 18 + TypeScript + Vite, Deck.gl 9, MapLibre GL, TanStack Query, Zustand, Tailwind, Recharts.

NON-NEGOTIABLE RULES
1. Memory: windowed reads only. Never load a full cube into RAM.
2. Geo: preserve CRS and affine transform end to end. Reproject to EPSG:4326 only at the API boundary. Never hardcode coordinates.
3. Leakage: split by scene or spatial block. Fit normalization and PCA on the training split only.
4. Data is SYNTHETIC unless stated. Build a physically plausible synthetic generator (healthy / soil / early-stress / visible-disease spectra, spatial stress fields, noise, time series, ground-truth labels, ground control points). Label data origin in the UI and every report.
5. Never invent metrics, screenshots, or audit numbers. Every reported number must come from a logged run.
6. Build baselines (spectral MLP, 2D-CNN, 3D-CNN) before the hybrid and report them side by side, mean ± std over 3 seeds.
7. Do not change the API contract in api-spec.md without updating the spec and asking me.
8. Two review gates exist: Mid-Project (Extraction Audit + GIS Validation) and Final. Do not start Week 3 before memory_audit.md and gis_validation.md exist.

HOW TO WORK
- One task ID from tasks.md at a time.
- For each task: state the ID and a 3-5 line plan, implement in small steps with tests, run lint and tests, tick the task in tasks.md, then report files changed, tests run with results, and open issues.
- Ask me before changing architecture, schemas, or adding heavy dependencies.
- Prefer the simplest implementation that satisfies the spec; note upgrade paths.
- Commit format: "T<id>: <what>".

START
Do Phase 0 (T0.1 to T0.5) now. Show the folder tree and the Makefile when done. Stop and wait for my go-ahead before Phase 1.
```

---

## PHASE 0 — Setup

```
Execute Phase 0 from tasks.md (T0.1-T0.5).
- Create the monorepo layout from architecture.md section 6.
- Provide environment.yml (conda-forge: python 3.11, gdal, rasterio, pytorch, etc.) and a Dockerfile alternative. Pin versions.
- Configure ruff, mypy, pytest, pre-commit; ESLint + Prettier for web.
- Makefile targets: dev, test, lint, synth, train, eval, serve, web, demo, audit.
- Write configs/data.yaml, model.yaml, train.yaml with sensible defaults from the docs.
- Add placeholder tests so `make test` passes.
Exit check: `make test` and `make lint` pass; `make dev` starts stub API and web.
```

## PHASE 1A — Data & ML (Week 1)

```
Execute T1.1-T1.9.
1. Synthetic generator (ml/data/synth.py) per data-pipeline.md section 3: 224 bands (400-2500 nm), healthy/soil/stress spectral models, canopy mixing, spatially coherent stress fields, noise, T dates, labels (healthy / stressed-invisible / visible), days_to_visible raster, GCPs in meta.json, deterministic by seed. Georeference to a real UTM zone and document which.
2. Write tiled, compressed GeoTIFFs and one chunked HDF5 variant.
3. Windowed readers with validation (CRS, dtype, nodata, band count).
4. Preprocessing: nodata mask, bad-band removal, reflectance scaling, train-only per-band standardization.
5. IncrementalPCA (fit on train sample), persist, report explained variance, choose C for >=99% variance.
6. Scene/block-level splits with a buffer gap and a leakage test.
7. HSIPatchDataset (lazy per-worker file handles, class-balanced sampler, augmentations) and DataLoader.
8. Save spectral-signature plots and the PCA variance curve to artifacts/reports/.
9. Tests: determinism, geotransform round trip, split disjointness.
Exit check: iterate one full epoch of patches from a cube larger than the configured RAM cap; PCA round trip works; all tests pass.
```

## PHASE 1B — Frontend scaffolding (Week 1)

```
Execute T1.10-T1.14 using frontend-spec.md and api-spec.md.
- Vite + React + TS + Tailwind; layout shell: top bar, left panel, map, right panel, bottom timeline placeholder. Dark, data-first design with one green accent; the risk colour ramp is reserved for data.
- MapView with Deck.gl over MapLibre, 3D pitch, terrain toggle.
- Farm boundary + grid layer from the generator's metadata GeoJSON (no hardcoded coordinates).
- Mock API with MSW matching api-spec.md exactly, using fixtures derived from the generator.
- Layer toggle panel and a persistent DataOriginBadge.
Exit check: the map shows the farm in the right place, tilted in 3D, with toggles working.
```

## PHASE 2A — 3D-CNN (Week 2)

```
Execute T2.1-T2.7 using model-spec.md.
- Baselines: spectral MLP, 2D-CNN. Then 3D-CNN (ml/models/cnn3d.py).
- Training loop: AMP, class balance or focal loss (not both blindly), AdamW + warmup + cosine, early stopping on val F1, best+last checkpoints with config, git hash, artefact hashes, resume support.
- evaluate.py: precision, recall, F1 (stressed), AUROC, AUPRC, confusion matrix on the scene-level test split, run once at the end.
- Log peak RSS, CUDA peak memory, throughput per epoch.
- Run training on a cube larger than a RAM cap (ulimit or container limit) and record the result.
- Draft the model card.
Exit check: 3D-CNN vs spectral MLP compared honestly on held-out scenes; memory logs exist.
```

## PHASE 2B — Heatmap rendering (Week 2)

```
Execute T2.8-T2.10.
- RiskLayer via TileLayer + BitmapLayer from XYZ PNG tiles (mock), colour ramp green->yellow->orange->red, transparent below threshold, opacity slider, colour-blind-safe alternative.
- ThresholdControl (debounced) and ZonesLayer with hover tooltip.
- GCP debug overlay toggle drawing markers from scene metadata.
Exit check: coloured heatmap overlays the 3D map from the mock backend and stays aligned at pitch 0 and 60 degrees.
```

## MID-PROJECT REVIEW GATE

```
Execute T2.11-T2.13. Do not start Week 3 until both files exist.
1. artifacts/reports/memory_audit.md (Extraction Audit): cube size on disk vs peak RSS in preprocessing and training; batch tensor shape, dtype, bytes; CUDA peak; AMP on/off comparison; a completed run under an enforced RAM cap on data larger than the cap; throughput. Use only logged numbers.
2. artifacts/reports/gis_validation.md (GIS Validation): GCP table with lat/lon, expected raster row/col, observed row/col, error in pixels (must be under 1 pixel); screenshots at three zoom levels and two pitches; note on CRS handling and pixel-center vs corner convention.
Summarise gaps honestly. Stop and wait for my review.
```

## PHASE 3A — Vision Transformer (Week 3)

```
Execute T3.1-T3.7.
- ViT encoder and hybrid 3D-CNN + ViT (vit.py, hybrid.py) with token_mode configurable (spectral-group or spatial) per model-spec.md section 3.2.
- Horizon risk head: label = days_to_visible <= 21 while currently not visible.
- Train 3D-CNN and hybrid over 3 seeds each; produce a comparison table (MLP, 2D-CNN, 3D-CNN, hybrid) with mean ± std.
- Early-detection metrics: lead-time distribution (median, share detected >=14 and >=21 days ahead), false-alarm rate on never-diseased pixels, zone-level IoU.
- Stack-of-dates temporal input.
- Attention extraction with a perturbation check before claiming band-group importance.
- Calibration: reliability diagram, ECE, temperature scaling.
If the hybrid does not beat the 3D-CNN, say so and explain likely reasons.
```

## PHASE 3B — Analytics panel (Week 3)

```
Execute T3.8-T3.10.
- AnalyticsPanel: acres at risk (large), percent of field, zone count.
- Sortable zones table; click a zone to fly the map there and highlight the row.
- AnomalyChart (hidden when the API returns no anomalies, never fake values) and RiskHistogram.
- Threshold changes must update panel and map within ~300 ms after debounce.
```

## PHASE 4A — Tiling, API, Docker (Week 4)

```
Execute T4.1-T4.8 using api-spec.md exactly.
- ml/infer.py: tiled inference (tile 256, overlap 32) with 2D Hann blending and a weight raster; torch.inference_mode; progress callback.
- Seam test: border prediction difference under 2% of range; tiled output equals single-pass output on a small scene within tolerance.
- FastAPI: health, scenes (register + upload), jobs (create, status, cancel), results (latest, risk.tif, zones.geojson), XYZ tiles, analytics, field timeline. Model loaded once in lifespan; inference off the event loop; one GPU job at a time.
- SQLite job persistence; jobs left "running" at startup become "failed".
- source_ref resolved inside DATA_ROOT; reject traversal.
- Contract tests covering every error code.
- Dockerfiles and docker-compose.yml (api + web).
- Final evaluation report and model card.
```

## PHASE 4B — Frontend polish (Week 4)

```
Execute T4.9-T4.13.
- Swap MSW mocks for the real API via VITE_API_BASE_URL.
- TimelineSlider with play/pause (1.2 s per step, preload next tiles), keyboard arrows, TrendSparkline of acres-at-risk.
- Template-based natural-language summary from analytics JSON (no LLM; numbers must be exact), e.g. "4.8% of the field (48 acres) shows early stress signatures; largest zone 12.1 acres in the north-east."
- Responsive layout (drawers below 1024 px), accessibility pass, empty/error/loading states.
- One Playwright smoke test: load, select field, move timeline, acres value changes.
```

## FINAL REVIEW

```
Execute T5.1-T5.4.
- `make demo`: generate a fresh synthetic scene, run tiled inference, start API and web, and open the dashboard.
- README with architecture diagram, results tables (from logged runs only), and a Limitations section: synthetic data, simplified spectral model, no field validation, no agronomic advice.
- Demo GIF/video and screenshots.
- Walk the acceptance checklist in testing.md; mark each item pass/fail with evidence links.
```

---

## UTILITY PROMPTS

**Debug a failing task**
```
Task T<id> fails. Here is the error: <paste>. Read the relevant spec and the code. Find the root cause (do not patch symptoms), propose the minimal fix, add a regression test, and explain what went wrong.
```

**Memory problem**
```
Training/inference hit OOM or high RSS. Profile with tracemalloc / torch.cuda.memory_summary. Check for whole-cube reads, open handles pickled to workers, large caches, and oversized patches. Propose fixes in this order: smaller patch, fewer PCA components, AMP, gradient accumulation, chunk alignment. Re-run the memory audit numbers.
```

**Geo misalignment**
```
Overlay is offset from the GCPs. Check, in order: lat/lon vs lon/lat order, CRS used at each stage, affine transform after tiling/stitching, pixel-center vs pixel-corner convention, Deck.gl bounds ordering [west, south, east, north], and tile Y scheme (XYZ vs TMS). Write a unit test with 3 GCPs that fails before the fix and passes after.
```

**Honest-results check**
```
Audit every number in README and reports. For each, point to the log file or artefact that produced it. Remove or flag anything without a source. Confirm data origin is stated next to every metric.
```

**Review my work (before a gate)**
```
Act as the Infotact reviewer. Using testing.md section 3 and the acceptance table, list what passes, what is missing, and what is weakest. Be specific and do not soften.
```
