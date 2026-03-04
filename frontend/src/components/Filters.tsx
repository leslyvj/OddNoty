"use client";

export default function Filters() {
    return (
        <div className="filters">
            <input
                id="filter-league"
                className="filter-input"
                type="text"
                placeholder="Filter by league..."
            />
            <input
                id="filter-odds-min"
                className="filter-input"
                type="number"
                step="0.1"
                placeholder="Min odds"
            />
            <input
                id="filter-minute-min"
                className="filter-input"
                type="number"
                placeholder="Min minute"
            />
            <input
                id="filter-minute-max"
                className="filter-input"
                type="number"
                placeholder="Max minute"
            />
        </div>
    );
}
