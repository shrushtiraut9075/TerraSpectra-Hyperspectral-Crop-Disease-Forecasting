import os
import json
import math
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any, Optional

import numpy as np
import rasterio
from rasterio.transform import from_origin
import h5py
from scipy.ndimage import gaussian_filter

from ml.utils.seed import set_seed
from ml.utils.geo import compute_bounds_wgs84, pixel_to_geo, compute_acreage

def generate_wavelengths(bands: int = 224, min_nm: float = 400.0, max_nm: float = 2500.0) -> np.ndarray:
    """Generate center wavelengths for hyperspectral sensor in nanometers."""
    return np.linspace(min_nm, max_nm, bands, dtype=np.float32)

def generate_healthy_spectrum(wavelengths: np.ndarray) -> np.ndarray:
    """
    Physical-approximation spectral reflectance curve for healthy green canopy.
    Features: Chlorophyll absorption (blue 450nm, red 670nm), green peak (550nm),
    steep red edge (700-750nm), high NIR plateau (750-1300nm), SWIR water dips (1450, 1950nm).
    """
    refl = np.zeros_like(wavelengths, dtype=np.float32)
    for i, wl in enumerate(wavelengths):
        if wl < 500: # Blue: strong chlorophyll absorption
            r = 0.04 + 0.03 * ((wl - 400) / 100.0) ** 2
        elif wl < 600: # Green peak
            r = 0.07 + 0.06 * np.exp(-((wl - 550) ** 2) / (2 * 25 ** 2))
        elif wl < 700: # Red absorption
            r = 0.04 + 0.02 * np.exp(-((wl - 670) ** 2) / (2 * 20 ** 2))
        elif wl < 760: # Red edge steep transition
            t = (wl - 700) / 60.0
            r = 0.05 + 0.45 / (1.0 + np.exp(-10 * (t - 0.5)))
        elif wl < 1350: # NIR plateau
            r = 0.50 - 0.06 * ((wl - 760) / 600.0)
        elif wl < 1550: # 1450 nm water absorption band
            water_dip = 0.25 * np.exp(-((wl - 1450) ** 2) / (2 * 45 ** 2))
            r = 0.38 - water_dip
        elif wl < 1850: # Secondary NIR/SWIR plateau
            r = 0.34 - 0.05 * ((wl - 1550) / 300.0)
        elif wl < 2100: # 1950 nm deep water absorption band
            water_dip = 0.22 * np.exp(-((wl - 1950) ** 2) / (2 * 50 ** 2))
            r = 0.24 - water_dip
        else: # Far SWIR
            r = 0.16 - 0.08 * ((wl - 2100) / 400.0)
        refl[i] = np.clip(r, 0.01, 0.85)
    return refl

def generate_soil_spectrum(wavelengths: np.ndarray) -> np.ndarray:
    """Smooth, monotonically rising reflectance characteristic of agricultural soil."""
    # Gradual rise from ~0.10 at 400nm to ~0.35 at 2500nm with mild iron oxide/clay features
    base = 0.10 + 0.25 * ((wavelengths - 400.0) / 2100.0) ** 0.8
    # Mild clay absorption at 2200nm
    clay = 0.03 * np.exp(-((wavelengths - 2200.0) ** 2) / (2 * 40 ** 2))
    return np.clip(base - clay, 0.05, 0.60).astype(np.float32)

def apply_stress_to_spectrum(
    healthy_refl: np.ndarray,
    wavelengths: np.ndarray,
    stress_level: float
) -> np.ndarray:
    """
    Simulates physiological and biochemical stress response:
    - Red edge shifts to shorter wavelengths (blue-shift: chlorophyll reduction).
    - NIR plateau drops (mesophyll cell structure collapse).
    - SWIR reflectance rises (leaf water loss reduces water absorption).
    - Only at high stress (visible yellowing) does visible reflectance rise noticeably.
    """
    if stress_level <= 0.0:
        return healthy_refl.copy()

    s = np.clip(stress_level, 0.0, 1.0)
    stressed = healthy_refl.copy()

    for i, wl in enumerate(wavelengths):
        # 1. Early chemical stress: Red-edge blue shift (690-750 nm)
        if 680 <= wl <= 750:
            red_edge_shift = 0.14 * s * np.exp(-((wl - 715) ** 2) / (2 * 20 ** 2))
            stressed[i] = max(0.01, stressed[i] - red_edge_shift)

        # 2. Early NIR plateau drop (760-1200 nm)
        if 760 <= wl <= 1300:
            nir_drop = 0.18 * (s ** 1.1) * (1.0 - 0.2 * ((wl - 760) / 540.0))
            stressed[i] = max(0.05, stressed[i] - nir_drop)

        # 3. Early SWIR water stress: increased reflectance due to moisture loss
        if (1350 <= wl <= 1650) or (1850 <= wl <= 2150):
            swir_increase = 0.15 * s
            stressed[i] = min(0.70, stressed[i] + swir_increase)

        # 4. Late visible symptom: yellowing/chlorosis only when s > 0.65
        if s > 0.65 and (500 <= wl <= 680):
            visible_excess = (s - 0.65) / 0.35
            chlorosis = 0.12 * visible_excess * np.exp(-((wl - 620) ** 2) / (2 * 35 ** 2))
            stressed[i] = min(0.60, stressed[i] + chlorosis)

    return stressed

def generate_spatial_stress_field(
    height: int,
    width: int,
    time_steps: int,
    num_foci: int = 4,
    random_state: Optional[np.random.RandomState] = None
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Simulates disease foci initiation and outward diffusion over time.
    Returns:
      stress_field: (T, H, W) float in [0, 1]
      onset_step: (H, W) step index when stress became visible (or 999 if never)
    """
    if random_state is None:
        random_state = np.random.RandomState(42)

    stress_field = np.zeros((time_steps, height, width), dtype=np.float32)

    # Pick infection foci points
    foci = []
    for _ in range(num_foci):
        fy = random_state.randint(int(height * 0.15), int(height * 0.85))
        fx = random_state.randint(int(width * 0.15), int(width * 0.85))
        start_t = random_state.randint(0, max(1, time_steps // 2))
        max_rate = random_state.uniform(0.12, 0.22)
        radius = random_state.uniform(6.0, 14.0)
        foci.append((fy, fx, start_t, max_rate, radius))

    # Base background variations
    bg_noise = gaussian_filter(random_state.randn(height, width).astype(np.float32), sigma=12.0)
    bg_noise = (bg_noise - bg_noise.min()) / (bg_noise.max() - bg_noise.min() + 1e-6)

    for t in range(time_steps):
        t_field = np.zeros((height, width), dtype=np.float32)
        for (fy, fx, start_t, max_rate, radius) in foci:
            if t >= start_t:
                steps_active = t - start_t + 1
                curr_radius = radius + steps_active * 2.5
                intensity = min(1.0, steps_active * max_rate)

                # Distance grid
                y_idx, x_idx = np.ogrid[:height, :width]
                dist = np.sqrt((y_idx - fy) ** 2 + (x_idx - fx) ** 2)
                gaussian_patch = intensity * np.exp(-(dist ** 2) / (2 * curr_radius ** 2))
                t_field = np.maximum(t_field, gaussian_patch)

        # Modulate by soil/crop density background to create realistic ragged patch edges
        t_field = t_field * (0.8 + 0.4 * bg_noise)
        stress_field[t] = np.clip(t_field, 0.0, 1.0)

    # Compute onset step where s >= 0.65 (visible disease)
    visible_threshold = 0.65
    onset_step = np.full((height, width), 999, dtype=np.int32)
    for t in range(time_steps):
        mask = (stress_field[t] >= visible_threshold) & (onset_step == 999)
        onset_step[mask] = t

    return stress_field, onset_step

def generate_synthetic_scene(
    scene_id: str,
    output_dir: str,
    height: int = 200,
    width: int = 200,
    bands: int = 224,
    time_steps: int = 8,
    pixel_size_m: float = 10.0,
    utm_crs: str = "EPSG:32643",
    origin_x: float = 362000.0,
    origin_y: float = 2046000.0,
    start_date: str = "2026-05-01",
    days_between_dates: int = 7,
    horizon_days: int = 21,
    stress_detect_thresh: float = 0.18,
    stress_visible_thresh: float = 0.65,
    seed: int = 42,
    write_hdf5: bool = False
) -> Dict[str, Any]:
    """
    Generates a full synthetic multi-temporal hyperspectral scene.
    Writes tiled GeoTIFFs, ground-truth masks, and metadata JSON.
    """
    set_seed(seed)
    rng = np.random.RandomState(seed)

    os.makedirs(output_dir, exist_ok=True)

    wavelengths = generate_wavelengths(bands)
    healthy_spectrum = generate_healthy_spectrum(wavelengths)
    soil_spectrum = generate_soil_spectrum(wavelengths)

    # Affine transform for rasterio: top-left origin, pixel_size_m, -pixel_size_m
    transform = from_origin(origin_x, origin_y, pixel_size_m, pixel_size_m)

    # Spatial stress progression
    num_foci = rng.randint(3, 6)
    stress_field, onset_step = generate_spatial_stress_field(
        height, width, time_steps, num_foci=num_foci, random_state=rng
    )

    # Canopy cover fraction field fc in [0.65, 0.95]
    fc_field = 0.65 + 0.30 * gaussian_filter(rng.rand(height, width).astype(np.float32), sigma=8.0)
    fc_field = np.clip(fc_field, 0.50, 0.98)

    base_date = datetime.fromisoformat(start_date)
    acquisition_dates = [
        (base_date + timedelta(days=t * days_between_dates)).isoformat() + "Z"
        for t in range(time_steps)
    ]

    # Pre-select Ground Control Points (GCPs)
    gcp_pixels = [
        (20, 20),
        (width - 25, 25),
        (25, height - 25),
        (width - 30, height - 30),
        (width // 2, height // 2)
    ]
    gcps = []
    for col, row in gcp_pixels:
        lon, lat = pixel_to_geo(float(col), float(row), transform, utm_crs)
        gcps.append({
            "col": int(col),
            "row": int(row),
            "lon": round(lon, 7),
            "lat": round(lat, 7)
        })

    bounds_wgs84 = compute_bounds_wgs84(width, height, transform, utm_crs)
    acres = compute_acreage(width, height, pixel_size_m)

    # Generate each time-step
    tiff_paths = []
    for t in range(time_steps):
        cube_t = np.zeros((bands, height, width), dtype=np.float32)
        s_t = stress_field[t]

        # Sample pixel-wise spectra with linear spectral mixture + stress
        # For efficiency, discretize stress levels into bins
        unique_s_bins = np.linspace(0.0, 1.0, 50)
        s_bin_indices = np.digitize(s_t, unique_s_bins) - 1
        s_bin_indices = np.clip(s_bin_indices, 0, len(unique_s_bins) - 1)

        cached_stressed_veg = np.zeros((len(unique_s_bins), bands), dtype=np.float32)
        for idx, sv in enumerate(unique_s_bins):
            cached_stressed_veg[idx] = apply_stress_to_spectrum(healthy_spectrum, wavelengths, sv)

        # Assemble cube: canopy_cover * veg + (1 - canopy_cover) * soil
        for b in range(bands):
            veg_band = cached_stressed_veg[s_bin_indices, b]
            soil_val = soil_spectrum[b]
            band_refl = fc_field * veg_band + (1.0 - fc_field) * soil_val

            # Band noise + slight illumination modulation
            noise_std = 0.005 + 0.008 * (wavelengths[b] > 1800)
            noise = rng.normal(0.0, noise_std, (height, width)).astype(np.float32)
            cube_t[b] = np.clip(band_refl + noise, 0.005, 0.95)

        # Write Tiled GeoTIFF: shape (bands, height, width)
        tif_filename = f"t{t:02d}.tif"
        tif_path = os.path.join(output_dir, tif_filename)
        with rasterio.open(
            tif_path,
            "w",
            driver="GTiff",
            height=height,
            width=width,
            count=bands,
            dtype="float32",
            crs=utm_crs,
            transform=transform,
            tiled=True,
            blockxsize=128 if width >= 128 else max(16, (width // 16) * 16),
            blockysize=128 if height >= 128 else max(16, (height // 16) * 16),
            compress="deflate",
            nodata=-9999.0
        ) as dst:
            dst.write(cube_t)
        tiff_paths.append(tif_filename)

        # Ground truth labels:
        # 0: Healthy
        # 1: Stressed Invisible (s_detect <= s < s_visible)
        # 2: Visible Disease (s >= s_visible)
        labels_t = np.zeros((height, width), dtype=np.uint8)
        labels_t[s_t >= stress_detect_thresh] = 1
        labels_t[s_t >= stress_visible_thresh] = 2

        # Days to visible:
        days_to_vis = np.full((height, width), -1.0, dtype=np.float32)
        for r_i in range(height):
            for c_i in range(width):
                vis_step = onset_step[r_i, c_i]
                if vis_step < 999:
                    delta_steps = vis_step - t
                    days_to_vis[r_i, c_i] = max(0.0, delta_steps * days_between_dates)

        # Write stress mask
        stress_tif = os.path.join(output_dir, f"stress_t{t:02d}.tif")
        with rasterio.open(
            stress_tif,
            "w",
            driver="GTiff",
            height=height,
            width=width,
            count=1,
            dtype="float32",
            crs=utm_crs,
            transform=transform,
            compress="deflate",
            nodata=-9999.0
        ) as dst:
            dst.write(s_t, 1)

        # Write labels mask
        labels_tif = os.path.join(output_dir, f"labels_t{t:02d}.tif")
        with rasterio.open(
            labels_tif,
            "w",
            driver="GTiff",
            height=height,
            width=width,
            count=1,
            dtype="uint8",
            crs=utm_crs,
            transform=transform,
            compress="deflate",
            nodata=255
        ) as dst:
            dst.write(labels_t, 1)

        # Write days-to-visible
        days_tif = os.path.join(output_dir, f"days_t{t:02d}.tif")
        with rasterio.open(
            days_tif,
            "w",
            driver="GTiff",
            height=height,
            width=width,
            count=1,
            dtype="float32",
            crs=utm_crs,
            transform=transform,
            compress="deflate",
            nodata=-1.0
        ) as dst:
            dst.write(days_to_vis, 1)

    # Optional HDF5 variant for t00 to prove HDF5 windowed reader
    if write_hdf5:
        h5_path = os.path.join(output_dir, "t00.h5")
        with rasterio.open(os.path.join(output_dir, "t00.tif")) as src:
            first_cube = src.read() # (B, H, W)
            # transpose to (H, W, B) for standard spatial HDF5 chunking
            first_cube_hwc = np.transpose(first_cube, (1, 2, 0))

        with h5py.File(h5_path, "w") as hf:
            dset = hf.create_dataset(
                "cube",
                data=first_cube_hwc,
                chunks=(min(64, height), min(64, width), bands),
                compression="gzip"
            )
            hf.attrs["crs"] = utm_crs
            hf.attrs["transform"] = list(transform)
            hf.attrs["wavelengths"] = wavelengths
            hf.attrs["layout"] = "HWB"

    # Save meta.json
    metadata = {
        "scene_id": scene_id,
        "data_origin": "synthetic",
        "created_at": datetime.utcnow().isoformat() + "Z",
        "dimensions": {
            "height": height,
            "width": width,
            "bands": bands,
            "time_steps": time_steps,
            "pixel_size_m": pixel_size_m,
            "acres": round(acres, 2)
        },
        "crs": utm_crs,
        "transform": [transform.a, transform.b, transform.c, transform.d, transform.e, transform.f],
        "bounds_wgs84": [round(b, 6) for b in bounds_wgs84],
        "wavelengths_nm": [round(float(w), 2) for w in wavelengths],
        "acquisition_dates": acquisition_dates,
        "ground_control_points": gcps,
        "seed": seed,
        "params": {
            "stress_detection_threshold": stress_detect_thresh,
            "stress_visible_threshold": stress_visible_thresh,
            "horizon_days": horizon_days,
            "days_between_dates": days_between_dates
        }
    }

    with open(os.path.join(output_dir, "meta.json"), "w") as mf:
        json.dump(metadata, mf, indent=2)

    return metadata

if __name__ == "__main__":
    import yaml
    import argparse

    parser = argparse.ArgumentParser(description="Generate synthetic hyperspectral cubes.")
    parser.add_argument("--config", default="configs/data.yaml", help="Path to data config YAML")
    parser.add_argument("--demo", action="store_true", help="Generate single scene for demo")
    args = parser.parse_args()

    cfg_path = args.config if os.path.exists(args.config) else "configs/data.yaml"
    with open(cfg_path, "r") as f:
        cfg = yaml.safe_load(f)

    scene_cfg = cfg["scene"]
    base_raw_dir = "data/raw/synth_v1"
    os.makedirs(base_raw_dir, exist_ok=True)

    num_scenes = 1 if args.demo else scene_cfg.get("num_scenes", 4)
    for s_idx in range(num_scenes):
        s_id = f"scene_{s_idx:03d}"
        s_dir = os.path.join(base_raw_dir, s_id)
        print(f"Generating synthetic scene {s_id} in {s_dir}...")
        meta = generate_synthetic_scene(
            scene_id=s_id,
            output_dir=s_dir,
            height=scene_cfg["height"],
            width=scene_cfg["width"],
            bands=scene_cfg["bands"],
            time_steps=scene_cfg["time_steps"],
            pixel_size_m=scene_cfg["pixel_size_m"],
            utm_crs=scene_cfg["utm_crs"],
            origin_x=scene_cfg["origin_x"] + s_idx * 2500.0,
            origin_y=scene_cfg["origin_y"],
            days_between_dates=scene_cfg["days_between_dates"],
            horizon_days=scene_cfg["horizon_days"],
            stress_detect_thresh=scene_cfg["stress_detection_threshold"],
            stress_visible_thresh=scene_cfg["stress_visible_threshold"],
            seed=scene_cfg["random_seed"] + s_idx,
            write_hdf5=(s_idx == 0) # write HDF5 for scene_000
        )
        print(f"Done scene {s_id}: bounds={meta['bounds_wgs84']}, acres={meta['dimensions']['acres']}")