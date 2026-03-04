/**
 * Custom hook for fetching live matches.
 */

"use client";

import { useState, useEffect } from "react";
import { Match } from "@/types";
import { api } from "@/lib/api";

export function useMatches(refreshInterval = 10000) {
    const [matches, setMatches] = useState<Match[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        let isMounted = true;

        const fetchMatches = async () => {
            try {
                const data = (await api.getMatches({ status: "live" })) as Match[];
                if (isMounted) {
                    setMatches(data);
                    setError(null);
                }
            } catch (err) {
                if (isMounted) {
                    setError(err instanceof Error ? err.message : "Failed to fetch matches");
                }
            } finally {
                if (isMounted) setLoading(false);
            }
        };

        fetchMatches();
        const interval = setInterval(fetchMatches, refreshInterval);

        return () => {
            isMounted = false;
            clearInterval(interval);
        };
    }, [refreshInterval]);

    return { matches, loading, error };
}
