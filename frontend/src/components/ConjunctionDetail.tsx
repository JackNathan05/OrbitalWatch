"use client";

import { useState, useEffect } from "react";
import type { ConjunctionDetail as ConjunctionDetailType } from "@/lib/types";
import { RISK_COLORS } from "@/lib/types";
import { getConjunctionDetail } from "@/lib/api";

interface ConjunctionDetailProps {
  cdmId: string;
  onClose: () => void;
}

export default function ConjunctionDetail({ cdmId, onClose }: ConjunctionDetailProps) {
  const [detail, setDetail] = useState<ConjunctionDetailType | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getConjunctionDetail(cdmId)
      .then(setDetail)
      .catch(() => setDetail(null))
      .finally(() => setLoading(false));
  }, [cdmId]);

  if (loading) {
    return (
      <div className="p-4 text-gray-400 text-sm">Loading CDM details...</div>
    );
  }

  if (!detail) {
    return (
      <div className="p-4 text-gray-400 text-sm">Failed to load conjunction details.</div>
    );
  }

  return (
    <div className="p-4 overflow-y-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-white font-semibold">Conjunction Detail</h3>
        <button
          onClick={onClose}
          className="text-gray-400 hover:text-white text-lg leading-none"
        >
          x
        </button>
      </div>

      {/* Risk Banner */}
      <div
        className="rounded-md px-3 py-2 mb-4 text-sm"
        style={{
          backgroundColor: `${RISK_COLORS[detail.risk_level]}20`,
          borderLeft: `3px solid ${RISK_COLORS[detail.risk_level]}`,
        }}
      >
        <div className="font-semibold" style={{ color: RISK_COLORS[detail.risk_level] }}>
          {detail.risk_level} RISK
        </div>
        <p className="text-gray-300 mt-1 text-xs leading-relaxed">
          {detail.plain_english_summary}
        </p>
      </div>

      {/* Objects involved */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        <div className="bg-gray-800 rounded-md p-2">
          <div className="text-xs text-gray-400 mb-1">Object 1</div>
          <div className="text-white text-sm font-medium">{detail.sat1_object_name}</div>
          <div className="text-xs text-gray-400">
            NORAD {detail.sat1_norad_id} - {detail.sat1_object_type}
          </div>
        </div>
        <div className="bg-gray-800 rounded-md p-2">
          <div className="text-xs text-gray-400 mb-1">Object 2</div>
          <div className="text-white text-sm font-medium">{detail.sat2_object_name}</div>
          <div className="text-xs text-gray-400">
            NORAD {detail.sat2_norad_id} - {detail.sat2_object_type}
          </div>
        </div>
      </div>

      {/* Key metrics */}
      <div className="space-y-2 mb-4">
        <DetailRow label="Time of Closest Approach" value={new Date(detail.tca).toUTCString()} />
        <DetailRow label="Miss Distance" value={`${detail.miss_distance_m.toLocaleString()} m`} />
        <DetailRow
          label="Collision Probability"
          value={detail.collision_probability.toExponential(2)}
          highlight={RISK_COLORS[detail.risk_level]}
        />
        {detail.relative_speed_ms && (
          <DetailRow
            label="Relative Speed"
            value={`${detail.relative_speed_ms.toLocaleString()} m/s (${(detail.relative_speed_ms * 3.6).toLocaleString(undefined, { maximumFractionDigits: 0 })} km/h)`}
          />
        )}
        <DetailRow label="CDM Created" value={new Date(detail.creation_date).toUTCString()} />
        <DetailRow label="CDM ID" value={detail.cdm_id} mono />
      </div>

      {/* Disclaimer */}
      <div className="bg-gray-800/50 rounded-md p-2 text-xs text-gray-500 leading-relaxed">
        Most conjunctions don't lead to maneuvers. Operators use non-public data
        when making avoidance decisions. This is an educational tool, not an operational one.
        Source: Space-Track.org (18 SDS, USSPACECOM).
      </div>
    </div>
  );
}

function DetailRow({
  label,
  value,
  highlight,
  mono,
}: {
  label: string;
  value: string;
  highlight?: string;
  mono?: boolean;
}) {
  return (
    <div className="flex items-start justify-between text-sm">
      <span className="text-gray-400">{label}</span>
      <span
        className={`text-right ml-2 ${mono ? "font-mono text-xs" : ""}`}
        style={highlight ? { color: highlight } : { color: "white" }}
      >
        {value}
      </span>
    </div>
  );
}
