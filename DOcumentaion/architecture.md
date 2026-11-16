# Architecture — TerraSpectra

## 1. High-Level View

```
┌──────────────────────┐    ┌────────────────────────────────┐    ┌──────────────────────────┐
│  Data Sources        │    │  ML & Data Layer (Python)      │    │  Serving Layer (FastAPI) │
│  - Synthetic cubes   │───▶│  Rasterio/GDAL ingest          │───▶│  /scenes  /jobs          │
│  - HDF5 / GeoTIFF    │    │  Normalize → PCA → Tiles       │    │  /results /analytics     │
│  - Public benchmarks │    │  3D-CNN + ViT (PyTorch)        │    │  Async job queue         │
└──────────────────────┘    │  Train / Evaluate / Checkpoint │    └────────────┬─────────────┘
                            └────────────────────────────────┘                 │ REST / GeoJSON / PNG tiles
                                                                               ▼
                                                              ┌──────────────────────────────┐
                                                              │  Web Dashboard (React)       │
                                                              │  Deck.gl + Mapbox/MapLibre   │
                                                              │  Heatmap · Analytics · Time  │
                                                              └──────────────────────────────┘
```

## 2. Components

### 2.1 Data Pipeline (`ml/data`)
- **Readers:** `rasterio` for GeoTIFF, `h5py` for HDF5. Always windowed reads.
- **Synthetic generator:** builds a cube `(H, W, B)` with a soil/vegetation spectral base, spatially correlated stress patches, noise, and a time series of acquisitions with a known disease onset.
- **Preprocessing:** no-data masking, bad-band removal, reflectance scaling, per-band standardization (stats from train set).
- **PCA:** `IncrementalPCA` fitted on sampled training pixels; transform persisted (`artifacts/pca.joblib`).
- **Tiling:** overlapping tiles (e.g., 64×64 with 16 px overlap) with geotransform preserved per tile.
- **Dataset class:** returns `(patch[1, C, h, w], label, meta)` where the patch is a spatial-spectral cube for the 3D-CNN.

### 2.2 Model (`ml/models`)
- **Stem:** 3D convolutions over `(spectral, height, width)` capture local spatial-spectral features.
- **Tokenization:** feature map is flattened into tokens (spectral-group or spatial tokens).
- **Transformer encoder:** ViT-style self-attention across tokens to capture long-range spectral correlations.
- **Head:** per-patch center-pixel classifier (healthy / stressed) plus a continuous risk score; optional days-to-onset regression.
- **Training:** AdamW, cosine schedule, mixed precision, class-imbalance handling (focal loss or weighted CE).

### 2.3 Inference Service (`api`)
- FastAPI app with a pluggable job runner (start with `BackgroundTasks` / thread pool; upgrade path to Celery/RQ).
- Scene registry (SQLite for MVP; metadata only, rasters stay on disk).
- Tiled inference: stream tiles → batch → GPU → write to output raster window → feather overlaps.
- Output formats: single-band risk GeoTIFF (COG if stretch), GeoJSON polygons for risk zones, optional XYZ PNG tiles.

### 2.4 Web Dashboard (`web`)
- React + TypeScript + Vite.
- Deck.gl layers on a MapLibre/Mapbox base: `BitmapLayer`/`TileLayer` for the heatmap raster, `GeoJsonLayer` for zones, terrain for 3D.
- State: TanStack Query for API data, Zustand for UI state.
- Panels: Scene picker, Timeline slider, Risk threshold, Analytics sidebar (Recharts or Plotly).

## 3. Data Flow

1. **Ingest:** user (or script) registers a scene (`POST /scenes`) pointing to a cube on disk or uploading it.
2. **Preprocess:** API/worker applies the saved normalization and PCA window by window.
3. **Infer:** `POST /scenes/{id}/jobs` starts tiled inference; job status polled via `GET /jobs/{id}`.
4. **Stitch:** tile outputs are blended with a weighted window into a full-scene risk raster.
5. **Publish:** risk raster + zones GeoJSON + analytics JSON saved under `data/results/{scene_id}/`.
6. **Visualize:** frontend requests results and draws the overlay; timeline requests multiple scenes of the same field.

## 4. Coordinate Reference Systems (critical)

- Store rasters in their native projected CRS (e.g., UTM).
- At the **API boundary** reproject outputs/GeoJSON to **EPSG:4326** for the web map.
- Keep geotransform and CRS in raster metadata; never hardcode corner coordinates in the frontend.
- Validation: place 3+ ground control points in the synthetic scene and assert overlay pixel positions match their lat/lon (this is the GIS Validation evidence).

## 5. Memory Strategy (critical)

- Windowed reads only; never `read()` the whole cube.
- Store preprocessed data as chunked Zarr or HDF5 with chunks aligned to tile size.
- `Dataset.__getitem__` reads one patch; `DataLoader` uses workers and pinned memory.
- Mixed precision (`torch.autocast`), small patches, gradient accumulation.
- Log `peak_rss_mb` and `torch.cuda.max_memory_allocated()` per epoch (Extraction Audit evidence).

## 6. Repository Layout

```
terraspectra/
├── AGENTS.md
├── README.md
├── docs/                      # this docs pack
├── configs/
│   ├── data.yaml
│   ├── model.yaml
│   └── train.yaml
├── ml/
│   ├── data/                  # readers, synth generator, preprocess, pca, tiling, dataset
│   ├── models/                # cnn3d.py, vit.py, hybrid.py, losses.py
│   ├── train.py
│   ├── evaluate.py
│   ├── infer.py               # tiled inference + stitching
│   └── utils/                 # seed, logging, memory profiling, geo helpers
├── api/
│   ├── main.py
│   ├── routers/               # scenes.py, jobs.py, results.py, analytics.py
│   ├── services/              # inference_service.py, geo_service.py, jobs.py
│   ├── schemas.py
│   └── settings.py
├── web/
│   ├── src/
│   │   ├── components/        # Map, HeatmapLayer, Timeline, AnalyticsPanel, SceneList
│   │   ├── hooks/
│   │   ├── api/
│   │   └── App.tsx
│   └── vite.config.ts
├── data/                      # git-ignored: raw, processed, results
├── artifacts/                 # git-ignored: checkpoints, pca.joblib, reports
├── tests/
│   ├── ml/  api/  web/
├── docker-compose.yml
├── pyproject.toml / requirements.txt
└── Makefile
```

## 7. Tech Stack and Versions (pin them)

| Layer | Choice | Notes |
|---|---|---|
| Language | Python 3.11, TypeScript 5 | |
| Geo | rasterio, GDAL, pyproj, shapely, h5py, zarr | GDAL install is the usual pain point; prefer conda or the official GDAL wheel/Docker image |
| ML | PyTorch 2.x, scikit-learn, einops | `timm` optional for ViT blocks |
| API | FastAPI, Uvicorn, Pydantic v2 | |
| Frontend | React 18, Vite, Deck.gl 9, MapLibre GL (Mapbox optional), Recharts/Plotly | Mapbox needs a token; MapLibre does not |
| Tooling | pytest, ruff, mypy, ESLint, Prettier, Vitest | |

## 8. Key Design Decisions

| Decision | Reason |
|---|---|
| Synthetic-first data | Real labelled pre-symptomatic data is rare; assignment permits mock data |
| PCA before the network | Cuts 200+ bands to ~20–30 components, making 3D conv tractable |
| Hybrid 3D-CNN + ViT | CNN captures local spatial-spectral texture; ViT captures long-range spectral correlation |
| Tiling with overlap and feathering | Avoids seams and memory spikes |
| Async jobs | Large scenes take longer than an HTTP request should |
| MapLibre by default | No token or billing needed; Mapbox can be swapped in |
| EPSG:4326 at API edge | Keeps frontend simple and consistent |

## 9. Failure Modes and Handling

| Failure | Handling |
|---|---|
| GPU out of memory | Auto-reduce batch size, fall back to CPU, return clear job error |
| Corrupt or unsupported raster | Validate on registration; return 422 with reason |
| CRS missing | Reject, or require explicit `crs` on registration |
| Job crash | Persist job state `failed` with traceback id; never hang in `running` |
| Frontend large payloads | Serve tiles or simplified polygons, not raw per-pixel JSON |

## 10. Security and Config

- No secrets in git; `.env` for tokens (Mapbox optional).
- CORS limited to the web origin.
- Upload size limits and file-type checks.
- Paths sanitized; scenes referenced by ID, never by raw user-provided filesystem path.
