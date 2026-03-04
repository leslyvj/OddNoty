"use client";

import MatchTable from "@/components/MatchTable";
import Filters from "@/components/Filters";

export default function DashboardPage() {
    return (
        <>
            <div className="page-header">
                <h1>⚽ Live Matches</h1>
                <p>Real-time Over/Under goal odds monitoring</p>
            </div>

            <Filters />
            <MatchTable />
        </>
    );
}
