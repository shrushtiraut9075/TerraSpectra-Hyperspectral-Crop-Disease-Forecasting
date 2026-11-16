from typing import Any, List, Literal, Optional, Tuple

from pydantic import BaseModel


class ApiErrorBody(BaseModel):
    code: str
    message: str
    details: Optional[Any] = None


class ApiErrorResponse(BaseModel):
    error: ApiErrorBody


class RasterInfo(BaseModel):
    width: int
    height: int
    bands: int
    crs: str
    pixel_size_m: float


class SceneCreate(BaseModel):
    name: str
    field_id: str
    acquired_at: str
    source_ref: str
    data_origin: Literal["synthetic", "public", "real"] = "synthetic"


class Scene(BaseModel):
    id: str
    name: str
    field_id: str
    acquired_at: str
    data_origin: Literal["synthetic", "public", "real"]
    raster: RasterInfo
    bounds_wgs84: Tuple[float, float, float, float]
    acres: float


class JobCreate(BaseModel):
    model: str = "hybrid-v1"
    horizon_days: int = 21
    tile_size: int = 256
    overlap: int = 32


class JobStatus(BaseModel):
    job_id: str
    scene_id: str
    status: Literal["queued", "running", "succeeded", "failed", "cancelled"]
    progress: float = 0.0
    tiles_done: int = 0
    tiles_total: int = 0
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    error: Optional[str] = None


class LatestResults(BaseModel):
    job_id: str
    risk_raster_url: str
    tiles_url_template: str
    zones_url: str
    model: str
    horizon_days: int
    bounds_wgs84: Tuple[float, float, float, float]


class AnomalyItem(BaseModel):
    name: str
    bands_nm: List[float]
    share: float


class RiskHistogram(BaseModel):
    bins: List[float]
    counts: List[int]


class AnalyticsResponse(BaseModel):
    scene_id: str
    threshold: float
    acres_total: float
    acres_at_risk: float
    percent_at_risk: float
    zones_count: int
    anomalies: List[AnomalyItem]
    risk_histogram: RiskHistogram


class TimelinePoint(BaseModel):
    scene_id: str
    acquired_at: str
    acres_at_risk: float
    mean_risk: float


class TimelineResponse(BaseModel):
    field_id: str
    points: List[TimelinePoint]


class LocationSearchResult(BaseModel):
    name: str
    lat: float
    lon: float


class FieldItem(BaseModel):
    id: str
    name: str
    crop_type: str
    acres: float
    lat: float
    lon: float
    bounds_wgs84: Tuple[float, float, float, float]
    created_at: str


class FieldCreateRequest(BaseModel):
    name: str
    lat: float
    lon: float
    acres: float = 250.0
    crop_type: str = "Sugarcane"
    disease_scenario: str = "early_onset"

