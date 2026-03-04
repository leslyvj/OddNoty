"use client";

import OddsChart from "@/components/OddsChart";

interface MatchDetailProps {
    params: { id: string };
}

export default function MatchDetailPage({ params }: MatchDetailProps) {
    const { id } = params;

    return (
        <>
            <div className="page-header">
                <h1>Match Details</h1>
                <p>Match ID: {id}</p>
            </div>

            <div className="card" style={{ marginBottom: "var(--space-lg)" }}>
                <h2 style={{ fontSize: "1.2rem", marginBottom: "var(--space-md)" }}>
                    Live Score
                </h2>
                {/* TODO: fetch and display live score */}
                <p style={{ color: "var(--text-secondary)" }}>Loading match data...</p>
            </div>

            <div className="card">
                <h2 style={{ fontSize: "1.2rem", marginBottom: "var(--space-md)" }}>
                    📈 Odds Movement
                </h2>
                <OddsChart matchId={id} />
            </div>
        </>
    );
}
