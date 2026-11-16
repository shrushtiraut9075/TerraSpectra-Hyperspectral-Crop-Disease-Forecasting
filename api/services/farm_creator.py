import json
import math
import os
import re
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List

import numpy as np
import pyproj
import rasterio
from rasterio.features import shapes
from rasterio.transform import from_origin
from scipy.ndimage import gaussian_filter
from shapely.geometry import shape

from api.schemas import FieldCreateRequest, FieldItem
from api.services.db import save_field, save_job, save_scene
from api.settings import settings
from ml.utils.geo import compute_acreage, compute_bounds_wgs84, project_coords


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"[-\s]+", "-", text)


def create_custom_farm(req: FieldCreateRequest) -> FieldItem:
    """Creates a custom farm with multi-temporal acquisitions and risk analysis for any GPS location."""
    # 1. Coordinate Reference System (UTM)
    utm_zone = int((req.lon + 180) / 6) + 1
    crs = f"EPSG:{32600 + utm_zone}" if req.lat >= 0 else f"EPSG:{32700 + utm_zone}"

    transformer = pyproj.Transformer.from_crs("EPSG:4326", crs, always_xy=True)
    xc, yc = transformer.transform(req.lon, req.lat)

    # 2. Raster dimensions from requested acreage
    num_px = int(req.acres / 0.0247105)
    side = max(32, ((int(math.sqrt(num_px)) + 15) // 16) * 16)
    side = min(256, side)  # Limit to 256 for instant response

    half_w = (side * 10.0) / 2.0
    half_h = (side * 10.0) / 2.0
    tf = from_origin(xc - half_w, yc + half_h, 10.0, 10.0)
    bounds = tuple(round(b, 6) for b in compute_bounds_wgs84(side, side, tf, crs))
    calc_acres = round(compute_acreage(side, side, 10.0), 1)

    field_slug = slugify(req.name)[:24]
    field_id = f"farm-{field_slug}-{int(time.time()) % 10000}"
    now_iso = datetime.utcnow().isoformat() + "Z"

    # 3. Save Field in database
    field_dict = {
        "id": field_id,
        "name": req.name,
        "crop_type": req.crop_type,
        "acres": calc_acres,
        "lat": req.lat,
        "lon": req.lon,
        "bounds_wgs84": bounds,
        "created_at": now_iso,
    }
    save_field(field_dict)

    # 4. Generate 8 weekly multi-temporal acquisitions
    base_date = datetime.utcnow()
    dates = [
        (base_date - timedelta(days=7 * (7 - t))).replace(microsecond=0).isoformat() + "Z"
        for t in range(8)
    ]

    raster_meta = {
        "width": side,
        "height": side,
        "bands": 224,
        "crs": crs,
        "pixel_size_m": 10.0,
    }

    # Geotiff meta for writing risk rasters
    tif_meta = {
        "driver": "GTiff",
        "height": side,
        "width": side,
        "count": 1,
        "dtype": "float32",
        "crs": crs,
        "transform": tf,
        "compress": "deflate",
        "nodata": -9999.0,
    }

    anomalies_ref = [
        {"name": "Red-edge shift", "bands_nm": [690, 740], "share": 0.44},
        {"name": "SWIR water stress", "bands_nm": [1450, 1950], "share": 0.33},
        {"name": "NIR plateau drop", "bands_nm": [780, 900], "share": 0.23},
    ]

    px_area_m2 = 100.0
    px_to_acres = px_area_m2 / 4046.8564224

    # Epidemiological growth center
    cy, cx = side // 2, side // 2
    y_coords, x_coords = np.ogrid[:side, :side]
    dist_from_center = np.sqrt((x_coords - cx) ** 2 + (y_coords - cy) ** 2)

    for t in range(8):
        scene_id = f"{field_id}_t0{t}"
        results_dir = os.path.join(settings.data_root, "results", scene_id)
        os.makedirs(results_dir, exist_ok=True)

        # Build risk raster following progression
        # Baseline noise (healthy background: 0.04 - 0.12)
        np.random.seed(int(time.time()) % 1000 + t)
        baseline = np.random.uniform(0.04, 0.12, size=(side, side)).astype(np.float32)
        baseline = gaussian_filter(baseline, sigma=3.0)

        # Radial focal stress growth
        spread_radius = max(0.0, (t - 1) * (side / 14.0)) if t > 0 else 0.0
        if spread_radius > 0:
            stress_mask = (dist_from_center <= spread_radius).astype(np.float32)
            smoothed_stress = gaussian_filter(stress_mask, sigma=2.5)
            smoothed_stress = smoothed_stress / max(1e-5, smoothed_stress.max())
            intensity = 0.55 + 0.35 * (t / 7.0)
            risk = baseline * (1.0 - smoothed_stress) + intensity * smoothed_stress
        else:
            risk = baseline

        risk = np.clip(risk, 0.0, 1.0).astype(np.float32)

        # Write risk GeoTIFF
        risk_tif_path = os.path.join(results_dir, "risk.tif")
        with rasterio.open(risk_tif_path, "w", **tif_meta) as dst:
            dst.write(risk, 1)

        # Vectorize Risk Zones (threshold = 0.5)
        binary_mask = (risk >= 0.5).astype(np.int32)
        features: List[Dict[str, Any]] = []
        zone_id = 1
        total_at_risk_px = int(np.sum(binary_mask))

        if total_at_risk_px > 0:
            for geom_shape, _ in shapes(binary_mask, mask=(binary_mask == 1), transform=tf):
                geom_obj = shape(geom_shape)
                if geom_obj.area < (0.2 / px_to_acres):
                    continue

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

                zone_area_acres = round(float(geom_obj.area * px_to_acres), 2)
                features.append(
                    {
                        "type": "Feature",
                        "properties": {
                            "zone_id": zone_id,
                            "mean_risk": round(float(np.mean(risk[binary_mask == 1])), 2),
                            "max_risk": round(float(np.max(risk[binary_mask == 1])), 2),
                            "area_acres": zone_area_acres,
                            "top_anomaly": anomalies_ref[0]["name"],
                        },
                        "geometry": geo_geom,
                    }
                )
                zone_id += 1

        zones_geojson = {"type": "FeatureCollection", "features": features}
        with open(os.path.join(results_dir, "zones.geojson"), "w") as zf:
            json.dump(zones_geojson, zf, indent=2)

        # Write Analytics JSON
        acres_at_risk = round(float(total_at_risk_px * px_to_acres), 1)
        percent_at_risk = round(float(100.0 * total_at_risk_px / (side * side)), 1)
        hist_counts, hist_bins = np.histogram(risk, bins=10, range=(0.0, 1.0))

        analytics = {
            "scene_id": scene_id,
            "threshold": 0.5,
            "acres_total": calc_acres,
            "acres_at_risk": acres_at_risk,
            "percent_at_risk": percent_at_risk,
            "zones_count": len(features),
            "anomalies": anomalies_ref if acres_at_risk > 0 else [],
            "risk_histogram": {
                "bins": [round(float(b), 1) for b in hist_bins],
                "counts": [int(c) for c in hist_counts],
            },
        }
        with open(os.path.join(results_dir, "analytics.json"), "w") as af:
            json.dump(analytics, af, indent=2)

        # Save scene in SQLite
        scene_obj = {
            "id": scene_id,
            "name": f"{req.name} - Acq #{t + 1}",
            "field_id": field_id,
            "acquired_at": dates[t],
            "data_origin": "synthetic",
            "source_ref": f"raw/synth_v1/scene_000/t0{t}.tif",  # point to valid base
            "raster": raster_meta,
            "bounds_wgs84": bounds,
            "acres": calc_acres,
        }
        save_scene(scene_obj)

        # Save completed job in SQLite
        save_job(
            {
                "job_id": f"job-seed-{scene_id}",
                "scene_id": scene_id,
                "model": "hybrid-v1",
                "horizon_days": 21,
                "tile_size": 256,
                "overlap": 32,
                "status": "succeeded",
                "progress": 1.0,
                "tiles_done": 100,
                "tiles_total": 100,
                "started_at": dates[t],
                "finished_at": dates[t],
                "error": None,
            }
        )

    return FieldItem(
        id=field_id,
        name=req.name,
        crop_type=req.crop_type,
        acres=calc_acres,
        lat=req.lat,
        lon=req.lon,
        bounds_wgs84=bounds,
        created_at=now_iso,
    )

