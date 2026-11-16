export interface RasterInfo {
  width: number;
  height: number;
  bands: number;
  crs: string;
  pixel_size_m: number;
}

export interface Scene {
  id: string;
  name: string;
  field_id: string;
  acquired_at: string;
  data_origin: 'synthetic' | 'public' | 'real';
  raster: RasterInfo;
  bounds_wgs84: [number, number, number, number]; // [min_lon, min_lat, max_lon, max_lat]
  acres: number;
}

export interface JobStatus {
  job_id: string;
  scene_id: string;
  status: 'queued' | 'running' | 'succeeded' | 'failed' | 'cancelled';
  progress: number;
  tiles_done: number;
  tiles_total: number;
  started_at?: string;
  finished_at?: string;
  error?: string | null;
}

export interface LatestResults {
  job_id: string;
  risk_raster_url: string;
  tiles_url_template: string;
  zones_url: string;
  model: string;
  horizon_days: number;
  bounds_wgs84: [number, number, number, number];
}

export interface AnomalyItem {
  name: string;
  bands_nm: [number, number];
  share: number;
}

export interface RiskHistogramData {
  bins: number[];
  counts: number[];
}

export interface AnalyticsData {
  scene_id: string;
  threshold: number;
  acres_total: number;
  acres_at_risk: number;
  percent_at_risk: number;
  zones_count: number;
  anomalies: AnomalyItem[];
  risk_histogram: RiskHistogramData;
}

export interface TimelinePoint {
  scene_id: string;
  acquired_at: string;
  acres_at_risk: number;
  mean_risk: number;
}

export interface TimelineResponse {
  field_id: string;
  points: TimelinePoint[];
}

export interface RiskZoneProperties {
  zone_id: number;
  mean_risk: number;
  max_risk: number;
  area_acres: number;
  top_anomaly: string;
}

export interface GroundControlPoint {
  col: number;
  row: number;
  lon: number;
  lat: number;
}

export interface FieldItem {
  id: string;
  name: string;
  crop_type: string;
  acres: number;
  lat: number;
  lon: number;
  bounds_wgs84: [number, number, number, number];
  created_at: string;
}

export interface FieldCreateInput {
  name: string;
  lat: number;
  lon: number;
  acres?: number;
  crop_type?: string;
  disease_scenario?: string;
}

export interface LocationSearchResult {
  name: string;
  lat: number;
  lon: number;
}


