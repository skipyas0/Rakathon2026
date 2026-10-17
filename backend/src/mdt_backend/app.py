import base64
import secrets
from pathlib import Path

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles

from mdt_backend import fhir
from mdt_backend.config import settings
from mdt_backend.features import (
    cases,
    compliance,
    export,
    history,
    intake,
    recommendation,
    records,
    report,
    stanovisko,
)

app = FastAPI(title="MDT Copilot")


@app.middleware("http")
async def shared_password(request: Request, call_next):
    """ponytail: one shared password for the whole demo (APP_PASSWORD); per-user login when
    decisions must be attributable to authenticated clinicians."""
    if not settings.app_password or request.url.path == "/api/health":
        return await call_next(request)
    scheme, _, encoded = request.headers.get("authorization", "").partition(" ")
    try:
        password = base64.b64decode(encoded).decode().partition(":")[2]
    except ValueError:
        password = ""
    if scheme.lower() == "basic" and secrets.compare_digest(
        password.encode(), settings.app_password.encode()
    ):
        return await call_next(request)
    return Response(status_code=401, headers={"WWW-Authenticate": 'Basic realm="MDT Copilot"'})


# Features live in mdt_backend/features/<name>.py, each exposing `router`.
# Register them here; removing a feature = delete its file + its line below.
app.include_router(cases.router)
app.include_router(records.router)
app.include_router(intake.router)
app.include_router(history.router)
app.include_router(recommendation.router)
app.include_router(compliance.router)
app.include_router(export.router)
app.include_router(stanovisko.router)
app.include_router(report.router)


@app.get("/api/health")
def health() -> dict:
    """The app is up (200, for Fly's check: restarting the app wouldn't fix IRIS); `fhir` says
    whether IRIS answers an authenticated read."""
    try:
        fhir.get("Patient", _summary="count")
        return {"status": "ok", "fhir": True}
    except httpx.HTTPError:
        return {"status": "ok", "fhir": False}


@app.get("/api/patients")
def patients() -> dict:
    return fhir.get("Patient", _count=50)


# Built frontend (Docker image / `npm run build`); mounted last so /api routes win.
DIST = Path(__file__).parents[3] / "frontend" / "dist"
if DIST.is_dir():
    app.mount("/", StaticFiles(directory=DIST, html=True), name="frontend")
