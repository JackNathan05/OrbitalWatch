"use client";

import { useState, useEffect } from "react";
import type { PlatformStats } from "@/lib/types";
import { getStats } from "@/lib/api";

export default function StatsBar() {
  const [stats, setStats] = useState<PlatformStats | null>(null);

  useEffect(() => {
    getStats().then(setStats).catch(() => {});
    const interval = setInterval(() => {
      getStats().then(setStats).catch(() => {});
    }, 60_000);
    return () => clearInterval(interval);
  }, []);

  const formatTime = (iso?: string) => {
    if (!iso) return "Never";
    const d = new Date(iso);
    const mins = Math.floor((Date.now() - d.getTime()) / 60000);
    if (mins < 1) return "Just now";
    if (mins < 60) return `${mins}m ago`;
    return `${Math.floor(mins / 60)}h ago`;
  };

  if (!stats) {
    return (
      <div className="bg-gray-900 border-b border-gray-800 px-4 py-2 flex items-center gap-6 text-sm text-gray-400">
        <span>Loading stats...</span>
      </div>
    );
  }

  return (
    <div className="bg-gray-900 border-b border-gray-800 px-4 py-2 flex items-center gap-6 text-sm">
      <div className="flex items-center gap-2">
        <span className="text-gray-400">Tracked:</span>
        <span className="text-white font-mono font-semibold">
          {stats.total_objects_tracked.toLocaleString()}
        </span>
      </div>

      <div className="w-px h-4 bg-gray-700" />

      <div className="flex items-center gap-2">
        <span className="text-gray-400">Active Conjunctions (7d):</span>
        <span className="text-yellow-400 font-mono font-semibold">
          {stats.active_conjunctions_7d.toLocaleString()}
        </span>
      </div>

      <div className="w-px h-4 bg-gray-700" />

      <div className="flex items-center gap-2">
        <span className="text-gray-400">High Risk:</span>
        <span className={`font-mono font-semibold ${stats.high_risk_events > 0 ? "text-red-400" : "text-green-400"}`}>
          {stats.high_risk_events}
        </span>
      </div>

      <div className="flex-1" />

      <div className="flex items-center gap-4 text-xs text-gray-500">
        <span>TLE: {formatTime(stats.last_tle_update)}</span>
        <span>CDM: {formatTime(stats.last_cdm_update)}</span>
      </div>
    </div>
  );
}
