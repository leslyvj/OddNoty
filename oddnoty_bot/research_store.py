import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class ResearchStore:
    def __init__(self, db_path: str = "research_data.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS matches (
                    match_id TEXT PRIMARY KEY,
                    home_team TEXT,
                    away_team TEXT,
                    start_time DATETIME,
                    sofascore_id TEXT,
                    onexbet_id TEXT,
                    last_updated DATETIME
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS research_reports (
                    match_id TEXT PRIMARY KEY,
                    report_text TEXT,
                    created_at DATETIME,
                    FOREIGN KEY(match_id) REFERENCES matches(match_id)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS raw_data (
                    match_id TEXT,
                    source TEXT,
                    data_json TEXT,
                    fetched_at DATETIME,
                    PRIMARY KEY(match_id, source)
                )
            """)
            conn.commit()

    def save_match(self, home: str, away: str, sofascore_id: str = None, onexbet_id: str = None):
        match_id = f"{home}_{away}".lower().replace(" ", "")
        now = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO matches (match_id, home_team, away_team, sofascore_id, onexbet_id, last_updated)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(match_id) DO UPDATE SET
                    sofascore_id=excluded.sofascore_id,
                    onexbet_id=excluded.onexbet_id,
                    last_updated=excluded.last_updated
            """, (match_id, home, away, sofascore_id, onexbet_id, now))
        return match_id

    def save_raw_data(self, match_id: str, source: str, data: Dict[str, Any]):
        now = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO raw_data (match_id, source, data_json, fetched_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(match_id, source) DO UPDATE SET
                    data_json=excluded.data_json,
                    fetched_at=excluded.fetched_at
            """, (match_id, source, json.dumps(data), now))

    def get_raw_data(self, match_id: str) -> Dict[str, Any]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT source, data_json FROM raw_data WHERE match_id = ?", (match_id,))
            return {row[0]: json.loads(row[1]) for row in cursor.fetchall()}

    def save_report(self, match_id: str, report: str):
        now = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO research_reports (match_id, report_text, created_at)
                VALUES (?, ?, ?)
                ON CONFLICT(match_id) DO UPDATE SET
                    report_text=excluded.report_text,
                    created_at=excluded.created_at
            """, (match_id, report, now))

    def get_report(self, match_id: str, max_age_hours: int = 24) -> Optional[str]:
        threshold = (datetime.now() - timedelta(hours=max_age_hours)).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT report_text FROM research_reports 
                WHERE match_id = ? AND created_at > ?
            """, (match_id, threshold))
            row = cursor.fetchone()
            return row[0] if row else None
    def get_match(self, match_id: str) -> Optional[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT home_team, away_team, sofascore_id, onexbet_id FROM matches WHERE match_id = ?", (match_id,))
            row = cursor.fetchone()
            if row:
                return {
                    "home_team": row[0],
                    "away_team": row[1],
                    "sofascore_id": row[2],
                    "onexbet_id": row[3]
                }
            return None
