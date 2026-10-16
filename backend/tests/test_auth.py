from fastapi.testclient import TestClient

from mdt_backend.app import app
from mdt_backend.config import settings


def test_shared_password(monkeypatch):
    c = TestClient(app)
    assert c.get("/api/cases").status_code == 200  # no password set = open (local dev)
    monkeypatch.setattr(settings, "app_password", "tajne")
    assert c.get("/api/cases").status_code == 401
    assert c.get("/api/cases", auth=("x", "spatne")).status_code == 401
    assert c.get("/api/cases", headers={"Authorization": "Basic %%%"}).status_code == 401
    assert c.get("/api/cases", auth=("kdokoli", "tajne")).status_code == 200
    assert c.get("/api/health").status_code == 200  # Fly health checks need no password
