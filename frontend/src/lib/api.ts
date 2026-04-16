const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchApi<T>(path: string, params?: Record<string, string>): Promise<T> {
  const url = new URL(`${API_BASE}${path}`);
  if (params) {
    Object.entries(params).forEach(([key, val]) => url.searchParams.set(key, val));
  }

  const res = await fetch(url.toString());
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

import type {
  SatellitePosition,
  SatelliteDetail,
  ConjunctionSummary,
  ConjunctionDetail,
  PlatformStats,
  SatelliteSearchResult,
  OrbitTrail,
} from "./types";

export async function getPositions(limit = 2000, objectType?: string): Promise<SatellitePosition[]> {
  const params: Record<string, string> = { limit: String(limit) };
  if (objectType) params.object_type = objectType;
  return fetchApi("/api/positions", params);
}

export async function getOrbitTrail(noradId: number): Promise<OrbitTrail> {
  return fetchApi(`/api/positions/${noradId}/trail`);
}

export async function getConjunctions(
  minPc = 1e-5,
  days = 7,
  riskLevel?: string,
  limit = 100,
): Promise<ConjunctionSummary[]> {
  const params: Record<string, string> = {
    min_pc: String(minPc),
    days: String(days),
    limit: String(limit),
  };
  if (riskLevel) params.risk_level_filter = riskLevel;
  return fetchApi("/api/conjunctions", params);
}

export async function getConjunctionDetail(cdmId: string): Promise<ConjunctionDetail> {
  return fetchApi(`/api/conjunctions/${encodeURIComponent(cdmId)}`);
}

export async function searchSatellites(query: string, limit = 10): Promise<SatelliteSearchResult[]> {
  return fetchApi("/api/satellites/search", { q: query, limit: String(limit) });
}

export async function getSatelliteDetail(noradId: number): Promise<SatelliteDetail> {
  return fetchApi(`/api/satellites/${noradId}`);
}

export async function getSatelliteConjunctions(noradId: number, days = 90): Promise<ConjunctionSummary[]> {
  return fetchApi(`/api/satellites/${noradId}/conjunctions`, { days: String(days) });
}

export async function getStats(): Promise<PlatformStats> {
  return fetchApi("/api/stats");
}
