from fastapi import FastAPI

from mdt_backend import fhir
from mdt_backend.features import cases

app = FastAPI(title="MDT Copilot")

# Features live in mdt_backend/features/<name>.py, each exposing `router`.
# Register them here; removing a feature = delete its file + its line below.
app.include_router(cases.router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/patients")
def patients() -> dict:
    return fhir.get("Patient", _count=50)
