export interface SatellitePosition {
  norad_cat_id: number;
  object_name: string;
  object_type: "PAYLOAD" | "ROCKET BODY" | "DEBRIS" | "UNKNOWN";
  latitude: number;
  longitude: number;
  altitude_km: number;
}

export interface SatelliteDetail {
  norad_cat_id: number;
  object_name: string;
  object_type: string;
  object_id?: string;
  country_code?: string;
  launch_date?: string;
  epoch: string;
  mean_motion: number;
  eccentricity: number;
  inclination: number;
  period_minutes?: number;
  apogee_km?: number;
  perigee_km?: number;
  active_conjunction_count: number;
}

export interface ConjunctionSummary {
  cdm_id: string;
  tca: string;
  sat1_norad_id: number;
  sat1_object_name?: string;
  sat1_object_type?: string;
  sat2_norad_id: number;
  sat2_object_name?: string;
  sat2_object_type?: string;
  miss_distance_m: number;
  collision_probability: number;
  relative_speed_ms?: number;
  risk_level: "GREEN" | "YELLOW" | "ORANGE" | "RED";
}

export interface ConjunctionDetail extends ConjunctionSummary {
  creation_date: string;
  plain_english_summary: string;
  raw_json?: Record<string, unknown>;
}

export interface PlatformStats {
  total_objects_tracked: number;
  active_conjunctions_7d: number;
  high_risk_events: number;
  most_recent_high_risk?: ConjunctionSummary;
  last_tle_update?: string;
  last_cdm_update?: string;
}

export interface SatelliteSearchResult {
  norad_cat_id: number;
  object_name: string;
  object_type: string;
  apogee_km?: number;
  perigee_km?: number;
  conjunction_count: number;
}

export interface OrbitPoint {
  latitude: number;
  longitude: number;
  altitude_km: number;
  timestamp: string;
}

export interface OrbitTrail {
  norad_cat_id: number;
  points: OrbitPoint[];
}

// Color mapping for object types
export const OBJECT_TYPE_COLORS: Record<string, string> = {
  PAYLOAD: "#3B82F6",       // blue
  "ROCKET BODY": "#EAB308", // yellow
  DEBRIS: "#EF4444",        // red
  UNKNOWN: "#6B7280",       // gray
};

// Risk level colors
export const RISK_COLORS: Record<string, string> = {
  GREEN: "#22C55E",
  YELLOW: "#EAB308",
  ORANGE: "#F97316",
  RED: "#EF4444",
};
