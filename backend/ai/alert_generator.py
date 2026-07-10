import anthropic
from config import get_settings


async def generate_alert_explanation(zone: str, risk_data: dict, reading: dict) -> str:
    settings = get_settings()
    if not settings.ANTHROPIC_API_KEY:
        return _fallback_alert(zone, risk_data, reading)

    prompt = f"""You are an industrial safety AI system. Generate a concise, urgent safety alert.

Zone: {zone}
Compound Risk Score: {risk_data['compound_score']} ({risk_data['severity']})
Contributing Factors: {', '.join(risk_data['contributing_factors'])}

Current Readings:
- CO: {reading.get('co_ppm', 0)} ppm
- H2S: {reading.get('h2s_ppm', 0)} ppm
- Methane: {reading.get('methane_ppm', 0)} ppm
- Temperature: {reading.get('temperature', 0)}°C

Active Permit: {risk_data.get('active_permit', 'None')}

Generate a 3-4 sentence alert that:
1. States the danger clearly
2. Explains WHY this combination is dangerous (not just individual readings)
3. Gives a specific recommended action
Keep it under 150 words. Be direct and urgent."""

    try:
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text
    except Exception:
        return _fallback_alert(zone, risk_data, reading)


async def generate_incident_report(zone: str, risk_data: dict, reading: dict, alert_text: str) -> str:
    settings = get_settings()
    if not settings.ANTHROPIC_API_KEY:
        return f"# Incident Report\n\nZone: {zone}\nScore: {risk_data['compound_score']}\n\n{alert_text}"

    prompt = f"""Generate a formal industrial safety incident report.

Zone: {zone}
Timestamp: {reading.get('timestamp', 'N/A')}
Compound Risk Score: {risk_data['compound_score']} ({risk_data['severity']})
Factors: {', '.join(risk_data['contributing_factors'])}
CO: {reading.get('co_ppm')} ppm | H2S: {reading.get('h2s_ppm')} ppm | Methane: {reading.get('methane_ppm')} ppm
Permit: {risk_data.get('active_permit')}

Generate a structured incident report with sections:
1. Incident Summary
2. Risk Assessment
3. Contributing Factors Analysis
4. Recommended Actions (immediate + long-term)
5. Regulatory References (OISD/Factory Act)

Format in markdown. Keep under 500 words."""

    try:
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text
    except Exception:
        return f"# Incident Report\n\nZone: {zone}\nScore: {risk_data['compound_score']}\n\n{alert_text}"


def _fallback_alert(zone: str, risk_data: dict, reading: dict) -> str:
    permit = risk_data.get("active_permit")
    permit_str = f"Worker {permit['worker_name']} has an active {permit['work_type'].replace('_', ' ')} permit ({permit['permit_id']})." if permit else ""
    return (
        f"COMPOUND RISK DETECTED in {zone}. "
        f"CO at {reading.get('co_ppm', 0)} ppm, H2S at {reading.get('h2s_ppm', 0)} ppm. "
        f"{permit_str} "
        f"Combined risk score: {risk_data['compound_score']} ({risk_data['severity']}). "
        f"Recommend immediate work suspension and zone evacuation."
    )
