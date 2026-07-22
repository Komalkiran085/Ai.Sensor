"""Real phone call for extreme-severity alerts, via Twilio Programmable Voice — a
webhook can sit unread in a channel nobody's watching, a phone ringing can't. Placed
directly against Twilio's REST API (no SDK dependency, matching webhook.py's httpx
pattern) with the spoken message passed inline as TwiML, so no publicly reachable
callback URL is needed. If Twilio isn't configured, this just logs and skips — same
degrade-gracefully behavior as the webhook notifier.
"""
from __future__ import annotations
import logging
from xml.sax.saxutils import escape

import httpx

from config import get_settings

logger = logging.getLogger(__name__)

TWILIO_CALLS_URL = "https://api.twilio.com/2010-04-01/Accounts/{sid}/Calls.json"


def _twiml(message: str) -> str:
    said = escape(message)
    # Said twice with a pause between — a phone call has no "scroll back up" like a
    # dashboard or chat message does, so the listener gets one chance to catch it live.
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        f'<Say voice="Polly.Joanna">{said}</Say>'
        '<Pause length="1"/>'
        f'<Say voice="Polly.Joanna">Repeating. {said}</Say>'
        "</Response>"
    )


async def send_alert_call(zone_name: str, severity: str, explanation: str, compound_score: float) -> bool:
    settings = get_settings()
    if not (settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN
            and settings.TWILIO_FROM_NUMBER and settings.ALERT_PHONE_NUMBER):
        logger.info("Twilio not fully configured — skipping alert call for %s", zone_name)
        return False

    message = (
        f"Extreme safety alert in {zone_name}. Compound risk score "
        f"{round(compound_score * 100)} percent. {explanation}"
    )

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                TWILIO_CALLS_URL.format(sid=settings.TWILIO_ACCOUNT_SID),
                auth=(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN),
                data={
                    "To": settings.ALERT_PHONE_NUMBER,
                    "From": settings.TWILIO_FROM_NUMBER,
                    "Twiml": _twiml(message),
                },
            )
            response.raise_for_status()
        logger.info("Alert call placed for %s (%s)", zone_name, severity)
        return True
    except Exception:
        logger.exception("Failed to place alert call for %s", zone_name)
        return False
