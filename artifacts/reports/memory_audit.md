# Memory Extraction Audit — TerraSpectra

**Date:** 2026-11-15 · **Status:** PASSED (Gate Review Evidence)
**Requirement:** Windowed reads only. Never load full cube into RAM. Training completes under enforced memory envelope.

---

## 1. Memory Profile Summary

| Metric | Measurement | Target / Constraint | Status |
|---|---|---|---|
| **Single Date Cube on Disk** | `29.84 MB` | — | Documented |
| **Full 8-Date Scene on Disk** | `238.75 MB` | — | Documented |
| **Peak Ingestion System RAM (RSS)** | `293.0 MB` | `< 4,000 MB` | **PASS** |
| **Batch Tensor Shape** | `(128, 1, 24, 11, 11)` | Float32 | **PASS** |
| **Batch Memory Size** | `1.48 MB` | Compact 3D tensor | **PASS** |
| **Windowed Ingestion Throughput** | `> 450 patches/sec` | `> 100 patches/sec` | **PASS** |

---

## 2. Windowed Read Latency by Block Size

| Window Size (px) | Total Windows | Total Read Time (s) | Throughput |
|---|---|---|---|
| 32 × 32 | 16 | 1.7027s | Fast streaming |
| 64 × 64 | 4 | 0.5326s | Fast streaming |
| 128 × 128 | 1 | 0.1152s | Fast streaming |

---

## 3. Memory Optimization Knobs Applied

1. **Windowed GeoTIFF & HDF5 Readers:** Reads spatial subsets with `rasterio.windows.Window` and chunked h5py slices; full-cube `src.read()` is strictly prohibited.
2. **Incremental PCA:** Dimensions reduced from 224 raw bands to 24 principal components using `IncrementalPCA` chunk by chunk.
3. **Pre-allocated Tiled Blend Raster:** Stitched risk rasters are accumulated in-place with a float32 2D Hann window, preventing array duplication.
4. **Lazy Worker Dataset:** `HSIPatchDataset` opens file handles inside workers without pickling open raster descriptors.
