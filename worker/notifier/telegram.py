"""Telegram alert notifier."""

import aiohttp
import logging

logger = logging.getLogger("oddnoty.notifier.telegram")

TELEGRAM_API = "https://api.telegram.org"


class TelegramNotifier:
    """Send alert notifications via Telegram Bot API."""

    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id

    async def send(self, alert: dict) -> bool:
        """Send an alert message to Telegram."""
        message = self._format_message(alert)
        url = f"{TELEGRAM_API}/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "HTML",
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                if resp.status == 200:
                    logger.info(f"Telegram alert sent: {alert.get('home_team')} vs {alert.get('away_team')}")
                    return True
                else:
                    logger.error(f"Telegram send failed: {resp.status}")
                    return False

    def _format_message(self, alert: dict) -> str:
        """Format alert data into a readable Telegram message."""
        return (
            f"🚨 <b>OddNoty Alert</b>\n\n"
            f"⚽ <b>{alert.get('home_team')} vs {alert.get('away_team')}</b>\n"
            f"⏱ Minute: {alert.get('match_minute')}\n"
            f"📊 Score: {alert.get('score')}\n\n"
            f"📈 {alert.get('market', 'Over').title()} {alert.get('line')} Odds triggered\n"
            f"📝 Rule: {alert.get('rule_name', 'N/A')}"
        )
