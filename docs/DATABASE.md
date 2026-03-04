# OddNoty — Database Schema

## Tables

### `matches`
| Column      | Type        | Description            |
|-------------|-------------|------------------------|
| match_id    | VARCHAR PK  | External match ID      |
| league      | VARCHAR     | League name            |
| home_team   | VARCHAR     | Home team name         |
| away_team   | VARCHAR     | Away team name         |
| home_score  | INTEGER     | Current home score     |
| away_score  | INTEGER     | Current away score     |
| match_minute| INTEGER     | Current match minute   |
| start_time  | TIMESTAMP   | Scheduled kick-off     |
| status      | VARCHAR     | not_started / live / finished |
| created_at  | TIMESTAMP   | Row creation time      |
| updated_at  | TIMESTAMP   | Last update time       |

### `odds`
| Column      | Type        | Description            |
|-------------|-------------|------------------------|
| id          | SERIAL PK   | Auto-increment ID      |
| match_id    | VARCHAR FK  | References matches     |
| market      | VARCHAR     | e.g. "over", "under"  |
| line        | DECIMAL     | 0.5, 1.5, 2.5, 3.5    |
| bookmaker   | VARCHAR     | Bookmaker name         |
| odds        | DECIMAL     | Current odds value     |
| timestamp   | TIMESTAMP   | Snapshot time          |

### `alerts`
| Column       | Type        | Description           |
|--------------|-------------|-----------------------|
| alert_id     | SERIAL PK   | Auto-increment ID     |
| user_id      | INTEGER FK  | References users      |
| match_id     | VARCHAR FK  | References matches    |
| market       | VARCHAR     | Market that triggered  |
| condition    | JSONB       | Rule conditions JSON   |
| triggered_at | TIMESTAMP   | When alert fired       |

### `users`
| Column       | Type        | Description           |
|--------------|-------------|-----------------------|
| user_id      | SERIAL PK   | Auto-increment ID     |
| email        | VARCHAR     | User email            |
| telegram_id  | VARCHAR     | Telegram chat ID      |
| created_at   | TIMESTAMP   | Registration time     |

### `alert_rules`
| Column       | Type        | Description           |
|--------------|-------------|-----------------------|
| rule_id      | SERIAL PK   | Auto-increment ID     |
| user_id      | INTEGER FK  | References users      |
| name         | VARCHAR     | Rule display name     |
| conditions   | JSONB       | Rule conditions       |
| is_active    | BOOLEAN     | Enabled / disabled    |
| created_at   | TIMESTAMP   | Creation time         |

## Indexes
- `odds(match_id, timestamp)` — fast lookup of latest odds per match
- `alerts(user_id, triggered_at)` — user alert history
- `matches(status)` — filter live matches
