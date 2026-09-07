"""
Action Agent (Day 6, optional stretch — brief section 4.5).

"given a flagged VIN, drafts a short outreach message recommending service
timing to the dealer/fleet owner — practising prompt design and message
generation, without sending anything automatically."

Design: unlike the Insight Agent, this doesn't need a tool-calling loop —
it deterministically fetches the grounding data first (get_prediction_detail
+ get_rul, same tools, same functions, same source of truth), then makes
ONE model call whose only job is turning that already-verified data into
a well-written message. This is simpler and more reliable than letting the
model decide whether/when to call tools for a task that always needs the
exact same two lookups. Nothing is sent anywhere — this returns a draft
string only.
"""
from groq import Groq, APIStatusError

from app.core.config import settings
from app.agent.tools import execute_tool

SYSTEM_PROMPT = """You draft short, professional service-outreach messages for a fleet \
maintenance team to send to a dealer or fleet owner about a specific vehicle \
part flagged by FleetGuard AI's predictive maintenance system.

You will be given the vehicle's live failure probability, risk tier, top \
contributing signals, and remaining useful life (RUL) in km/days. Use ONLY \
the data given to you — do not invent additional figures.

Adapt tone and urgency to the risk tier:
- Red: urgent, recommend scheduling service within days, be direct about risk.
- Amber: advisory, recommend scheduling service in the coming weeks.
- Green: informational only, no urgency — usually you won't be asked to \
draft one of these, but if asked, keep it low-key.

Keep it short (under 120 words), professional, and specific to the vehicle/part/RUL — \
not a generic template. Sign off as "FleetGuard AI Maintenance Team". Do not \
include placeholder brackets like [Name] — write it as ready to send."""


def draft_outreach_message(vin: str, part_code: str) -> dict:
    detail = execute_tool("get_prediction_detail", {"vin": vin, "part_code": part_code})
    if "error" in detail:
        return {"error": detail["error"], "draft": None}

    rul = execute_tool("get_rul", {"vin": vin, "part_code": part_code})
    if "error" in rul:
        return {"error": rul["error"], "draft": None}

    if not settings.groq_api_key:
        return {
            "error": "GROQ_API_KEY is missing from .env — the Action Agent needs it to draft messages.",
            "draft": None,
            "grounding_data": {"prediction": detail, "rul": rul},
        }

    grounding = (
        f"Vehicle: {vin}\n"
        f"Part: {part_code}\n"
        f"Failure probability: {detail['failure_probability']*100:.1f}%\n"
        f"Risk tier: {detail['risk_tier']}\n"
        f"Top contributing signals: {', '.join(detail['top_signals'])}\n"
        f"Remaining useful life: {rul['rul_km']} km / {rul['rul_days']} days\n"
    )

    client = Groq(api_key=settings.groq_api_key)
    try:
        response = client.chat.completions.create(
            model=settings.groq_model,
            max_tokens=400,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Draft the outreach message.\n\n{grounding}"},
            ],
        )
    except APIStatusError as e:
        return {"error": f"API error ({e.status_code}): {e.message}", "draft": None}

    draft_text = response.choices[0].message.content or ""
    return {
        "error": None,
        "draft": draft_text,
        "grounding_data": {"prediction": detail, "rul": rul},
    }
