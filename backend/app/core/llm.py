"""Thin wrapper around OpenAI chat completions with graceful fallback."""
from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from .config import settings

_client: OpenAI | None = None


def _get_client() -> OpenAI | None:
    global _client
    if not settings.OPENAI_API_KEY:
        return None
    if _client is None:
        _client = OpenAI(api_key=settings.OPENAI_API_KEY)
    return _client


def chat(prompt: str, system: str = "", temperature: float = 0.4, fallback: str = "") -> str:
    """Run a chat completion. If no API key or call fails, return fallback."""
    client = _get_client()
    if client is None:
        return fallback or "[LLM disabled — set OPENAI_API_KEY in .env]"
    try:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        resp = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=messages,
            temperature=temperature,
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception as e:  # noqa: BLE001
        return fallback or f"[LLM error: {e}]"


def chat_json(prompt: str, system: str = "", temperature: float = 0.2, fallback: dict | None = None) -> dict[str, Any]:
    """Chat completion that asks for JSON. Returns dict (or fallback on failure)."""
    client = _get_client()
    if client is None:
        return fallback or {}
    try:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt + "\n\nRespond with valid JSON only."})
        resp = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=messages,
            temperature=temperature,
            response_format={"type": "json_object"},
        )
        return json.loads(resp.choices[0].message.content or "{}")
    except Exception:
        return fallback or {}
