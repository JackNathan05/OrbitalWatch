"use client";

import { useState, useEffect, useCallback } from "react";
import type { ConjunctionSummary } from "@/lib/types";
import { getConjunctions } from "@/lib/api";

const REFRESH_INTERVAL = 60_000; // 1 minute

export function useConjunctions(minPc = 1e-5, days = 7) {
  const [conjunctions, setConjunctions] = useState<ConjunctionSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const data = await getConjunctions(minPc, days);
      setConjunctions(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch conjunctions");
    } finally {
      setLoading(false);
    }
  }, [minPc, days]);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, REFRESH_INTERVAL);
    return () => clearInterval(interval);
  }, [fetchData]);

  return { conjunctions, loading, error, refetch: fetchData };
}
