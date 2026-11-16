import json
import os

import numpy as np
import rasterio
from fastapi import APIRouter, HTTPException, status

from api.schemas import TimelinePoint, TimelineResponse
from api.services.db import list_scenes
from api.settings import settings

router = APIRouter(prefix="/fields", tags=["timeline"])


@router.get("/{field_id}/timeline", response_model=TimelineResponse)
def get_field_timeline(field_id: str, threshold: float = 0.5):
    scenes = list_scenes(field_id=field_id)
    if not scenes:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "SCENE_NOT_FOUND",
                "message": f"No scenes found for field {field_id}",
                "details": None,
            },
        )

    points = []
    for sc in scenes:
        s_id = sc["id"]
        results_dir = os.path.join(settings.data_root, "results", s_id)
        risk_tif = os.path.join(results_dir, "risk.tif")
        analytics_file = os.path.join(results_dir, "analytics.json")

        acres_at_risk = 0.0
        mean_risk = 0.0

        if os.path.exists(risk_tif):
            with rasterio.open(risk_tif) as src:
                risk_arr = src.read(1)
            px_area_m2 = (sc["raster"]["pixel_size_m"]) ** 2
            px_to_acres = px_area_m2 / 4046.8564224
            at_risk_mask = (risk_arr >= threshold) & (risk_arr <= 1.0)
            acres_at_risk = round(float(np.sum(at_risk_mask) * px_to_acres), 1)
            valid_mask = ~np.isnan(risk_arr)
            mean_risk = (
                round(float(np.mean(risk_arr[valid_mask])), 2) if np.any(valid_mask) else 0.0
            )
        elif os.path.exists(analytics_file):
            with open(analytics_file, "r") as af:
                adata = json.load(af)
            acres_at_risk = adata.get("acres_at_risk", 0.0)
            mean_risk = 0.15

        points.append(
            TimelinePoint(
                scene_id=s_id,
                acquired_at=sc["acquired_at"],
                acres_at_risk=acres_at_risk,
                mean_risk=mean_risk,
            )
        )

    return TimelineResponse(field_id=field_id, points=points)
