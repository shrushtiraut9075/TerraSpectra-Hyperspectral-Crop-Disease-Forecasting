import {
  Scene,
  JobStatus,
  LatestResults,
  AnalyticsData,
  TimelineResponse,
  FieldItem,
  FieldCreateInput,
  LocationSearchResult,
} from '../types';

const API_BASE = (import.meta as any).env?.VITE_API_BASE_URL || '/api/v1';

export async function fetchFields(): Promise<FieldItem[]> {
  const res = await fetch(`${API_BASE}/fields`);
  if (!res.ok) throw new Error('Failed to fetch fields');
  return res.json();
}

export async function createField(input: FieldCreateInput): Promise<FieldItem> {
  const res = await fetch(`${API_BASE}/fields`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err?.error?.message || 'Failed to create farm');
  }
  return res.json();
}

export async function searchLocations(query: string): Promise<LocationSearchResult[]> {
  if (!query || query.trim().length < 2) return [];
  const res = await fetch(`${API_BASE}/fields/search?q=${encodeURIComponent(query.trim())}`);
  if (!res.ok) return [];
  return res.json();
}

export async function fetchHealth(): Promise<{ status: string; gpu: boolean; model_loaded: boolean; version: string }> {
  const healthUrl = API_BASE.includes('/api/v1') ? ${API_BASE}/health : '/health';
  const res = await fetch(healthUrl);
  if (!res.ok) throw new Error('Health check failed');
  return res.json();
}

export async function fetchScenes(fieldId?: string): Promise<Scene[]> {
  const url = fieldId ? `${API_BASE}/scenes?field_id=${encodeURIComponent(fieldId)}` : `${API_BASE}/scenes`;
  const res = await fetch(url);
  if (!res.ok) throw new Error('Failed to fetch scenes');
  return res.json();
}

export async function fetchScene(sceneId: string): Promise<Scene> {
  const res = await fetch(`${API_BASE}/scenes/${sceneId}`);
  if (!res.ok) throw new Error(`Failed to fetch scene ${sceneId}`);
  return res.json();
}

export async function startInferenceJob(
  sceneId: string,
  params: { model?: string; horizon_days?: number; tile_size?: number; overlap?: number } = {}
): Promise<{ job_id: string; status: string }> {
  const res = await fetch(`${API_BASE}/scenes/${sceneId}/jobs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      model: params.model || 'hybrid-v1',
      horizon_days: params.horizon_days || 21,
      tile_size: params.tile_size || 256,
      overlap: params.overlap || 32,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err?.error?.message || 'Failed to start inference job');
  }
  return res.json();
}

export async function fetchJobStatus(jobId: string): Promise<JobStatus> {
  const res = await fetch(`${API_BASE}/jobs/${jobId}`);
  if (!res.ok) throw new Error('Failed to fetch job status');
  return res.json();
}

export async function fetchLatestResults(sceneId: string): Promise<LatestResults | null> {
  const res = await fetch(`${API_BASE}/scenes/${sceneId}/results/latest`);
  if (res.status === 409 || res.status === 404) return null;
  if (!res.ok) throw new Error('Failed to fetch results');
  return res.json();
}

export async function fetchAnalytics(sceneId: string, threshold: number = 0.5): Promise<AnalyticsData | null> {
  const res = await fetch(`${API_BASE}/scenes/${sceneId}/analytics?threshold=${threshold}`);
  if (res.status === 409 || res.status === 404) return null;
  if (!res.ok) throw new Error('Failed to fetch analytics');
  return res.json();
}

export async function fetchZonesGeoJson(sceneId: string, threshold: number = 0.5): Promise<any | null> {
  const res = await fetch(`${API_BASE}/scenes/${sceneId}/results/zones.geojson?threshold=${threshold}`);
  if (res.status === 409 || res.status === 404) return null;
  if (!res.ok) throw new Error('Failed to fetch zones GeoJSON');
  return res.json();
}

export async function fetchTimeline(fieldId: string, threshold: number = 0.5): Promise<TimelineResponse> {
  const res = await fetch(`${API_BASE}/fields/${encodeURIComponent(fieldId)}/timeline?threshold=${threshold}`);
  if (!res.ok) throw new Error('Failed to fetch timeline');
  return res.json();
}
