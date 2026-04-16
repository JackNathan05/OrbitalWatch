"use client";

import { useState, useEffect } from "react";
import type { SatelliteDetail, ConjunctionSummary } from "@/lib/types";
import { getSatelliteDetail, getSatelliteConjunctions } from "@/lib/api";
import { RISK_COLORS } from "@/lib/types";

interface SatellitePanelProps {
  noradId: number;
  onClose: () => void;
}

export default function SatellitePanel({ noradId, onClose }: SatellitePanelProps) {
  const [satellite, setSatellite] = useState<SatelliteDetail | null>(null);
  const [conjunctions, setConjunctions] = useState<ConjunctionSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      getSatelliteDetail(noradId),
      getSatelliteConjunctions(noradId),
    ])
      .then(([sat, conjs]) => {
        setSatellite(sat);
        setConjunctions(conjs);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [noradId]);

  if (loading) {
    return <div className="p-4 text-gray-400 text-sm">Loading satellite data...</div>;
  }

  if (!satellite) {
    return <div className="p-4 text-gray-400 text-sm">Satellite not found.</div>;
  }

  const typeColors: Record<string, string> = {
    PAYLOAD: "text-blue-400 bg-blue-400/10",
    "ROCKET BODY": "text-yellow-400 bg-yellow-400/10",
    DEBRIS: "text-red-400 bg-red-400/10",
    UNKNOWN: "text-gray-400 bg-gray-400/10",
  };

  return (
    <div className="p-4 overflow-y-auto">
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="text-white font-semibold text-lg">{satellite.object_name}</h3>
          <div className="flex items-center gap-2 mt-1">
            <span className={`text-xs px-2 py-0.5 rounded ${typeColors[satellite.object_type] || typeColors.UNKNOWN}`}>
              {satellite.object_type}
            </span>
            <span className="text-gray-400 text-xs font-mono">NORAD {satellite.norad_cat_id}</span>
          </div>
        </div>
        <button onClick={onClose} className="text-gray-400 hover:text-white text-lg leading-none">
          x
        </button>
      </div>

      {/* Metadata */}
      <div className="bg-gray-800 rounded-md p-3 mb-4 space-y-1.5 text-sm">
        {satellite.country_code && <InfoRow label="Country" value={satellite.country_code} />}
        {satellite.launch_date && (
          <InfoRow label="Launch Date" value={new Date(satellite.launch_date).toLocaleDateString()} />
        )}
        {satellite.object_id && <InfoRow label="Object ID" value={satellite.object_id} />}
      </div>

      {/* Orbital Elements */}
      <h4 className="text-gray-400 text-xs font-semibold uppercase tracking-wider mb-2">
        Orbital Elements
      </h4>
      <div className="bg-gray-800 rounded-md p-3 mb-4 space-y-1.5 text-sm">
        <InfoRow label="Inclination" value={`${satellite.inclination.toFixed(2)}\u00B0`} />
        <InfoRow label="Eccentricity" value={satellite.eccentricity.toFixed(6)} />
        <InfoRow label="Mean Motion" value={`${satellite.mean_motion.toFixed(4)} rev/day`} />
        {satellite.period_minutes && (
          <InfoRow label="Period" value={`${satellite.period_minutes.toFixed(1)} min`} />
        )}
        {satellite.apogee_km && (
          <InfoRow label="Apogee" value={`${Math.round(satellite.apogee_km)} km`} />
        )}
        {satellite.perigee_km && (
          <InfoRow label="Perigee" value={`${Math.round(satellite.perigee_km)} km`} />
        )}
        <InfoRow label="Epoch" value={new Date(satellite.epoch).toUTCString()} />
      </div>

      {/* Active Conjunctions */}
      <h4 className="text-gray-400 text-xs font-semibold uppercase tracking-wider mb-2">
        Conjunctions ({satellite.active_conjunction_count} active)
      </h4>
      {conjunctions.length > 0 ? (
        <div className="space-y-1">
          {conjunctions.slice(0, 10).map((c) => (
            <div key={c.cdm_id} className="bg-gray-800 rounded-md px-3 py-2 text-sm">
              <div className="flex items-center gap-2">
                <div
                  className="w-2 h-2 rounded-full"
                  style={{ backgroundColor: RISK_COLORS[c.risk_level] }}
                />
                <span className="text-white">
                  vs {c.sat1_norad_id === noradId ? c.sat2_object_name : c.sat1_object_name}
                </span>
              </div>
              <div className="text-xs text-gray-400 ml-4 mt-0.5">
                {new Date(c.tca).toUTCString()} - {Math.round(c.miss_distance_m)} m
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-gray-500 text-sm">No recent conjunctions.</p>
      )}
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-gray-400">{label}</span>
      <span className="text-white font-mono text-xs">{value}</span>
    </div>
  );
}
