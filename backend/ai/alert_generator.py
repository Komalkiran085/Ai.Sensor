import asyncio
import logging

import anthropic

from config import get_settings

logger = logging.getLogger(__name__)

CLAUDE_MODEL = "claude-sonnet-4-20250514"


def _readings_text(readings: list[dict]) -> str:
    return "\n".join(f"- {r['sensor_type']}: {r['value']}" for r in readings) or "- (no active readings)"


def _permit_text(risk_data: dict) -> str:
    permit = risk_data.get("agent_outputs", {}).get("permit", {}).get("active_permit")
    if not permit:
        return "None"
    return f"{permit['work_type'].replace('_', ' ')} permit {permit['permit_id']}"


def _citations_text(risk_data: dict) -> str:
    citations = risk_data.get("agent_outputs", {}).get("compliance", {}).get("citations") or []
    if not citations:
        return "None on file"
    return "; ".join(f"{c['clause_ref']}" for c in citations)


def _similar_incidents_text(risk_data: dict) -> str:
    matches = risk_data.get("agent_outputs", {}).get("incident", {}).get("matches") or []
    if not matches:
        return "No similar past incidents or near-misses on file"
    lines = []
    for m in matches:
        label = "Incident" if m["type"] == "incident" else "Near-miss"
        lines.append(f"{label} ({m.get('date', 'undated')}, {m['zone_id']}): {m['description']}")
    return "\n".join(lines)


# Neither call ever raises; a failure just means the caller falls back to the
# static template. ──────────────────────────────────────────────────────────────

async def _call_claude(prompt: str, max_tokens: int) -> str | None:
    settings = get_settings()
    if not settings.ANTHROPIC_API_KEY:
        return None
    try:
        def _sync_call():
            client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            response = client.messages.create(
                model=CLAUDE_MODEL, max_tokens=max_tokens, messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text
        return await asyncio.to_thread(_sync_call)
    except Exception:
        logger.exception("Claude generation failed")
        return None


async def _generate(prompt: str, max_tokens: int) -> str | None:
    return await _call_claude(prompt, max_tokens)


async def generate_alert_explanation(zone_name: str, risk_data: dict, readings: list[dict]) -> str:
    lead_time = risk_data.get("lead_time_minutes")
    lead_time_text = f"~{lead_time} min until next threshold at current trend" if lead_time is not None else "not currently trending toward a threshold"

    prompt = f"""You are an industrial safety AI system. Generate a concise, urgent safety alert.

Zone: {zone_name}
Compound Risk Score: {risk_data['compound_score']} ({risk_data['severity']})
Contributing Factors: {', '.join(risk_data['contributing_factors']) or 'none'}
Estimated lead time: {lead_time_text}

Current Readings:
{_readings_text(readings)}

Active Permit: {_permit_text(risk_data)}
Relevant regulations on file: {_citations_text(risk_data)}

Similar past incidents/near-misses:
{_similar_incidents_text(risk_data)}

Generate a 3-4 sentence alert that:
1. States the danger clearly
2. Explains WHY this combination is dangerous (not just individual readings)
3. Gives a specific recommended action
Keep it under 150 words. Be direct and urgent."""

    text = await _generate(prompt, max_tokens=300)
    return text if text is not None else immediate_alert_text(zone_name, risk_data, readings)


async def generate_incident_report(zone_name: str, risk_data: dict, readings: list[dict]) -> str:
    prompt = f"""Generate a formal industrial safety incident report.

Zone: {zone_name}
Compound Risk Score: {risk_data['compound_score']} ({risk_data['severity']})
Factors: {', '.join(risk_data['contributing_factors']) or 'none'}

Readings:
{_readings_text(readings)}

Permit: {_permit_text(risk_data)}
Relevant regulations on file: {_citations_text(risk_data)}

Similar past incidents/near-misses:
{_similar_incidents_text(risk_data)}

Generate a structured incident report with sections:
1. Incident Summary
2. Risk Assessment
3. Contributing Factors Analysis
4. Similar Past Incidents (what this situation has in common with the history above, if any)
5. Recommended Actions (immediate + long-term)
6. Regulatory References (cite the clause refs given above, if any)

Format in markdown. Keep under 500 words."""

    text = await _generate(prompt, max_tokens=800)
    return text if text is not None else immediate_incident_report(zone_name, risk_data, readings)


def immediate_incident_report(zone_name: str, risk_data: dict, readings: list[dict]) -> str:
    return f"# Incident Report\n\nZone: {zone_name}\nScore: {risk_data['compound_score']}\n\n{immediate_alert_text(zone_name, risk_data, readings)}"


def immediate_alert_text(zone_name: str, risk_data: dict, readings: list[dict]) -> str:
    permit = risk_data.get("agent_outputs", {}).get("permit", {}).get("active_permit")
    permit_str = (
        f"Active {permit['work_type'].replace('_', ' ')} permit {permit['permit_id']} is in effect. "
        if permit else ""
    )
    readings_str = ", ".join(f"{r['sensor_type']} {r['value']}" for r in readings)
    return (
        f"COMPOUND RISK DETECTED in {zone_name}. {readings_str}. "
        f"{permit_str}"
        f"Combined risk score: {risk_data['compound_score']} ({risk_data['severity']}). "
        f"Recommend immediate work suspension and zone evacuation."
    )
