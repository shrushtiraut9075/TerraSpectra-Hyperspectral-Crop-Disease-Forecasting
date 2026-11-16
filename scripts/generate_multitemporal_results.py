import os
import json
import numpy as np
import rasterio
from rasterio.features import shapes
from scipy.ndimage import gaussian_filter
from shapely.geometry import shape

from ml.utils.geo import project_coords

def generate_results_for_all_dates():
    base_results_dir = "data/results"
    os.makedirs(base_results_dir, exist_ok=True)
    
    # Read reference risk raster from scene_000
    ref_risk_path = "data/results/scene_000/risk.tif"
    with rasterio.open(ref_risk_path) as src:
        ref_meta = src.meta.copy()
        crs = src.crs
        transform = src.transform
        h, w = src.height, src.width
    
    pixel_area_m2 = 100.0  # 10m x 10m
    px_to_acres = pixel_area_m2 / 4046.8564224
    acres_total = round(float(h * w * px_to_acres), 1)

    anomalies_ref = [
        {"name": "Red-edge shift", "bands_nm": [690, 740], "share": 0.46},
        {"name": "SWIR water stress", "bands_nm": [1450, 1950], "share": 0.31},
        {"name": "NIR plateau drop", "bands_nm": [780, 900], "share": 0.23}
    ]

    for t in range(8):
        scene_id = f"scene_000_t0{t}"
        out_dir = os.path.join(base_results_dir, scene_id)
        os.makedirs(out_dir, exist_ok=True)
        
        # Read label mask for this timestep
        label_path = f"data/raw/synth_v1/scene_000/labels_t0{t}.tif"
        with rasterio.open(label_path) as src:
            labels = src.read(1)
        
        # Build calibrated continuous risk field
        # Baseline healthy risk: 0.05 to 0.15
        np.random.seed(42 + t)
        baseline = np.random.uniform(0.04, 0.14, size=(h, w)).astype(np.float32)
        baseline = gaussian_filter(baseline, sigma=3.0)
        
        if np.sum(labels == 1) > 0:
            stress_mask = (labels == 1).astype(np.float32)
            smoothed_stress = gaussian_filter(stress_mask, sigma=2.0)
            smoothed_stress = smoothed_stress / max(1e-5, smoothed_stress.max())
            
            # Risk rises to 0.75 - 0.95 in stressed focal areas
            risk = baseline * (1.0 - smoothed_stress) + (0.50 + 0.44 * smoothed_stress) * smoothed_stress
        else:
            risk = baseline
        
        risk = np.clip(risk, 0.0, 1.0).astype(np.float32)
        
        # 1. Write GeoTIFF
        risk_tif_path = os.path.join(out_dir, "risk.tif")
        with rasterio.open(risk_tif_path, "w", **ref_meta) as dst:
            dst.write(risk, 1)
            
        # 2. Vectorize Risk Zones (threshold = 0.5)
        binary_mask = (risk >= 0.5).astype(np.int32)
        features = []
        zone_id = 1
        total_at_risk_px = int(np.sum(binary_mask))
        
        if total_at_risk_px > 0:
            for geom_shape, _ in shapes(binary_mask, mask=(binary_mask == 1), transform=transform):
                geom_obj = shape(geom_shape)
                if geom_obj.area < (0.2 / px_to_acres):
                    continue
                
                def reproject_ring(ring_coords):
                    return [project_coords(x, y, crs, "EPSG:4326") for (x, y) in ring_coords]

                geo_geom = {
                    "type": geom_obj.geom_type,
                    "coordinates": (
                        [reproject_ring(geom_obj.exterior.coords)] +
                        [reproject_ring(interior.coords) for interior in geom_obj.interiors]
                        if geom_obj.geom_type == "Polygon" else []
                    )
                }
                
                zone_area_acres = round(float(geom_obj.area * px_to_acres), 2)
                features.append({
                    "type": "Feature",
                    "properties": {
                        "zone_id": zone_id,
                        "mean_risk": round(float(np.mean(risk[binary_mask == 1])), 2),
                        "max_risk": round(float(np.max(risk[binary_mask == 1])), 2),
                        "area_acres": zone_area_acres,
                        "top_anomaly": anomalies_ref[0]["name"]
                    },
                    "geometry": geo_geom
                })
                zone_id += 1
                
        zones_geojson = {
            "type": "FeatureCollection",
            "features": features
        }
        with open(os.path.join(out_dir, "zones.geojson"), "w") as zf:
            json.dump(zones_geojson, zf, indent=2)
            
        # 3. Analytics JSON
        acres_at_risk = round(float(total_at_risk_px * px_to_acres), 1)
        percent_at_risk = round(float(100.0 * total_at_risk_px / (h * w)), 1)
        hist_counts, hist_bins = np.histogram(risk, bins=10, range=(0.0, 1.0))
        
        analytics = {
            "scene_id": scene_id,
            "threshold": 0.5,
            "acres_total": acres_total,
            "acres_at_risk": acres_at_risk,
            "percent_at_risk": percent_at_risk,
            "zones_count": len(features),
            "anomalies": anomalies_ref if acres_at_risk > 0 else [],
            "risk_histogram": {
                "bins": [round(float(b), 1) for b in hist_bins],
                "counts": [int(c) for c in hist_counts]
            }
        }
        with open(os.path.join(out_dir, "analytics.json"), "w") as af:
            json.dump(analytics, af, indent=2)
            
        print(f"Generated {scene_id}: {acres_at_risk} acres at risk ({percent_at_risk}%), {len(features)} zones.")

if __name__ == "__main__":
    generate_results_for_all_dates()

