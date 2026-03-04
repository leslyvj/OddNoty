"""Betfair Exchange fetcher (stub).

Odds pillar provider — fetches O/U goals odds from Betfair Exchange.
Uses the Delayed App Key (free, no deposit required).

Requires: betfairlightweight (pip install betfairlightweight)
This is a stub — full implementation needs real Betfair credentials
and the betfairlightweight library.

Only requests these 4 market types:
  - OVER_UNDER_05
  - OVER_UNDER_15
  - OVER_UNDER_25
  - OVER_UNDER_35
"""

import logging
from typing import Optional

logger = logging.getLogger("oddnoty.fetcher.betfair")

# Betfair O/U goals market types — Soccer eventTypeId=1
BETFAIR_OU_MARKETS = [
    "OVER_UNDER_05",
    "OVER_UNDER_15",
    "OVER_UNDER_25",
    "OVER_UNDER_35",
]

OU_LABEL_MAP = {
    "OVER_UNDER_05": "ou_05",
    "OVER_UNDER_15": "ou_15",
    "OVER_UNDER_25": "ou_25",
    "OVER_UNDER_35": "ou_35",
}


class BetfairFetcher:
    """Fetch Over/Under goals odds from Betfair Exchange.

    This is a stub implementation. To use:
    1. pip install betfairlightweight
    2. Set real credentials in goaledge_keys.yaml
    3. Implement the login and API calls below
    """

    def __init__(
        self,
        app_key: str,
        username: str = "",
        password: str = "",
        certs_path: Optional[str] = None,
    ):
        self.app_key = app_key
        self.username = username
        self.password = password
        self.certs_path = certs_path
        self._client = None

    def _get_client(self):
        """Lazy-initialize the betfairlightweight client."""
        if self._client is not None:
            return self._client

        try:
            import betfairlightweight
            self._client = betfairlightweight.APIClient(
                username=self.username,
                password=self.password,
                app_key=self.app_key,
                certs=self.certs_path,
            )
            self._client.login()
            logger.info("Betfair login successful")
            return self._client
        except ImportError:
            logger.error(
                "betfairlightweight not installed — "
                "pip install betfairlightweight"
            )
            return None
        except Exception as e:
            logger.error(f"Betfair login failed: {e}")
            return None

    async def fetch_ou_odds(self, home_team: str, away_team: str) -> dict:
        """Fetch Over/Under goals odds for a specific match.

        Returns dict like:
        {
            "ou_05": {"over": 1.08, "under": 8.0},
            "ou_15": {"over": 1.35, "under": 3.4},
            "ou_25": {"over": 1.90, "under": 1.95},
            "ou_35": {"over": 3.20, "under": 1.35},
        }

        Returns empty dict if client unavailable or no markets found.
        """
        client = self._get_client()
        if not client:
            return {}

        try:
            from betfairlightweight.filters import market_filter

            event_filter = market_filter(
                event_type_ids=["1"],             # Soccer only
                in_play_only=True,
                market_types=BETFAIR_OU_MARKETS,  # O/U 0.5–3.5 ONLY
                text_query=f"{home_team} v {away_team}",
            )
            markets = client.betting.list_market_catalogue(
                filter=event_filter,
                max_results=20,
                market_projection=["RUNNER_DESCRIPTION"],
            )

            result = {}
            for mkt in markets:
                label = OU_LABEL_MAP.get(mkt.market_type)
                if not label:
                    continue  # skip anything not in our 4 O/U markets

                book = client.betting.list_market_book(
                    market_ids=[mkt.market_id],
                    price_projection={"priceData": ["EX_BEST_OFFERS"]},
                )
                if book and len(book[0].runners) >= 2:
                    over_runner = book[0].runners[0]
                    under_runner = book[0].runners[1]
                    best_back_over = over_runner.ex.available_to_back
                    best_back_under = under_runner.ex.available_to_back
                    result[label] = {
                        "over": best_back_over[0].price if best_back_over else None,
                        "under": best_back_under[0].price if best_back_under else None,
                    }

            return result

        except Exception as e:
            logger.error(f"Betfair fetch error: {e}")
            return {}

    async def fetch_all_live_ou_odds(self) -> dict:
        """Fetch O/U odds for all live soccer matches.

        Returns dict keyed by "HomeTeam vs AwayTeam" → ou_lines dict.
        """
        client = self._get_client()
        if not client:
            return {}

        try:
            from betfairlightweight.filters import market_filter

            event_filter = market_filter(
                event_type_ids=["1"],
                in_play_only=True,
                market_types=BETFAIR_OU_MARKETS,
            )
            markets = client.betting.list_market_catalogue(
                filter=event_filter,
                max_results=100,
                market_projection=["RUNNER_DESCRIPTION", "EVENT"],
            )

            # Group markets by event
            events: dict[str, list] = {}
            for mkt in markets:
                event_name = mkt.event.name if mkt.event else "Unknown"
                events.setdefault(event_name, []).append(mkt)

            result = {}
            for event_name, mkts in events.items():
                ou_lines = {}
                for mkt in mkts:
                    label = OU_LABEL_MAP.get(mkt.market_type)
                    if not label:
                        continue
                    book = client.betting.list_market_book(
                        market_ids=[mkt.market_id],
                        price_projection={"priceData": ["EX_BEST_OFFERS"]},
                    )
                    if book and len(book[0].runners) >= 2:
                        over_runner = book[0].runners[0]
                        under_runner = book[0].runners[1]
                        best_over = over_runner.ex.available_to_back
                        best_under = under_runner.ex.available_to_back
                        ou_lines[label] = {
                            "over": best_over[0].price if best_over else None,
                            "under": best_under[0].price if best_under else None,
                        }
                if ou_lines:
                    result[event_name] = ou_lines

            return result

        except Exception as e:
            logger.error(f"Betfair bulk fetch error: {e}")
            return {}

    def close(self):
        """Logout from Betfair."""
        if self._client:
            try:
                self._client.logout()
                logger.info("Betfair logout successful")
            except Exception:
                pass
            self._client = None
