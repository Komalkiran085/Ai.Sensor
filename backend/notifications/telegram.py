"""Real-time text alert via the Telegram Bot API — a free, no-trial-credit alternative
to SMS. Delivers to a Telegram chat on the on-call officer's phone rather than their
actual SMS inbox, but arrives the same way: an instant push notification. If not
configured, this just logs and skips — same degrade-gracefully pattern as the webhook
and Twilio call notifiers.
"""
from __future__ import annotations
import logging

import httpx

from config import get_settings

logger = logging.getLogger(__name__)

TELEGRAM_SEND_MESSAGE_URL = "https://api.telegram.org/bot{token}/sendMessage"


async def send_telegram_alert(zone_name: str, severity: str, explanation: str, compound_score: float) -> bool:
    settings = get_settings()
    if not (settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID):
        logger.info("Telegram not configured — skipping alert message for %s", zone_name)
        return False

    text = f"🚨 [{severity.upper()}] {zone_name} — compound risk {compound_score * 100:.0f}%\n{explanation}"

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                TELEGRAM_SEND_MESSAGE_URL.format(token=settings.TELEGRAM_BOT_TOKEN),
                json={"chat_id": settings.TELEGRAM_CHAT_ID, "text": text},
            )
            response.raise_for_status()
        logger.info("Telegram alert sent for %s (%s)", zone_name, severity)
        return True
    except Exception:
        logger.exception("Failed to send Telegram alert for %s", zone_name)
        return False
