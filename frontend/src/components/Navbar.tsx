"use client";

import Link from "next/link";

export default function Navbar() {
    return (
        <nav className="navbar">
            <div className="navbar-brand">
                <span className="emoji">🚨</span> OddNoty
            </div>
            <ul className="navbar-links">
                <li>
                    <Link href="/" className="active">
                        Dashboard
                    </Link>
                </li>
                <li>
                    <Link href="/alerts">Alerts</Link>
                </li>
            </ul>
        </nav>
    );
}
