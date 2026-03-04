"use client";

import Link from "next/link";
import { Match } from "@/types";

// Placeholder data — replace with useMatches hook
const PLACEHOLDER_MATCHES: Match[] = [
    {
        match_id: "1",
        league: "Premier League",
        home_team: "Chelsea",
        away_team: "Arsenal",
        home_score: 0,
        away_score: 0,
        match_minute: 62,
        status: "live",
    },
    {
        match_id: "2",
        league: "La Liga",
        home_team: "Barcelona",
        away_team: "Real Madrid",
        home_score: 1,
        away_score: 1,
        match_minute: 78,
        status: "live",
    },
];

export default function MatchTable() {
    const matches = PLACEHOLDER_MATCHES;

    return (
        <div className="card">
            <table className="data-table" id="live-matches-table">
                <thead>
                    <tr>
                        <th>League</th>
                        <th>Match</th>
                        <th>Min</th>
                        <th>Score</th>
                        <th>Over 1.5</th>
                        <th>Over 2.5</th>
                        <th>Over 3.5</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    {matches.map((m) => (
                        <tr key={m.match_id}>
                            <td>{m.league}</td>
                            <td>
                                <Link href={`/match/${m.match_id}`}>
                                    {m.home_team} vs {m.away_team}
                                </Link>
                            </td>
                            <td>{m.match_minute}&apos;</td>
                            <td>
                                {m.home_score} - {m.away_score}
                            </td>
                            <td className="odds-value">—</td>
                            <td className="odds-value">—</td>
                            <td className="odds-value">—</td>
                            <td>
                                <span
                                    className={`badge ${m.status === "live" ? "badge-live" : "badge-finished"
                                        }`}
                                >
                                    {m.status === "live" ? "● LIVE" : m.status.toUpperCase()}
                                </span>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}
