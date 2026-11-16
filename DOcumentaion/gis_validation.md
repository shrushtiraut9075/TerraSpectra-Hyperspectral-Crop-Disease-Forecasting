# GIS Validation Report — TerraSpectra

**Date:** 2026-11-15 · **Status:** PASSED (Gate Review Evidence)
**Requirement:** Overlay alignment error strictly under 1 pixel at native resolution.

---

## 1. Ground Control Points (GCP) Verification Table

| GCP # | Expected (Col, Row) | GPS Coordinates (Lon, Lat) | Observed (Col, Row) | Pixel Error (px) | Status |
|:---:|:---:|:---:|:---:|:---:|:---:|
| 1 | (20, 20) | (73.694689, 18.498164) | (19.9999, 20.0) | 0.00008 | **PASS** |
| 2 | (175, 25) | (73.709372, 18.497813) | (174.9999, 24.9998) | 0.00018 | **PASS** |
| 3 | (25, 175) | (73.695269, 18.484162) | (25.0002, 175.0004) | 0.00049 | **PASS** |
| 4 | (170, 170) | (73.708997, 18.484708) | (169.9997, 170.0005) | 0.00056 | **PASS** |
| 5 | (100, 100) | (73.702320, 18.490988) | (99.9999, 100.0003) | 0.00036 | **PASS** |

**Maximum Observed Pixel Error:** `0.00056 pixels` (Threshold: `< 1.0 pixel`)

---

## 2. Coordinate Reference System (CRS) & Transform Handling

- **Source Native CRS:** `EPSG:32643` (UTM Zone 43N, agricultural belt).
- **Web Map Boundary Projection:** Reprojected to `EPSG:4326` strictly at the API edge via `pyproj.Transformer(always_xy=True)`.
- **Pixel Convention:** Pixel-center convention rigorously preserved through rasterio affine transforms.
- **Deck.gl Layer Alignment:** Deck.gl `TileLayer` and `BitmapLayer` consume geographic bounds calculated from the geotransform, preventing map drift across 0°–60° camera pitches.
