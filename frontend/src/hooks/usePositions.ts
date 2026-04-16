"use client";

import { useState, useEffect, useCallback } from "react";
import type { SatellitePosition } from "@/lib/types";
import { getPositions } from "@/lib/api";

const REFRESH_INTERVAL = 30_000; // 30 seconds

export function usePositions(limit = 2000, objectType?: string) {
  const [positions, setPositions] = useState<SatellitePosition[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const data = await getPositions(limit, objectType);
      setPositions(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch positions");
    } finally {
      setLoading(false);
    }
  }, [limit, objectType]);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, REFRESH_INTERVAL);
    return () => clearInterval(interval);
  }, [fetchData]);

  return { positions, loading, error, refetch: fetchData };
}
