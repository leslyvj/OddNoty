/**
 * API client helpers for OddNoty frontend.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchAPI<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const res = await fetch(`${API_BASE}${endpoint}`, {
        headers: { "Content-Type": "application/json" },
        ...options,
    });
    if (!res.ok) {
        throw new Error(`API error: ${res.status} ${res.statusText}`);
    }
    return res.json();
}

export const api = {
    // Matches
    getMatches: (params?: { status?: string; league?: string }) => {
        const qs = new URLSearchParams(params as Record<string, string>).toString();
        return fetchAPI(`/api/matches${qs ? `?${qs}` : ""}`);
    },
    getMatch: (matchId: string) => fetchAPI(`/api/matches/${matchId}`),

    // Odds
    getOdds: (matchId: string) => fetchAPI(`/api/odds/${matchId}`),
    getOddsHistory: (matchId: string) => fetchAPI(`/api/odds/${matchId}/history`),

    // Alerts
    getAlerts: () => fetchAPI("/api/alerts"),
    createRule: (rule: { name: string; conditions: Record<string, unknown> }) =>
        fetchAPI("/api/alerts/rules", { method: "POST", body: JSON.stringify(rule) }),
    getRules: () => fetchAPI("/api/alerts/rules"),
    deleteRule: (ruleId: number) =>
        fetchAPI(`/api/alerts/rules/${ruleId}`, { method: "DELETE" }),
};
