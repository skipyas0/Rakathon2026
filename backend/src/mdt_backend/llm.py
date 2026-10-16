"""Minimal client for the OpenAI-compatible chat endpoint (Azure APIM). Structured output only."""

import json

import httpx

from mdt_backend.config import settings


def chat_json(system: str, user: str, schema: dict, name: str = "odpoved") -> dict:
    """One chat completion constrained to `schema` (strict JSON schema); returns the parsed JSON."""
    if not settings.azure_api_key:
        raise RuntimeError("AZURE_API_KEY is not set (put it in .env at the repo root)")
    r = httpx.post(
        f"{settings.llm_base_url.rstrip('/')}/chat/completions",
        headers={"api-key": settings.azure_api_key},
        json={
            "model": settings.llm_model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": name, "strict": True, "schema": schema},
            },
        },
        timeout=600,
    )
    r.raise_for_status()
    choice = r.json()["choices"][0]
    if choice["finish_reason"] != "stop" or choice["message"].get("refusal"):
        raise RuntimeError(f"LLM did not finish: {choice['finish_reason']} {choice['message']}")
    return json.loads(choice["message"]["content"])
