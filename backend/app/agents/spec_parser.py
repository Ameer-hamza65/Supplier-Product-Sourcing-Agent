"""Agent #1 — SpecParser: normalizes raw spec, infers HS code & materials via LLM."""
from __future__ import annotations

from ..core.llm import chat_json
from ..models.schemas import ProductSpec


HS_CODE_HINTS = {
    "toothbrush": "9603.21",
    "bamboo": "4421.99",
    "t-shirt": "6109.10",
    "phone case": "3926.90",
    "led light": "9405.40",
    "backpack": "4202.92",
    "bottle": "3923.30",
}


def _guess_hs_code(name: str) -> str | None:
    n = name.lower()
    for k, v in HS_CODE_HINTS.items():
        if k in n:
            return v
    return None


def parse_spec(spec: ProductSpec) -> ProductSpec:
    """Enrich ProductSpec with materials + HS code (via LLM if available)."""
    if spec.hs_code is None:
        spec.hs_code = _guess_hs_code(spec.product_name)

    if not spec.materials:
        result = chat_json(
            prompt=(
                f"Product: {spec.product_name}\n"
                f"Description: {spec.description}\n\n"
                "Return JSON with key 'materials' as a list of 1-4 likely raw materials "
                "(short lowercase strings)."
            ),
            system="You are a sourcing analyst. Be concise and accurate.",
            fallback={"materials": []},
        )
        mats = result.get("materials") or []
        if isinstance(mats, list):
            spec.materials = [str(m).lower() for m in mats][:4]

    return spec
