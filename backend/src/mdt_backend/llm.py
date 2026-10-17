"""Minimal client for the OpenAI-compatible chat endpoint (Azure APIM). Structured output only."""

import json
import threading
import time

import httpx

from mdt_backend.config import settings

# The APIM deployment rate-limits (429) when many pipeline steps/patients run at once, and
# occasionally fails with a transient 5xx; both are retried with backoff
_SLOTS = threading.BoundedSemaphore(4)
_RETRIES = 6
_RETRY_STATUS = {429, 500, 502, 503, 504}


def chat_json(
    system: str, user: str, schema: dict, name: str = "odpoved", effort: str | None = None
) -> dict:
    """One chat completion constrained to `schema` (strict JSON schema); returns the parsed JSON.
    `effort`: the model's reasoning effort ("none", "low", …); None = the deployment's default."""
    if not settings.azure_api_key:
        raise RuntimeError("AZURE_API_KEY is not set (put it in .env at the repo root)")
    body = {
        "model": settings.llm_model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": name, "strict": True, "schema": schema},
        },
    }
    if effort:
        body["reasoning_effort"] = effort
    for attempt in range(_RETRIES + 1):
        with _SLOTS:
            r = httpx.post(
                f"{settings.llm_base_url.rstrip('/')}/chat/completions",
                headers={"api-key": settings.azure_api_key},
                json=body,
                timeout=600,
            )
        if r.status_code not in _RETRY_STATUS or attempt == _RETRIES:
            break
        wait = r.headers.get("retry-after", "")
        time.sleep(float(wait) if wait.isdigit() else min(5 * 2**attempt, 60))
    r.raise_for_status()
    choice = r.json()["choices"][0]
    if choice["finish_reason"] != "stop" or choice["message"].get("refusal"):
        raise RuntimeError(f"LLM did not finish: {choice['finish_reason']} {choice['message']}")
    return json.loads(choice["message"]["content"])
