"""
Insight Agent tools (Day 6 — brief section 4.5).

"a conversational agent with tool-calling access to the backend APIs...
It must answer only from live backend data — no invented numbers."

Design choice: tools call the SAME SERVICE FUNCTIONS the FastAPI endpoints
call (app.services.*), not HTTP requests to the backend's own API. This
guarantees the agent can never see numbers that differ from what the
dashboard shows — there's only one source of truth (the service layer),
and both the REST API and the agent are thin wrappers around it.

Tool schema note: these are defined in the OpenAI/Groq function-calling
format ({"type": "function", "function": {...}}), since Groq's API is
OpenAI-compatible — not Anthropic's flat {"name", "input_schema"} shape.
"""
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.core import Vehicle, Part
from app.models.failure import Failure
from app.models.rules import Prediction
from app.services.correlation import compute_correlations, InsufficientDataError
from app.services.scoring import score_single_vehicle, SIM_AS_OF_DATE
from app.services.rul import estimate_rul

DEFAULT_METHOD = "point_biserial"


def _tool(name: str, description: str, parameters: dict) -> dict:
    """Wraps a tool definition in the OpenAI/Groq function-calling schema
    (Groq's API is OpenAI-compatible, not Anthropic's — this is the
    {"type": "function", "function": {...}} shape, not Anthropic's flat
    {"name", "input_schema"} shape)."""
    return {
        "type": "function",
        "function": {"name": name, "description": description, "parameters": parameters},
    }


TOOL_DEFINITIONS = [
    _tool(
        "list_parts",
        "List all parts tracked in the fleet (code, name, category, design life in km).",
        {"type": "object", "properties": {}},
    ),
    _tool(
        "get_correlation",
        "Get per-telematics-signal correlation with failure for a given part "
        "(point-biserial r and XGBoost importance). Use this to answer "
        "'why' or 'which signals matter' questions about a part.",
        {
            "type": "object",
            "properties": {"part_code": {"type": "string", "description": "e.g. 'ELC-0152'"}},
            "required": ["part_code"],
        },
    ),
    _tool(
        "get_predictions",
        "List the fleet's most recent failure-probability predictions for a part, "
        "optionally filtered by risk tier. Ranked highest risk first. Use this "
        "for 'which vehicles are at risk' / 'which are red-tier' questions.",
        {
            "type": "object",
            "properties": {
                "part_code": {"type": "string"},
                "risk_tier": {"type": "string", "enum": ["Green", "Amber", "Red"]},
                "limit": {"type": "integer", "default": 10},
            },
            "required": ["part_code"],
        },
    ),
    _tool(
        "get_prediction_detail",
        "Get the live failure probability, risk tier, top contributing signals, "
        "and a 6-week trend for one specific vehicle+part. Use this for "
        "'why is this VIN at X%' questions.",
        {
            "type": "object",
            "properties": {"vin": {"type": "string"}, "part_code": {"type": "string"}},
            "required": ["vin", "part_code"],
        },
    ),
    _tool(
        "get_rul",
        "Get remaining useful life (km and days) for one vehicle+part, cross-checked "
        "against its failure probability. Use this for 'how much life is left' / "
        "'when should this be serviced' questions.",
        {
            "type": "object",
            "properties": {"vin": {"type": "string"}, "part_code": {"type": "string"}},
            "required": ["vin", "part_code"],
        },
    ),
    _tool(
        "compare_parts",
        "Compare two or more parts on historical failure rate and, where "
        "available, current live risk distribution. Use this for "
        "'compare durability of Part A vs Part B' questions.",
        {
            "type": "object",
            "properties": {
                "part_codes": {"type": "array", "items": {"type": "string"}, "minItems": 2},
            },
            "required": ["part_codes"],
        },
    ),
    _tool(
        "find_vehicle",
        "Look up a vehicle by a full or partial VIN (handles loosely-phrased "
        "references like 'truck 4521' or the last few characters of a VIN). "
        "Returns matching vehicles with model/region/odometer. Use this before "
        "get_prediction_detail or get_rul if the user didn't give an exact VIN.",
        {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "full or partial VIN"}},
            "required": ["query"],
        },
    ),
]


def _list_parts(db: Session, args: dict) -> dict:
    parts = db.query(Part).all()
    return {
        "parts": [
            {"part_code": p.part_code, "part_name": p.part_name,
             "category": p.category, "design_life_km": p.design_life_km}
            for p in parts
        ]
    }


def _get_correlation(db: Session, args: dict) -> dict:
    part_code = args["part_code"]
    part = db.query(Part).filter(Part.part_code == part_code).first()
    if part is None:
        return {"error": f"Unknown part_code: {part_code}"}
    try:
        results, meta = compute_correlations(db, part_code)
    except InsufficientDataError as e:
        return {"error": str(e)}
    return {
        "part_code": part_code, "part_name": part.part_name, **meta,
        "signals": [
            {"signal": r.signal, "point_biserial_r": r.point_biserial_r,
             "xgboost_importance": r.xgboost_importance}
            for r in results
        ],
    }


def _get_predictions(db: Session, args: dict) -> dict:
    part_code = args["part_code"]
    risk_tier = args.get("risk_tier")
    limit = args.get("limit", 10)

    query = db.query(Prediction).filter(
        Prediction.part_code == part_code, Prediction.computed_date == SIM_AS_OF_DATE
    )
    if risk_tier:
        query = query.filter(Prediction.risk_tier == risk_tier)

    tier_order = {"Red": 0, "Amber": 1, "Green": 2}
    rows = query.all()
    if not rows:
        return {"error": f"No predictions found for {part_code}. "
                          f"The scoring engine may not have been run yet for this part."}
    rows.sort(key=lambda p: (tier_order.get(p.risk_tier, 3), -p.failure_probability))
    rows = rows[:limit]

    return {
        "part_code": part_code, "computed_date": str(SIM_AS_OF_DATE), "n_matching": len(rows),
        "predictions": [
            {"vin": r.vin, "failure_probability": r.failure_probability,
             "risk_tier": r.risk_tier, "top_signals": r.top_signals,
             "estimated_window_days": r.estimated_window_days}
            for r in rows
        ],
    }


def _get_prediction_detail(db: Session, args: dict) -> dict:
    vin, part_code = args["vin"], args["part_code"]
    if db.query(Vehicle).filter(Vehicle.vin == vin).first() is None:
        return {"error": f"Unknown VIN: {vin}"}
    if db.query(Part).filter(Part.part_code == part_code).first() is None:
        return {"error": f"Unknown part_code: {part_code}"}
    try:
        return score_single_vehicle(db, vin, part_code, DEFAULT_METHOD)
    except ValueError as e:
        return {"error": str(e)}


def _get_rul(db: Session, args: dict) -> dict:
    vin, part_code = args["vin"], args["part_code"]
    try:
        return estimate_rul(db, vin, part_code, DEFAULT_METHOD)
    except ValueError as e:
        return {"error": str(e)}


def _compare_parts(db: Session, args: dict) -> dict:
    part_codes = args["part_codes"]
    n_vehicles = db.query(Vehicle).count()
    comparison = []
    for code in part_codes:
        part = db.query(Part).filter(Part.part_code == code).first()
        if part is None:
            comparison.append({"part_code": code, "error": "unknown part_code"})
            continue
        n_failed = db.query(Failure).filter(Failure.part_code == code).count()
        entry = {
            "part_code": code, "part_name": part.part_name,
            "design_life_km": part.design_life_km,
            "historical_failure_rate": round(n_failed / n_vehicles, 4) if n_vehicles else None,
            "n_failed_of": f"{n_failed}/{n_vehicles}",
        }
        preds = db.query(Prediction).filter(
            Prediction.part_code == code, Prediction.computed_date == SIM_AS_OF_DATE
        ).all()
        if preds:
            tier_counts = {"Green": 0, "Amber": 0, "Red": 0}
            for p in preds:
                tier_counts[p.risk_tier] += 1
            entry["current_avg_failure_probability"] = round(
                sum(p.failure_probability for p in preds) / len(preds), 4
            )
            entry["current_tier_counts"] = tier_counts
        comparison.append(entry)
    return {"comparison": comparison}


def _find_vehicle(db: Session, args: dict) -> dict:
    query = args["query"].strip().upper()
    matches = db.query(Vehicle).filter(Vehicle.vin.like(f"%{query}%")).limit(10).all()
    if not matches:
        return {"error": f"No vehicles found matching '{query}'"}
    return {
        "matches": [
            {"vin": v.vin, "model": v.model, "region": v.region,
             "total_km_driven": v.total_km_driven}
            for v in matches
        ]
    }


TOOL_EXECUTORS = {
    "list_parts": _list_parts,
    "get_correlation": _get_correlation,
    "get_predictions": _get_predictions,
    "get_prediction_detail": _get_prediction_detail,
    "get_rul": _get_rul,
    "compare_parts": _compare_parts,
    "find_vehicle": _find_vehicle,
}


def execute_tool(tool_name: str, tool_input: dict) -> dict:
    """Opens its own short-lived DB session per tool call — simplest way
    to keep tool execution stateless and safe to call repeatedly within
    one agent turn (an agent turn may call several tools before replying)."""
    executor = TOOL_EXECUTORS.get(tool_name)
    if executor is None:
        return {"error": f"Unknown tool: {tool_name}"}
    db = SessionLocal()
    try:
        return executor(db, tool_input)
    finally:
        db.close()
