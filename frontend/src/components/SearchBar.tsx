"use client";

import { useState, useRef, useEffect } from "react";
import type { SatelliteSearchResult } from "@/lib/types";
import { searchSatellites } from "@/lib/api";

interface SearchBarProps {
  onSelect: (noradId: number) => void;
}

export default function SearchBar({ onSelect }: SearchBarProps) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SatelliteSearchResult[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(undefined);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!query || query.length < 2) {
      setResults([]);
      setOpen(false);
      return;
    }

    setLoading(true);
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(async () => {
      try {
        const data = await searchSatellites(query);
        setResults(data);
        setOpen(true);
      } catch {
        setResults([]);
      } finally {
        setLoading(false);
      }
    }, 300);

    return () => clearTimeout(debounceRef.current);
  }, [query]);

  // Close dropdown on outside click
  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const typeColor: Record<string, string> = {
    PAYLOAD: "text-blue-400",
    "ROCKET BODY": "text-yellow-400",
    DEBRIS: "text-red-400",
    UNKNOWN: "text-gray-400",
  };

  return (
    <div ref={containerRef} className="relative">
      <div className="relative">
        <input
          type="text"
          placeholder="Search satellites (name or NORAD ID)..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="w-64 bg-gray-800 border border-gray-700 rounded-md px-3 py-1.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
        />
        {loading && (
          <div className="absolute right-2 top-1/2 -translate-y-1/2">
            <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
          </div>
        )}
      </div>

      {open && results.length > 0 && (
        <div className="absolute top-full mt-1 w-80 bg-gray-800 border border-gray-700 rounded-md shadow-xl z-50 max-h-80 overflow-y-auto">
          {results.map((sat) => (
            <button
              key={sat.norad_cat_id}
              onClick={() => {
                onSelect(sat.norad_cat_id);
                setOpen(false);
                setQuery("");
              }}
              className="w-full text-left px-3 py-2 hover:bg-gray-700 border-b border-gray-700/50 last:border-0"
            >
              <div className="flex items-center justify-between">
                <span className="text-white text-sm font-medium">{sat.object_name}</span>
                <span className={`text-xs ${typeColor[sat.object_type] || "text-gray-400"}`}>
                  {sat.object_type}
                </span>
              </div>
              <div className="flex items-center gap-3 text-xs text-gray-400 mt-0.5">
                <span>NORAD: {sat.norad_cat_id}</span>
                {sat.apogee_km && <span>Alt: {Math.round(sat.apogee_km)} km</span>}
                {sat.conjunction_count > 0 && (
                  <span className="text-yellow-400">{sat.conjunction_count} conjunctions</span>
                )}
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
