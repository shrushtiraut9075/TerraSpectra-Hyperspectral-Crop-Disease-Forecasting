import asyncio
import io
import math
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Tuple

import matplotlib
import numpy as np
import pyproj
import rasterio
from PIL import Image
from rasterio.windows import from_bounds

from api.services.db import get_scene, update_job_progress
from api.settings import settings
from ml.infer import predict_scene

thread_pool = ThreadPoolExecutor(max_workers=2)
inference_semaphore = asyncio.Semaphore(1)


def tile_to_bounds_wgs84(z: int, x: int, y: int) -> Tuple[float, float, float, float]:
    """Convert XYZ web mercator tile indices to EPSG:4326 bbox [min_lon, min_lat, max_lon, max_lat]."""
    n = 2.0**z
    lon_min = x / n * 360.0 - 180.0
    lon_max = (x + 1) / n * 360.0 - 180.0
    lat_min_rad = math.atan(math.sinh(math.pi * (1.0 - 2.0 * (y + 1) / n)))
    lat_max_rad = math.atan(math.sinh(math.pi * (1.0 - 2.0 * y / n)))
    lat_min = math.degrees(lat_min_rad)
    lat_max = math.degrees(lat_max_rad)
    return (lon_min, lat_min, lon_max, lat_max)


def get_color_ramp_rgba(
    risk_arr: np.ndarray, threshold: float = 0.5, cmap_name: str = "risk"
) -> np.ndarray:
    """
    Renders risk array [0, 1] into RGBA image array.
    Perceptually ordered green -> yellow -> orange -> red.
    Transparent below threshold or nodata.
    """
    h, w = risk_arr.shape
    rgba = np.zeros((h, w, 4), dtype=np.uint8)

    # Valid mask
    valid = (~np.isnan(risk_arr)) & (risk_arr >= threshold) & (risk_arr <= 1.0)
    if not np.any(valid):
        return rgba

    # Normalize values above threshold to [0, 1] for colour ramp
    norm_vals = (risk_arr[valid] - threshold) / max(1e-4, 1.0 - threshold)
    norm_vals = np.clip(norm_vals, 0.0, 1.0)

    if cmap_name == "colorblind":
        # Viridis or cividis for colorblind safety
        colormap = matplotlib.colormaps["cividis"]
    else:
        # Standard risk: Turbo or RdYlGn_r (green to red)
        colormap = matplotlib.colormaps["RdYlGn_r"]

    colors = colormap(norm_vals)  # shape (N, 4) in [0, 1]
    rgba[valid, 0] = (colors[:, 0] * 255).astype(np.uint8)
    rgba[valid, 1] = (colors[:, 1] * 255).astype(np.uint8)
    rgba[valid, 2] = (colors[:, 2] * 255).astype(np.uint8)
    # Alpha proportional to risk level above threshold
    rgba[valid, 3] = np.clip(140 + colors[:, 3] * 115, 140, 255).astype(np.uint8)

    return rgba


def generate_tile_png(
    scene_id: str, z: int, x: int, y: int, threshold: float = 0.5, cmap: str = "risk"
) -> bytes:
    """Renders a 256x256 PNG tile for the given web tile coordinates."""
    risk_tif = os.path.join(settings.data_root, "results", scene_id, "risk.tif")
    if not os.path.exists(risk_tif):
        # Empty transparent 256x256 PNG
        img = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
        out = io.BytesIO()
        img.save(out, format="PNG")
        return out.getvalue()

    tile_min_lon, tile_min_lat, tile_max_lon, tile_max_lat = tile_to_bounds_wgs84(z, x, y)

    with rasterio.open(risk_tif) as src:
        # Reproject tile bounds to raster native CRS
        transformer = pyproj.Transformer.from_crs("EPSG:4326", src.crs, always_xy=True)
        native_min_x, native_min_y = transformer.transform(tile_min_lon, tile_min_lat)
        native_max_x, native_max_y = transformer.transform(tile_max_lon, tile_max_lat)

        try:
            window = from_bounds(
                min(native_min_x, native_max_x),
                min(native_min_y, native_max_y),
                max(native_min_x, native_max_x),
                max(native_min_y, native_max_y),
                src.transform,
            )
            # Read window and resample to 256x256
            tile_data = src.read(
                1,
                window=window,
                out_shape=(256, 256),
                resampling=rasterio.enums.Resampling.bilinear,
                boundless=True,
                fill_value=np.nan,
            )
        except Exception:
            tile_data = np.full((256, 256), fill_value=np.nan, dtype=np.float32)

    rgba = get_color_ramp_rgba(tile_data, threshold=threshold, cmap_name=cmap)
    img = Image.fromarray(rgba, "RGBA")
    out = io.BytesIO()
    img.save(out, format="PNG", optimize=True)
    return out.getvalue()


def execute_inference_worker(job_id: str, scene_id: str, tile_size: int, overlap: int):
    """Executes the heavy tiled inference pipeline synchronously in thread pool."""
    scene = get_scene(scene_id)
    if not scene:
        update_job_progress(job_id, "failed", 0.0, 0, 0, error="Scene not found")
        return

    source_path = os.path.join(settings.data_root, scene["source_ref"])
    if not os.path.exists(source_path):
        update_job_progress(job_id, "failed", 0.0, 0, 0, error=f"Source file {source_path} missing")
        return

    output_dir = os.path.join(settings.data_root, "results", scene_id)
    checkpoint_path = os.path.join(settings.artifacts_root, "checkpoints", "best_model.pt")
    if not os.path.exists(checkpoint_path):
        # Fallback to any pt file in checkpoints
        all_ckpts = [
            f
            for f in os.listdir(os.path.join(settings.artifacts_root, "checkpoints"))
            if f.endswith(".pt")
        ]
        if all_ckpts:
            checkpoint_path = os.path.join(settings.artifacts_root, "checkpoints", all_ckpts[0])

    def progress_callback(progress: float, done: int, total: int):
        update_job_progress(job_id, "running", progress, done, total)

    try:
        predict_scene(
            scene_path=source_path,
            checkpoint_path=checkpoint_path,
            output_dir=output_dir,
            tile_size=tile_size,
            overlap=overlap,
            progress_callback=progress_callback,
        )
        update_job_progress(job_id, "succeeded", 1.0, 100, 100)
    except Exception as e:
        update_job_progress(job_id, "failed", 0.0, 0, 0, error=str(e))
