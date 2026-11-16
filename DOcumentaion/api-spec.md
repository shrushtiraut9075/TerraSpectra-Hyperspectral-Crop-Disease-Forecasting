# API Spec — TerraSpectra Inference Service (FastAPI)

Base URL (dev): `http://localhost:8000/api/v1` · All responses JSON unless noted · Pydantic v2 schemas · OpenAPI at `/docs`.

## 1. Conventions

- IDs are UUID strings.
- Timestamps are ISO-8601 UTC.
- Geometries are GeoJSON in **EPSG:4326**.
- Errors use one shape:
```json
{ "error": { "code": "SCENE_NOT_FOUND", "message": "Scene 123 does not exist", "details": null } }
```
- Long-running work is **async**: start a job, poll its status.

## 2. Endpoints

### Health
`GET /health` → `{ "status": "ok", "gpu": true, "model_loaded": true, "version": "1.0.0" }`

### Scenes

`POST /scenes` — register a scene already on the server (preferred for multi-GB files) or upload a small one.

Request (JSON, registration by server path ID from an allow-listed data root):
```json
{
  "name": "Farm A — 2026-06-01",
  "field_id": "farm-a",
  "acquired_at": "2026-06-01T10:30:00Z",
  "source_ref": "synth_v1/scene_000/t03.tif",
  "data_origin": "synthetic"
}
```
Response `201`:
```json
{
  "id": "5f1c…",
  "name": "Farm A — 2026-06-01",
  "field_id": "farm-a",
  "acquired_at": "2026-06-01T10:30:00Z",
  "data_origin": "synthetic",
  "raster": { "width": 400, "height": 400, "bands": 224, "crs": "EPSG:32643", "pixel_size_m": 10.0 },
  "bounds_wgs84": [73.7, 18.5, 73.75, 18.55],
  "acres": 1000.4
}
```
Validation errors: `422 INVALID_RASTER`, `422 MISSING_CRS`, `404 SOURCE_NOT_FOUND`.

`POST /scenes/upload` — multipart upload (size-limited; for demo-sized files only).

`GET /scenes?field_id=farm-a` — list scenes (sorted by `acquired_at`).
`GET /scenes/{scene_id}` — scene detail.
`DELETE /scenes/{scene_id}` — delete scene and derived results.

### Jobs (inference)

`POST /scenes/{scene_id}/jobs`
```json
{ "model": "hybrid-v1", "horizon_days": 21, "tile_size": 256, "overlap": 32 }
```
Response `202`:
```json
{ "job_id": "9a2b…", "status": "queued" }
```

`GET /jobs/{job_id}`
```json
{
  "job_id": "9a2b…",
  "scene_id": "5f1c…",
  "status": "running",
  "progress": 0.42,
  "tiles_done": 17,
  "tiles_total": 40,
  "started_at": "…",
  "finished_at": null,
  "error": null
}
```
Status values: `queued | running | succeeded | failed | cancelled`.
`POST /jobs/{job_id}/cancel` — best-effort cancel.

### Results

`GET /scenes/{scene_id}/results/latest` →
```json
{
  "job_id": "9a2b…",
  "risk_raster_url": "/api/v1/scenes/5f1c…/results/risk.tif",
  "tiles_url_template": "/api/v1/scenes/5f1c…/tiles/{z}/{x}/{y}.png",
  "zones_url": "/api/v1/scenes/5f1c…/results/zones.geojson",
  "model": "hybrid-v1",
  "horizon_days": 21,
  "bounds_wgs84": [73.7, 18.5, 73.75, 18.55]
}
```

`GET /scenes/{scene_id}/tiles/{z}/{x}/{y}.png?threshold=0.5&cmap=risk` — XYZ PNG tiles (transparent where no data; colour ramp green→yellow→red). Cache headers set.

`GET /scenes/{scene_id}/results/zones.geojson?threshold=0.5&min_area_acres=0.5` — risk zones as polygons with properties:
```json
{ "type": "Feature", "properties": { "zone_id": 3, "mean_risk": 0.87, "max_risk": 0.99, "area_acres": 4.8, "top_anomaly": "red-edge shift" }, "geometry": { … } }
```

### Analytics

`GET /scenes/{scene_id}/analytics?threshold=0.5`
```json
{
  "scene_id": "5f1c…",
  "threshold": 0.5,
  "acres_total": 1000.4,
  "acres_at_risk": 48.2,
  "percent_at_risk": 4.8,
  "zones_count": 9,
  "anomalies": [
    { "name": "Red-edge shift", "bands_nm": [690, 740], "share": 0.46 },
    { "name": "SWIR water stress", "bands_nm": [1450, 1950], "share": 0.31 },
    { "name": "NIR plateau drop", "bands_nm": [780, 900], "share": 0.23 }
  ],
  "risk_histogram": { "bins": [0, 0.1, …, 1.0], "counts": [ … ] }
}
```
`anomalies` come from the explainability step (perturbation-validated); if unavailable return an empty list, not made-up values.

### Timeline

`GET /fields/{field_id}/timeline?threshold=0.5`
```json
{
  "field_id": "farm-a",
  "points": [
    { "scene_id": "…", "acquired_at": "2026-05-01T…", "acres_at_risk": 2.1, "mean_risk": 0.08 },
    { "scene_id": "…", "acquired_at": "2026-05-15T…", "acres_at_risk": 11.4, "mean_risk": 0.17 }
  ]
}
```

## 3. Schemas (Pydantic outline)

```python
class SceneCreate(BaseModel): name: str; field_id: str; acquired_at: datetime; source_ref: str; data_origin: Literal["synthetic","public","real"]
class RasterInfo(BaseModel): width:int; height:int; bands:int; crs:str; pixel_size_m:float
class Scene(SceneCreate): id:UUID; raster:RasterInfo; bounds_wgs84:tuple[float,float,float,float]; acres:float
class JobCreate(BaseModel): model:str="hybrid-v1"; horizon_days:int=21; tile_size:int=256; overlap:int=32
class JobStatus(BaseModel): job_id:UUID; scene_id:UUID; status:Literal["queued","running","succeeded","failed","cancelled"]; progress:float; tiles_done:int; tiles_total:int; error:str|None
```

## 4. Implementation Rules

- Routers thin; logic in `services/`.
- Inference runs off the event loop (thread/process pool); one GPU job at a time by default (semaphore).
- Model is loaded once at startup (lifespan), not per request.
- `source_ref` is resolved against `DATA_ROOT`; reject `..` and absolute paths.
- Upload limit configurable (`MAX_UPLOAD_MB`).
- Job state persisted (SQLite) so a restart does not lose history; jobs found `running` at startup are marked `failed`.
- Tile endpoint must not recompute inference; it reads the stored risk raster.
- CORS: allow only the configured web origin.
- Return `Cache-Control` and `ETag` for result files.

## 5. Error Codes

| Code | HTTP | When |
|---|---|---|
| `SCENE_NOT_FOUND` | 404 | Unknown scene id |
| `JOB_NOT_FOUND` | 404 | Unknown job id |
| `SOURCE_NOT_FOUND` | 404 | `source_ref` missing on disk |
| `INVALID_RASTER` | 422 | Unreadable or wrong band count |
| `MISSING_CRS` | 422 | Raster has no CRS |
| `MODEL_NOT_AVAILABLE` | 400 | Unknown model name |
| `RESULT_NOT_READY` | 409 | Results requested before a job succeeded |
| `GPU_OOM` | 500 | Out of GPU memory (job failed; suggest smaller tile) |
| `PAYLOAD_TOO_LARGE` | 413 | Upload over limit |

## 6. Contract Tests

- Registration then job then results happy path on a tiny synthetic scene.
- Each error code above reachable.
- Stitched risk raster has identical transform/CRS/shape to the source scene.
- Tile PNG for a known GCP location has the expected colour at the expected pixel.
