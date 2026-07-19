"""Real multi-channel alerting, minus the "multi": a single generic webhook that
reaches whatever the plant actually points it at — Slack, Discord, MS Teams, or any
custom endpoint all accept an incoming webhook POST. No new paid API, no provider
lock-in; if ALERT_WEBHOOK_URL isn't set, this just logs and skips, so it degrades to
exactly today's behavior (dashboard + browser beep) rather than failing.
"""
from __future__ import annotations
import logging

import httpx

from config import get_settings

logger = logging.getLogger(__name__)


async def send_alert_notification(zone_name: str, severity: str, explanation: str, compound_score: float) -> bool:
    settings = get_settings()
    if not settings.ALERT_WEBHOOK_URL:
        logger.info("ALERT_WEBHOOK_URL not configured — skipping external notification for %s", zone_name)
        return False

    message = f"[{severity.upper()}] {zone_name} — compound risk {compound_score * 100:.0f}%\n{explanation}"
    payload = {
        # Slack-compatible
        "text": message,
        # Discord-compatible
        "content": message,
        # Structured fields for a custom receiver
        "zone": zone_name,
        "severity": severity,
        "compound_score": compound_score,
        "explanation": explanation,
    }

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(settings.ALERT_WEBHOOK_URL, json=payload)
            response.raise_for_status()
        logger.info("Alert notification sent for %s (%s)", zone_name, severity)
        return True
    except Exception:
        logger.exception("Failed to send alert notification for %s", zone_name)
        return False
