"use client";

import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
} from "recharts";

interface OddsChartProps {
    matchId: string;
}

// Placeholder data — replace with API fetch
const PLACEHOLDER_DATA = [
    { time: "0'", over15: 1.4, over25: 2.1, over35: 3.5 },
    { time: "15'", over15: 1.38, over25: 2.05, over35: 3.4 },
    { time: "30'", over15: 1.5, over25: 2.2, over35: 3.6 },
    { time: "45'", over15: 1.65, over25: 2.4, over35: 3.9 },
    { time: "60'", over15: 1.85, over25: 2.7, over35: 4.5 },
    { time: "75'", over15: 2.1, over25: 3.2, over35: 5.5 },
];

export default function OddsChart({ matchId }: OddsChartProps) {
    return (
        <ResponsiveContainer width="100%" height={300}>
            <LineChart data={PLACEHOLDER_DATA}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="time" stroke="#64748b" fontSize={12} />
                <YAxis stroke="#64748b" fontSize={12} />
                <Tooltip
                    contentStyle={{
                        background: "#1a2236",
                        border: "1px solid #334155",
                        borderRadius: "8px",
                        color: "#f1f5f9",
                    }}
                />
                <Line
                    type="monotone"
                    dataKey="over15"
                    stroke="#22c55e"
                    strokeWidth={2}
                    dot={false}
                    name="Over 1.5"
                />
                <Line
                    type="monotone"
                    dataKey="over25"
                    stroke="#3b82f6"
                    strokeWidth={2}
                    dot={false}
                    name="Over 2.5"
                />
                <Line
                    type="monotone"
                    dataKey="over35"
                    stroke="#f59e0b"
                    strokeWidth={2}
                    dot={false}
                    name="Over 3.5"
                />
            </LineChart>
        </ResponsiveContainer>
    );
}
