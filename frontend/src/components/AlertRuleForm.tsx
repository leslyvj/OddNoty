"use client";

import { useState } from "react";

export default function AlertRuleForm() {
    const [name, setName] = useState("");
    const [market, setMarket] = useState("over");
    const [line, setLine] = useState("2.5");
    const [oddsGte, setOddsGte] = useState("");
    const [minuteGte, setMinuteGte] = useState("");
    const [score, setScore] = useState("");
    const [league, setLeague] = useState("");

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        // TODO: POST to /api/alerts/rules
        console.log("Creating rule:", {
            name,
            conditions: { market, line: parseFloat(line), odds_gte: parseFloat(oddsGte), minute_gte: parseInt(minuteGte), score, league },
        });
    };

    return (
        <form onSubmit={handleSubmit} className="card" style={{ display: "flex", flexDirection: "column", gap: "var(--space-md)" }}>
            <h3 style={{ fontSize: "1.1rem" }}>Create Alert Rule</h3>

            <input id="rule-name" className="filter-input" placeholder="Rule name" value={name} onChange={(e) => setName(e.target.value)} required />

            <div style={{ display: "flex", gap: "var(--space-md)", flexWrap: "wrap" }}>
                <select id="rule-market" className="filter-input" value={market} onChange={(e) => setMarket(e.target.value)}>
                    <option value="over">Over</option>
                    <option value="under">Under</option>
                </select>

                <select id="rule-line" className="filter-input" value={line} onChange={(e) => setLine(e.target.value)}>
                    <option value="0.5">0.5</option>
                    <option value="1.5">1.5</option>
                    <option value="2.5">2.5</option>
                    <option value="3.5">3.5</option>
                </select>

                <input id="rule-odds-gte" className="filter-input" type="number" step="0.01" placeholder="Odds ≥" value={oddsGte} onChange={(e) => setOddsGte(e.target.value)} />
                <input id="rule-minute-gte" className="filter-input" type="number" placeholder="Minute ≥" value={minuteGte} onChange={(e) => setMinuteGte(e.target.value)} />
                <input id="rule-score" className="filter-input" placeholder="Score (e.g. 0-0)" value={score} onChange={(e) => setScore(e.target.value)} />
                <input id="rule-league" className="filter-input" placeholder="League" value={league} onChange={(e) => setLeague(e.target.value)} />
            </div>

            <button type="submit" className="btn btn-primary" id="create-rule-btn">
                Create Rule
            </button>
        </form>
    );
}
