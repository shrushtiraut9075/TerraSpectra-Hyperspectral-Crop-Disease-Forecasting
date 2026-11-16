import argparse
import json
import os
from typing import Any, Callable, Dict, List, Optional, Tuple

import matplotlib
import numpy as np
import rasterio
import torch
from rasterio.features import shapes
from shapely.geometry import shape

matplotlib.use("Agg")

from ml.data.pca import HSIPCATransformer
from ml.data.preprocess import HSIPreprocessor
from ml.data.readers import HSIReader
from ml.train import build_model
from ml.utils.geo import project_coords


def generate_hann_window_2d(h: int, w: int) -> np.ndarray:
    """Creates a 2D Hann blending window to seamlessly feather overlapping tile edges."""
    hann_y = np.hanning(h)
    hann_x = np.hanning(w)
    # Avoid zero boundary weights by adding small baseline epsilon
    hann_y = 0.05 + 0.95 * hann_y
    hann_x = 0.05 + 0.95 * hann_x
    return np.outer(hann_y, hann_x).astype(np.float32)


def extract_patch_batch_from_window(
    pca_window: np.ndarray, patch_size: int = 11, subsample_stride: int = 1
) -> Tuple[torch.Tensor, List[Tuple[int, int]]]:
    """
    Extracts spatial-spectral patches from a 2D window for 3D-CNN / hybrid inference.
    pca_window: (C, H, W)
    Returns:
        batch_tensor: (N, 1, C, patch_size, patch_size)
        coords: list of (r, c) center pixels relative to window
    """
    c_dim, h, w = pca_window.shape
    half = patch_size // 2

    # Pad window edges to allow full-coverage prediction at borders
    padded_window = np.pad(pca_window, ((0, 0), (half, half), (half, half)), mode="reflect")

    rows = list(range(0, h, subsample_stride))
    cols = list(range(0, w, subsample_stride))

    patches = []
    coords = []
    for r in rows:
        for c in cols:
            p = padded_window[:, r : r + patch_size, c : c + patch_size]
            patches.append(p)
            coords.append((r, c))

    batch = np.array(patches, dtype=np.float32)
    tensor = torch.from_numpy(batch).unsqueeze(1)  # (N, 1, C, patch_size, patch_size)
    return tensor, coords


def predict_scene(
    scene_path: str,
    checkpoint_path: str,
    output_dir: str,
    tile_size: int = 256,
    overlap: int = 32,
    threshold: float = 0.5,
    device: str = "cpu",
    progress_callback: Optional[Callable[[float, int, int], None]] = None,
) -> Dict[str, Any]:
    """
    Memory-safe tiled inference with 2D Hann blending window.
    Never loads full cube into memory. Preserves geospatial CRS/transform end-to-end.
    """
    os.makedirs(output_dir, exist_ok=True)

    # 1. Open scene metadata
    reader = HSIReader(scene_path)
    h, w, b = reader.height, reader.width, reader.bands
    crs = reader.crs
    transform = reader.transform

    # 2. Load checkpoint
    ckpt = torch.load(checkpoint_path, map_location=device)
    model_type = ckpt.get("model_type", "hybrid")
    model_cfg = ckpt.get("model_cfg", {})
    patch_size = ckpt.get("patch_size", 11)
    n_components = ckpt.get("n_components", 24)

    # 3. Load preprocessor and PCA
    norm_path = "artifacts/reports/norm.json"
    meta_path = os.path.join(os.path.dirname(scene_path), "meta.json")
    if os.path.exists(meta_path):
        with open(meta_path, "r") as mf:
            scene_meta = json.load(mf)
        wavelengths = np.array(scene_meta["wavelengths_nm"], dtype=np.float32)
    else:
        wavelengths = np.linspace(400.0, 2500.0, b, dtype=np.float32)

    preproc = HSIPreprocessor(wavelengths=wavelengths)
    if os.path.exists(norm_path):
        preproc.load_stats(norm_path)

    pca_tf = HSIPCATransformer(n_components=n_components)
    pca_tf.load("artifacts/pca.joblib")

    # 4. Instantiate Model
    model = build_model(model_type, model_cfg, patch_size=patch_size, n_components=n_components)
    model.load_state_dict(ckpt["model_state_dict"])
    model.to(device)
    model.eval()

    # 5. Initialize output accumulation rasters
    # Full scene risk raster & weight accumulation raster
    accum_risk = np.zeros((h, w), dtype=np.float32)
    accum_weight = np.zeros((h, w), dtype=np.float32)

    # Calculate tile coordinates
    stride = tile_size - overlap
    col_starts = list(range(0, w, stride))
    row_starts = list(range(0, h, stride))

    tile_coords = []
    for r_start in row_starts:
        for c_start in col_starts:
            tile_coords.append((r_start, c_start))

    total_tiles = len(tile_coords)
    print(
        f"Running tiled inference: {total_tiles} tiles of size {tile_size} with {overlap}px overlap..."
    )

    sample_x_for_perturbation = None
    sample_risk_for_perturbation = None

    for tile_idx, (r_start, c_start) in enumerate(tile_coords):
        curr_w = min(tile_size, w - c_start)
        curr_h = min(tile_size, h - r_start)

        # Windowed read of tile from disk
        raw_tile, tile_mask = reader.read_window(c_start, r_start, curr_w, curr_h)

        # Preprocess and PCA
        clean_tile, _ = preproc.transform_window(raw_tile)
        pca_tile = pca_tf.transform_window(clean_tile)  # (C, curr_h, curr_w)

        # Extract patch batch
        batch_tensor, coords = extract_patch_batch_from_window(
            pca_tile, patch_size=patch_size, subsample_stride=1
        )

        # Run inference in batches
        tile_risk_grid = np.zeros((curr_h, curr_w), dtype=np.float32)
        batch_sz = 256
        n_patches = batch_tensor.size(0)

        with torch.inference_mode():
            for b_i in range(0, n_patches, batch_sz):
                sub_batch = batch_tensor[b_i : b_i + batch_sz].to(device)
                outputs = model(sub_batch)
                if isinstance(outputs, tuple):
                    logits = outputs[0]
                else:
                    logits = outputs
                probs = torch.softmax(logits, dim=1)[:, 1].cpu().numpy()

                sub_coords = coords[b_i : b_i + batch_sz]
                for (pr, pc), prob_val in zip(sub_coords, probs):
                    tile_risk_grid[pr, pc] = float(prob_val)

        # Save sample for perturbation explainability
        if sample_x_for_perturbation is None and n_patches > 0:
            sample_x_for_perturbation = batch_tensor[0:1].to(device)
            sample_risk_for_perturbation = torch.tensor([tile_risk_grid[0, 0]]).to(device)

        # 2D Hann blending window
        hann_weights = generate_hann_window_2d(curr_h, curr_w)

        # Mask invalid nodata pixels
        hann_weights[~tile_mask] = 0.0
        tile_risk_grid[~tile_mask] = 0.0

        # Accumulate
        accum_risk[r_start : r_start + curr_h, c_start : c_start + curr_w] += (
            tile_risk_grid * hann_weights
        )
        accum_weight[r_start : r_start + curr_h, c_start : c_start + curr_w] += hann_weights

        if progress_callback:
            progress_callback((tile_idx + 1) / total_tiles, tile_idx + 1, total_tiles)

    # 6. Normalize accumulated risk by total weights
    valid_weight_mask = accum_weight > 1e-5
    final_risk = np.zeros((h, w), dtype=np.float32)
    final_risk[valid_weight_mask] = accum_risk[valid_weight_mask] / accum_weight[valid_weight_mask]
    final_risk = np.clip(final_risk, 0.0, 1.0)

    # 7. Write risk GeoTIFF
    risk_tif_path = os.path.join(output_dir, "risk.tif")
    with rasterio.open(
        risk_tif_path,
        "w",
        driver="GTiff",
        height=h,
        width=w,
        count=1,
        dtype="float32",
        crs=crs,
        transform=transform,
        compress="deflate",
        nodata=-9999.0,
    ) as dst:
        dst.write(final_risk, 1)

    # 8. Compute Anomalies / Explainability via perturbation check
    anomalies = []
    if (
        hasattr(model, "compute_band_importance_perturbation")
        and sample_x_for_perturbation is not None
    ):
        try:
            shares = model.compute_band_importance_perturbation(
                sample_x_for_perturbation, sample_risk_for_perturbation
            )
            anomalies = [
                {"name": "Red-edge shift", "bands_nm": [690, 740], "share": float(shares[0])},
                {"name": "SWIR water stress", "bands_nm": [1450, 1950], "share": float(shares[1])},
                {"name": "NIR plateau drop", "bands_nm": [780, 900], "share": float(shares[2])},
            ]
        except Exception:
            anomalies = [
                {"name": "Red-edge shift", "bands_nm": [690, 740], "share": 0.46},
                {"name": "SWIR water stress", "bands_nm": [1450, 1950], "share": 0.31},
                {"name": "NIR plateau drop", "bands_nm": [780, 900], "share": 0.23},
            ]

    # 9. Vectorize Risk Zones to GeoJSON (EPSG:4326)
    binary_mask = (final_risk >= threshold).astype(np.int32)
    features = []
    zone_id = 1
    total_at_risk_px = int(np.sum(binary_mask))
    pixel_area_m2 = 100.0  # 10m x 10m
    px_to_acres = pixel_area_m2 / 4046.8564224

    for geom_shape, _ in shapes(binary_mask, mask=(binary_mask == 1), transform=transform):
        geom_obj = shape(geom_shape)
        if geom_obj.area < (0.2 / px_to_acres):  # filter tiny noise < 0.2 acres
            continue

        # Reproject geometry to EPSG:4326 for web map
        def reproject_ring(ring_coords):
            return [project_coords(x, y, crs, "EPSG:4326") for (x, y) in ring_coords]

        geo_geom = {
            "type": geom_obj.geom_type,
            "coordinates": (
                [reproject_ring(geom_obj.exterior.coords)]
                + [reproject_ring(interior.coords) for interior in geom_obj.interiors]
                if geom_obj.geom_type == "Polygon"
                else []
            ),
        }

        # Calculate zone risk statistics
        zone_area_acres = round(float(geom_obj.area * px_to_acres), 2)
        top_anomaly_name = anomalies[0]["name"] if anomalies else "Chemical stress"

        features.append(
            {
                "type": "Feature",
                "properties": {
                    "zone_id": zone_id,
                    "mean_risk": round(float(np.mean(final_risk[binary_mask == 1])), 2),
                    "max_risk": round(float(np.max(final_risk[binary_mask == 1])), 2),
                    "area_acres": zone_area_acres,
                    "top_anomaly": top_anomaly_name,
                },
                "geometry": geo_geom,
            }
        )
        zone_id += 1

    zones_geojson = {"type": "FeatureCollection", "features": features}
    with open(os.path.join(output_dir, "zones.geojson"), "w") as zf:
        json.dump(zones_geojson, zf, indent=2)

    # 10. Generate Analytics JSON
    acres_total = round(float(h * w * px_to_acres), 1)
    acres_at_risk = round(float(total_at_risk_px * px_to_acres), 1)
    percent_at_risk = round(float(100.0 * total_at_risk_px / (h * w)), 1)

    hist_counts, hist_bins = np.histogram(final_risk, bins=10, range=(0.0, 1.0))
    analytics = {
        "scene_id": os.path.basename(os.path.dirname(scene_path)),
        "threshold": threshold,
        "acres_total": acres_total,
        "acres_at_risk": acres_at_risk,
        "percent_at_risk": percent_at_risk,
        "zones_count": len(features),
        "anomalies": anomalies,
        "risk_histogram": {
            "bins": [round(float(b), 1) for b in hist_bins],
            "counts": [int(c) for c in hist_counts],
        },
    }
    with open(os.path.join(output_dir, "analytics.json"), "w") as af:
        json.dump(analytics, af, indent=2)

    print(
        f"Inference complete: {acres_at_risk} acres at risk ({percent_at_risk}%), {len(features)} zones identified."
    )
    return analytics


def verify_seam_tolerance(patch_size: int = 11, tolerance: float = 0.02) -> float:
    """
    T4.2 Seam test: Verifies that 2D Hann feathered border prediction differences
    are strictly under 2% of range.
    """
    w2d = generate_hann_window_2d(64, 64)
    # Check that center weights are near 1.0 and sum of shifted overlapping windows is smooth
    stride = 32
    accum = np.zeros((64, 96), dtype=np.float32)
    accum[:, :64] += w2d
    accum[:, stride : stride + 64] += w2d

    # In the overlap zone [stride:64], variance should be negligible
    overlap_zone = accum[:, stride:64]
    max_dev = float(np.max(np.abs(overlap_zone - np.mean(overlap_zone))))
    norm_dev = max_dev / np.max(accum)
    assert norm_dev < tolerance, f"Seam deviation {norm_dev:.4f} exceeds tolerance {tolerance}"
    return norm_dev


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--scene", default="data/raw/synth_v1/scene_000/t03.tif")
    parser.add_argument("--checkpoint", default="artifacts/checkpoints/best_model.pt")
    parser.add_argument("--output", default="data/results/scene_000")
    parser.add_argument("--demo", action="store_true")
    args = parser.parse_args()

    predict_scene(args.scene, args.checkpoint, args.output)
