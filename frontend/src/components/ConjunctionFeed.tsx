"use client";

import type { ConjunctionSummary } from "@/lib/types";
import { RISK_COLORS } from "@/lib/types";

interface ConjunctionFeedProps {
  conjunctions: ConjunctionSummary[];
  loading: boolean;
  onSelect: (conjunction: ConjunctionSummary) => void;
  selectedId?: string;
}

export default function ConjunctionFeed({
  conjunctions,
  loading,
  onSelect,
  selectedId,
}: ConjunctionFeedProps) {
  const formatTca = (iso: string) => {
    const d = new Date(iso);
    const now = Date.now();
    const diff = d.getTime() - now;
    const hours = Math.floor(diff / 3_600_000);
    const days = Math.floor(hours / 24);

    if (days > 0) return `in ${days}d ${hours % 24}h`;
    if (hours > 0) return `in ${hours}h`;
    if (diff > 0) return `in ${Math.floor(diff / 60000)}m`;
    return "passed";
  };

  const formatPc = (pc: number) => {
    if (pc >= 1e-2) return `1 in ${Math.round(1 / pc)}`;
    return pc.toExponential(1);
  };

  if (loading) {
    return (
      <div className="p-4 text-gray-400 text-sm">Loading conjunctions...</div>
    );
  }

  if (conjunctions.length === 0) {
    return (
      <div className="p-4 text-gray-400 text-sm">
        No conjunctions found matching current filters.
      </div>
    );
  }

  return (
    <div className="overflow-y-auto flex-1">
      {conjunctions.map((c) => (
        <button
          key={c.cdm_id}
          onClick={() => onSelect(c)}
          className={`w-full text-left px-3 py-2.5 border-b border-gray-800 hover:bg-gray-800/50 transition-colors ${
            selectedId === c.cdm_id ? "bg-gray-800" : ""
          }`}
        >
          <div className="flex items-start gap-2">
            {/* Risk indicator */}
            <div
              className="w-2 h-2 rounded-full mt-1.5 shrink-0"
              style={{ backgroundColor: RISK_COLORS[c.risk_level] }}
            />
            <div className="flex-1 min-w-0">
              {/* Satellite names */}
              <div className="flex items-center gap-1 text-sm">
                <span className="text-white font-medium truncate">
                  {c.sat1_object_name || `#${c.sat1_norad_id}`}
                </span>
                <span className="text-gray-500 shrink-0">vs</span>
                <span className="text-white font-medium truncate">
                  {c.sat2_object_name || `#${c.sat2_norad_id}`}
                </span>
              </div>

              {/* Details row */}
              <div className="flex items-center gap-3 text-xs text-gray-400 mt-1">
                <span className="font-mono" style={{ color: RISK_COLORS[c.risk_level] }}>
                  Pc: {formatPc(c.collision_probability)}
                </span>
                <span>{Math.round(c.miss_distance_m)} m</span>
                <span>{formatTca(c.tca)}</span>
              </div>

              {/* Object types */}
              <div className="flex items-center gap-2 text-xs text-gray-500 mt-0.5">
                <span>{c.sat1_object_type}</span>
                <span>/</span>
                <span>{c.sat2_object_type}</span>
              </div>
            </div>
          </div>
        </button>
      ))}
    </div>
  );
}
