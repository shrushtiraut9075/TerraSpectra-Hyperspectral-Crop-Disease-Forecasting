# Data Pipeline — TerraSpectra

## 1. Goals

Turn raw hyperspectral cubes (200+ bands, multi-GB) into model-ready spatial-spectral patches **without ever loading a full cube into memory**, while preserving geospatial metadata end to end.

## 2. Data Sources

| Source | Use | Notes |
|---|---|---|
| **Synthetic generator** (primary) | Training, review-gate demos, 3-week-ahead ground truth | You control onset date, stress patterns, noise |
| Indian Pines / Salinas / Pavia (public) | Sanity benchmark for the 3D-CNN/ViT | Land-cover labels, not disease; label results as a benchmark only |
| NASA Hyperion / EO-1, ESA Sentinel-2 (13 bands, multispectral) | Format and CRS realism, optional | Hyperion archive is historical; Sentinel-2 is not truly hyperspectral |
| PRISMA / EnMAP (real hyperspectral) | Stretch, if access is granted | Requires registration |

Be explicit in every report which data a number came from.

## 3. Synthetic Cube Generator (`ml/data/synth.py`)

### 3.1 Cube definition
- Shape `(T, H, W, B)`: `T` acquisition dates (e.g., 8, five days apart or weekly), `B = 224` bands over roughly 400–2500 nm.
- Scene covers a notional 1,000 acres (about 4.05 km²; at 10 m pixels roughly 200 × 200 px, at 3 m larger). Make resolution configurable.
- Georeference: a fixed UTM zone transform near a real agricultural area (choose and document it), so the GIS validation uses real coordinates.

### 3.2 Spectral model
1. **Healthy vegetation signature:** low reflectance in blue/red (chlorophyll absorption), a sharp red-edge rise around 700–750 nm, a high NIR plateau, and SWIR water absorption dips near 1450 and 1950 nm.
2. **Soil / background signature:** smoother, lower NIR.
3. **Mixing:** per-pixel linear mixture of vegetation and soil with a canopy-cover fraction field.
4. **Stress signature:** early disease shifts the red edge slightly toward shorter wavelengths (a blue shift), lowers NIR plateau slightly, and raises SWIR reflectance. Magnitude grows with a stress level `s ∈ [0, 1]` over time.
5. **Visible symptoms:** only when `s` exceeds a visible threshold does visible-band reflectance change noticeably (yellowing). Early stress (`0 < s < threshold`) is mostly invisible in RGB but present in red-edge/SWIR. This is what makes "forecasting before visible symptoms" a meaningful test.
6. **Noise:** band-dependent Gaussian noise, illumination/BRDF scaling per scene, atmospheric water-vapour noise in absorption bands, optional striping.

> These are plausible physical trends, not a validated radiative-transfer model. State that in the report; optionally use PROSAIL for a more defensible simulation as a stretch.

### 3.3 Spatial model
- Disease patches seeded at random locations; spread with a Gaussian random field / diffusion so patches are spatially coherent.
- `stress[t, y, x]` increases over `t`; ground-truth labels:
  - `label_stressed_now[t]` = `s > s_detect` (chemically stressed)
  - `label_visible[t]` = `s > s_visible`
  - `days_to_visible[y, x]` for forecasting
- Save masks as separate rasters next to the cube.

### 3.4 Outputs on disk
```
data/raw/synth_v1/
├── scene_000/
│   ├── t00.tif ... t07.tif     # multi-band GeoTIFF, tiled + compressed
│   ├── stress_t00.tif ...      # float32 stress level
│   ├── labels_t00.tif ...      # uint8: 0 healthy, 1 stressed-invisible, 2 visible
│   └── meta.json               # dates, bands (nm), crs, seed, params
└── ...
```
Write GeoTIFFs **tiled** (`tiled=True`, `blockxsize=256`, `blockysize=256`, `compress="deflate"`, `interleave="band"` or `pixel`, document which) so windowed reads are fast.

## 4. Reading Data

### GeoTIFF (Rasterio)
```python
with rasterio.open(path) as src:
    window = Window(col_off, row_off, w, h)
    arr = src.read(window=window)   # (B, h, w)
```
### HDF5 (h5py)
- Datasets must be **chunked** (e.g., `(64, 64, B)`); read slices only.
- Store CRS and geotransform in attributes.
### Rules
- Windows only. No `src.read()` of the whole file.
- Validate `count`, `dtype`, `nodata`, `crs`, `transform` at registration and reject if missing.

## 5. Preprocessing Steps (in order)

1. **No-data mask:** replace nodata with NaN, build boolean mask, keep it with the tile.
2. **Bad bands removal:** drop bands in strong atmospheric water absorption (around 1350–1450 nm, 1800–1950 nm) and noisy edge bands. Keep a `band_index_map` to document which were removed.
3. **Scaling:** convert to reflectance in `[0, 1]` (divide by the sensor scale factor from metadata).
4. **Standardization:** per-band mean/std computed from a **training-only** random pixel sample; saved to `artifacts/norm.json`.
5. **PCA:** `IncrementalPCA(n_components=C)` with `C` chosen by explained variance (target ≥ 99%, typically 20–40). Fit on training pixels only. Save to `artifacts/pca.joblib`. Report the explained-variance curve.
6. **NaN handling:** fill masked pixels with zeros after standardization and carry the mask so loss ignores them.

## 6. Splits (avoid leakage)

- **Split by scene (and by spatial block), not by random pixel.** Adjacent pixels are near-identical; random pixel splits give inflated scores.
- Suggested: 70% scenes train, 15% val, 15% test; for a single large scene, use spatially disjoint blocks with a buffer gap of at least the patch size.
- Fit normalization and PCA on train only.

## 7. Patch / Tile Extraction

| Item | Training patches | Inference tiles |
|---|---|---|
| Size | `9×9` to `15×15` pixels (odd, center-pixel label), `C` PCA components | `256×256` core with 32 px overlap |
| Label | Center pixel | n/a |
| Sampling | Class-balanced (oversample stressed); hard-negative mining near stress borders | Dense, sliding |
| Augmentation | Flip, 90° rotations, small spectral jitter, band dropout, Gaussian noise; never geometric shear that breaks georeferencing | none |

For inference, run the model as a fully convolutional or patch-wise sliding window and **blend overlaps** with a Hann/linear window.

## 8. Dataset and DataLoader

```python
class HSIPatchDataset(Dataset):
    def __getitem__(self, i):
        # open handle lazily per worker; read one window; apply norm+PCA; return
        return x, y, meta   # x: (1, C, h, w) float32
```
- Open file handles **inside the worker** (lazy), never pickle open handles.
- `num_workers` 4–8, `pin_memory=True`, `persistent_workers=True`.
- Cache PCA-transformed chunks in Zarr to avoid recomputing PCA every epoch.

## 9. Memory Audit Checklist (Mid-Project evidence)

Record in `artifacts/reports/memory_audit.md`:
- Cube size on disk vs. peak RSS during preprocessing.
- Batch tensor shape and dtype, and per-batch memory (e.g., `B×1×C×h×w×4 bytes`).
- `torch.cuda.max_memory_allocated()` and peak system RAM per epoch.
- A run on a cube **larger than available RAM** (or an artificially capped RAM via `ulimit`/container limit) that still completes.
- Throughput: patches/second and tiles/second.

## 10. Data Validation Tests

- Geotransform preserved after tiling and stitching (round-trip test).
- Bad-band mask length matches band metadata.
- PCA transform dimension and variance sanity.
- Split disjointness test (no scene or block overlap).
- Generator determinism: same seed gives byte-identical output.
