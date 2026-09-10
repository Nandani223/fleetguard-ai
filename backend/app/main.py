from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.parts import router as parts_router
from app.api.predictions import router as predictions_router
from app.api.rul import router as rul_router
from app.api.agent import router as agent_router
from app.api.auth import router as auth_router
from app.api.vehicles import router as vehicles_router
from app.api.maintenance import router as maintenance_router

app = FastAPI(
    title="FleetGuard AI",
    description="Predictive maintenance backend: correlation engine, "
                 "rule builder, failure scoring, RUL estimation, and the "
                 "Insight/Action agents.",
    version="0.1.0",
)

# Wide-open CORS for local dev; tighten before any real deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(parts_router)
app.include_router(predictions_router)
app.include_router(rul_router)
app.include_router(agent_router)
app.include_router(auth_router)
app.include_router(vehicles_router)
app.include_router(maintenance_router)

from pathlib import Path
from fastapi.staticfiles import StaticFiles

frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")

@app.get("/health")
def health():
    return {"status": "ok"}
