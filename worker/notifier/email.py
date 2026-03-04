"""Email alert notifier (optional)."""

import logging

logger = logging.getLogger("oddnoty.notifier.email")


class EmailNotifier:
    """Send alert notifications via email (SMTP)."""

    def __init__(self, smtp_host: str, smtp_port: int, username: str, password: str):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password

    async def send(self, alert: dict, to_email: str) -> bool:
        """Send an alert email."""
        # TODO: implement with aiosmtplib
        logger.info(f"Email alert to {to_email}: {alert}")
        return True
