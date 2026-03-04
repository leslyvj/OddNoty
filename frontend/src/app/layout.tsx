import "@/styles/globals.css";
import type { Metadata } from "next";
import Navbar from "@/components/Navbar";

export const metadata: Metadata = {
    title: "OddNoty — Over/Under Goal Odds Alerts",
    description:
        "Real-time Over/Under goal odds monitoring and alerts for football matches.",
};

export default function RootLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <html lang="en">
            <body>
                <Navbar />
                <main className="container">{children}</main>
            </body>
        </html>
    );
}
