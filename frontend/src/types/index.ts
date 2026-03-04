/**
 * Shared TypeScript types for OddNoty frontend.
 */

export interface Match {
    match_id: string;
    league: string;
    home_team: string;
    away_team: string;
    home_score: number;
    away_score: number;
    match_minute: number;
    status: "not_started" | "live" | "finished";
    start_time?: string;
}

export interface OddsEntry {
    id: number;
    match_id: string;
    market: "over" | "under";
    line: number;
    bookmaker: string;
    odds: number;
    timestamp: string;
}

export interface AlertRule {
    rule_id: number;
    user_id: number;
    name: string;
    conditions: AlertRuleConditions;
    is_active: boolean;
    created_at: string;
}

export interface AlertRuleConditions {
    market: string;
    line: number;
    odds_gte?: number;
    odds_lte?: number;
    minute_gte?: number;
    minute_lte?: number;
    score?: string;
    league?: string;
}

export interface Alert {
    alert_id: number;
    user_id: number;
    match_id: string;
    market: string;
    condition: Record<string, unknown>;
    triggered_at: string;
}
