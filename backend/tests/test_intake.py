"""Intake of a FHIR bundle into the FHIR server. The round trip needs the dataset (not in git) and
is skipped without it. PDFs are not processed yet (501)."""

import base64
import json

import httpx
import pytest
from conftest import BUNDLES
from fastapi.testclient import TestClient

from mdt_backend import load_fhir
from mdt_backend.app import app

OK = httpx.Request("POST", "http://fhir")


@pytest.fixture
def client(monkeypatch):
    sent = []
    monkeypatch.setattr(
        load_fhir, "put", lambda tx: sent.append(tx) or httpx.Response(200, request=OK)
    )
    client = TestClient(app)
    client.sent = sent
    return client


def b64(data: bytes) -> str:
    return base64.b64encode(data).decode()


def test_rejects_what_is_not_a_bundle(client):
    for kind, data in (("fhir", b"{}"), ("fhir", b"not json")):
        r = client.post(
            "/api/intake", json={"kind": kind, "files": [{"name": "x", "data": b64(data)}]}
        )
        assert r.status_code == 422, (kind, data)
    assert client.post("/api/intake", json={"kind": "fhir", "files": []}).status_code == 422
    pdf = {"kind": "pdf", "files": [{"name": "x.pdf", "data": b64(b"%PDF")}]}
    assert client.post("/api/intake", json=pdf).status_code == 501


def upload(client, bundle: dict):
    data = b64(json.dumps(bundle).encode())
    return client.post(
        "/api/intake", json={"kind": "fhir", "files": [{"name": "P.json", "data": data}]}
    )


@pytest.mark.skipif("p03" not in BUNDLES, reason="no dataset")
def test_fhir_upload_becomes_a_case(client, fake_fhir):
    r = upload(client, BUNDLES["p03"])
    assert r.status_code == 200
    case_id = r.json()["case_id"]
    assert case_id == "p03-2026-10-21"
    assert client.sent[0]["type"] == "transaction"  # loaded into the FHIR server for the agent
    assert client.get(f"/api/cases/{case_id}").status_code == 200


@pytest.mark.skipif("p03" not in BUNDLES, reason="no dataset")
def test_upload_fails_loudly_when_the_server_does(client, monkeypatch):
    def down(tx):
        raise httpx.ConnectError("down")

    monkeypatch.setattr(load_fhir, "put", down)
    assert upload(client, BUNDLES["p03"]).status_code == 503
    monkeypatch.setattr(load_fhir, "put", lambda tx: httpx.Response(400, request=OK, text="bad"))
    assert upload(client, BUNDLES["p03"]).status_code == 422
