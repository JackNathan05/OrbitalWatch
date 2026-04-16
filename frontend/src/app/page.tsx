"use client";

import { useState, useCallback, useMemo } from "react";
import dynamic from "next/dynamic";
import type { SatellitePosition, ConjunctionSummary } from "@/lib/types";
import { usePositions } from "@/hooks/usePositions";
import { useConjunctions } from "@/hooks/useConjunctions";
import StatsBar from "@/components/StatsBar";
import SearchBar from "@/components/SearchBar";
import ConjunctionFeed from "@/components/ConjunctionFeed";
import ConjunctionDetail from "@/components/ConjunctionDetail";
import SatellitePanel from "@/components/SatellitePanel";

// Dynamic import for Globe to avoid SSR issues with Cesium
const Globe = dynamic(() => import("@/components/Globe"), {
  ssr: false,
  loading: () => (
    <div className="flex-1 flex items-center justify-center bg-gray-950 text-gray-400">
      <div className="text-center">
        <div className="animate-spin w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full mx-auto mb-3" />
        <p>Initializing OrbitalWatch...</p>
      </div>
    </div>
  ),
});

const ALL_TYPES = new Set(["PAYLOAD", "ROCKET BODY", "DEBRIS", "UNKNOWN"]);

export default function Home() {
  const { positions, loading: positionsLoading } = usePositions(5000);
  const { conjunctions, loading: conjunctionsLoading } = useConjunctions();

  const [selectedSatellite, setSelectedSatellite] = useState<number | null>(null);
  const [selectedConjunction, setSelectedConjunction] = useState<ConjunctionSummary | null>(null);
  const [showDetail, setShowDetail] = useState(false);
  const [visibleTypes, setVisibleTypes] = useState<Set<string>>(ALL_TYPES);
  const [conjunctionFocus, setConjunctionFocus] = useState<{
    lat: number;
    lon: number;
    alt: number;
  } | null>(null);

  // Sidebar mode
  const [sidebarTab, setSidebarTab] = useState<"conjunctions" | "satellite">("conjunctions");

  const handleSatelliteClick = useCallback((sat: SatellitePosition) => {
    setSelectedSatellite(sat.norad_cat_id);
    setSidebarTab("satellite");
    setShowDetail(false);
  }, []);

  const handleConjunctionSelect = useCallback(
    (conjunction: ConjunctionSummary) => {
      setSelectedConjunction(conjunction);
      setShowDetail(true);

      // Find position of first satellite to zoom to
      const sat = positions.find(
        (p) =>
          p.norad_cat_id === conjunction.sat1_norad_id ||
          p.norad_cat_id === conjunction.sat2_norad_id,
      );
      if (sat) {
        setConjunctionFocus({
          lat: sat.latitude,
          lon: sat.longitude,
          alt: sat.altitude_km,
        });
      }
    },
    [positions],
  );

  const handleSearchSelect = useCallback((noradId: number) => {
    setSelectedSatellite(noradId);
    setSidebarTab("satellite");
    setShowDetail(false);
  }, []);

  const toggleType = useCallback((type: string) => {
    setVisibleTypes((prev) => {
      const next = new Set(prev);
      if (next.has(type)) next.delete(type);
      else next.add(type);
      return next;
    });
  }, []);

  const memoizedVisibleTypes = useMemo(() => visibleTypes, [visibleTypes]);

  return (
    <div className="h-screen flex flex-col bg-gray-950">
      {/* Stats Bar */}
      <StatsBar />

      {/* Toolbar */}
      <div className="bg-gray-900/80 border-b border-gray-800 px-4 py-2 flex items-center gap-4">
        <h1 className="text-white font-bold text-lg tracking-tight">
          ORBITAL<span className="text-blue-400">WATCH</span>
        </h1>

        <div className="w-px h-5 bg-gray-700" />

        <SearchBar onSelect={handleSearchSelect} />

        <div className="flex-1" />

        {/* Layer toggles */}
        <div className="flex items-center gap-2 text-xs">
          <span className="text-gray-400">Show:</span>
          {[
            { type: "PAYLOAD", label: "Payloads", color: "bg-blue-500" },
            { type: "ROCKET BODY", label: "Rockets", color: "bg-yellow-500" },
            { type: "DEBRIS", label: "Debris", color: "bg-red-500" },
            { type: "UNKNOWN", label: "Unknown", color: "bg-gray-500" },
          ].map(({ type, label, color }) => (
            <button
              key={type}
              onClick={() => toggleType(type)}
              className={`flex items-center gap-1.5 px-2 py-1 rounded transition-colors ${
                visibleTypes.has(type)
                  ? "bg-gray-700 text-white"
                  : "bg-gray-800/50 text-gray-500"
              }`}
            >
              <div className={`w-2 h-2 rounded-full ${color} ${!visibleTypes.has(type) ? "opacity-30" : ""}`} />
              {label}
            </button>
          ))}
        </div>

        {/* Object count */}
        {!positionsLoading && (
          <span className="text-gray-500 text-xs font-mono">
            {positions.filter((p) => visibleTypes.has(p.object_type)).length.toLocaleString()} objects
          </span>
        )}
      </div>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Globe */}
        <div className="flex-1 relative">
          <Globe
            positions={positions}
            onSatelliteClick={handleSatelliteClick}
            onConjunctionFocus={conjunctionFocus}
            visibleTypes={memoizedVisibleTypes}
          />
        </div>

        {/* Right Sidebar */}
        <div className="w-96 bg-gray-900 border-l border-gray-800 flex flex-col">
          {/* Sidebar tabs */}
          <div className="flex border-b border-gray-800">
            <button
              onClick={() => {
                setSidebarTab("conjunctions");
                setShowDetail(false);
              }}
              className={`flex-1 px-3 py-2 text-sm font-medium transition-colors ${
                sidebarTab === "conjunctions"
                  ? "text-white border-b-2 border-blue-500"
                  : "text-gray-400 hover:text-gray-300"
              }`}
            >
              Conjunctions
            </button>
            <button
              onClick={() => setSidebarTab("satellite")}
              className={`flex-1 px-3 py-2 text-sm font-medium transition-colors ${
                sidebarTab === "satellite"
                  ? "text-white border-b-2 border-blue-500"
                  : "text-gray-400 hover:text-gray-300"
              }`}
            >
              Satellite Detail
            </button>
          </div>

          {/* Sidebar content */}
          <div className="flex-1 overflow-hidden flex flex-col">
            {sidebarTab === "conjunctions" && !showDetail && (
              <ConjunctionFeed
                conjunctions={conjunctions}
                loading={conjunctionsLoading}
                onSelect={handleConjunctionSelect}
                selectedId={selectedConjunction?.cdm_id}
              />
            )}

            {sidebarTab === "conjunctions" && showDetail && selectedConjunction && (
              <ConjunctionDetail
                cdmId={selectedConjunction.cdm_id}
                onClose={() => setShowDetail(false)}
              />
            )}

            {sidebarTab === "satellite" && selectedSatellite && (
              <SatellitePanel
                noradId={selectedSatellite}
                onClose={() => {
                  setSelectedSatellite(null);
                  setSidebarTab("conjunctions");
                }}
              />
            )}

            {sidebarTab === "satellite" && !selectedSatellite && (
              <div className="p-4 text-gray-400 text-sm">
                Click a satellite on the globe or use the search bar to view details.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
