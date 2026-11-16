import json
import os

import numpy as np
import rasterio
from fastapi import APIRouter, HTTPException, status

from api.schemas import AnalyticsResponse
from api.services.db import get_scene
from api.settings import settings

router = APIRouter(prefix="/scenes", tags=["analytics"])


@router.get("/{scene_id}/analytics", response_model=AnalyticsResponse)
def get_scene_analytics(scene_id: str, threshold: float = 0.5):
    scene = get_scene(scene_id)
    if not scene:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "SCENE_NOT_FOUND",
                "message": f"Scene {scene_id} not found",
                "details": None,
            },
        )

    results_dir = os.path.join(settings.data_root, "results", scene_id)
    analytics_file = os.path.join(results_dir, "analytics.json")
    risk_tif = os.path.join(results_dir, "risk.tif")

    if not os.path.exists(risk_tif):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "RESULT_NOT_READY",
                "message": "Inference has not completed for this scene.",
                "details": None,
            },
        )

    # Read base analytics cache
    if os.path.exists(analytics_file):
        with open(analytics_file, "r") as af:
            data = json.load(af)
    else:
        data = {
            "scene_id": scene_id,
            "threshold": threshold,
            "acres_total": scene["acres"],
            "acres_at_risk": 0.0,
            "percent_at_risk": 0.0,
            "zones_count": 0,
            "anomalies": [],
            "risk_histogram": {"bins": [0.0, 0.2, 0.4, 0.6, 0.8, 1.0], "counts": [0, 0, 0, 0, 0]},
        }

    # If threshold matches base, return
    if abs(data.get("threshold", 0.5) - threshold) < 1e-4:
        return data

    # Otherwise recompute dynamically from stored risk raster (fast windowed stats)
    with rasterio.open(risk_tif) as src:
        risk_arr = src.read(1)

    px_area_m2 = (scene["raster"]["pixel_size_m"]) ** 2
    px_to_acres = px_area_m2 / 4046.8564224

    total_px = risk_arr.size
    at_risk_px = int(np.sum((risk_arr >= threshold) & (risk_arr <= 1.0)))

    data["threshold"] = threshold
    data["acres_at_risk"] = round(float(at_risk_px * px_to_acres), 1)
    data["percent_at_risk"] = round(float(100.0 * at_risk_px / total_px), 1)

    return data
