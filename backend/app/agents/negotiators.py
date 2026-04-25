"""Agents #11-16 — Negotiation, costing, ranking, output."""
from __future__ import annotations

import statistics
from typing import List

from ..core.llm import chat
from ..models.schemas import ProductSpec, Supplier

# Rough import duty rates by destination country (illustrative)
DUTY_RATES = {
    "US": 0.05, "DE": 0.06, "UK": 0.04, "FR": 0.06, "IN": 0.10,
    "CA": 0.05, "AU": 0.05, "JP": 0.04, "BR": 0.14,
}
VAT_RATES = {
    "US": 0.0, "DE": 0.19, "UK": 0.20, "FR": 0.20, "IN": 0.18,
    "CA": 0.05, "AU": 0.10, "JP": 0.10, "BR": 0.17,
}

CULTURAL_TIPS = {
    "China":     "Open with relationship-building; avoid blunt price pushback in the first email.",
    "Hong Kong": "Direct but polite; emphasise long-term partnership.",
    "Taiwan":    "Formal; mention quality standards and certifications upfront.",
    "India":     "Friendly tone; flexibility on payment terms is highly valued.",
    "Vietnam":   "Polite; discuss MOQ and payment terms early.",
    "Bangladesh":"Polite and structured; clear scope helps.",
}


# ---------- 11. PriceBenchmarker ----------
def benchmark_prices(suppliers: List[Supplier]) -> tuple[float, float, float]:
    prices = [s.quoted_price for s in suppliers if s.quoted_price > 0]
    if not prices:
        return (0.0, 0.0, 0.0)
    return (min(prices), statistics.median(prices), max(prices))


# ---------- 12. NegotiationStrategist ----------
def negotiation_strategy(s: Supplier, spec: ProductSpec, median_price: float) -> str:
    leverage = []
    if s.quoted_price > median_price:
        leverage.append(f"Quoted ${s.quoted_price:.2f} is above market median ${median_price:.2f}")
    if s.response_rate < 0.7:
        leverage.append("Low response rate — they need orders")
    if s.moq > spec.moq:
        leverage.append(f"Push MOQ down from {s.moq} toward {spec.moq}")
    if not leverage:
        leverage.append("Strong supplier — focus on payment terms (T/T 30/70) and sample cost waiver")
    target = round(min(s.quoted_price, median_price) * 0.92, 2)
    return f"Open at ${target}; leverage: " + "; ".join(leverage)


# ---------- 13. EmailDrafter ----------
def draft_email(s: Supplier, spec: ProductSpec) -> str:
    cultural = CULTURAL_TIPS.get(s.country, "Professional and concise tone.")
    fallback = (
        f"Dear {s.name} team,\n\n"
        f"We are evaluating suppliers for {spec.product_name} (HS {spec.hs_code or 'N/A'}). "
        f"Our target order is {spec.moq} units at around {spec.currency} {spec.target_price} per unit, "
        f"shipped to {spec.ship_to_country}. Required certifications: "
        f"{', '.join(spec.certifications) or 'standard quality'}.\n\n"
        f"Could you please share:\n"
        f"  1. Confirmed unit price at our MOQ\n"
        f"  2. Lead time for production and shipping\n"
        f"  3. Sample cost and turnaround\n"
        f"  4. Available certifications\n\n"
        f"We look forward to building a long-term partnership.\n\n"
        f"Best regards,\nProcurement Team"
    )
    prompt = (
        f"Write a concise, professional B2B inquiry email to a supplier from {s.country}.\n"
        f"Product: {spec.product_name}\n"
        f"MOQ: {spec.moq}, target price: {spec.currency} {spec.target_price}\n"
        f"Ship to: {spec.ship_to_country}\n"
        f"Required certs: {', '.join(spec.certifications) or 'standard'}\n"
        f"Cultural guidance: {cultural}\n"
        f"Their quoted price: ${s.quoted_price}, their MOQ: {s.moq}.\n"
        f"Output the email body only — no subject line, no markdown."
    )
    return chat(prompt, system="You are an experienced international procurement manager.", fallback=fallback)


# ---------- 14. SampleRequestAgent ----------
def sample_request(s: Supplier, spec: ProductSpec) -> str:
    return (
        f"Sample Request — {spec.product_name}\n"
        f"Quantity: 3 units\n"
        f"Specs: {spec.description or spec.product_name}\n"
        f"Materials: {', '.join(spec.materials) or 'as per standard'}\n"
        f"Certifications to demonstrate: {', '.join(spec.certifications) or 'N/A'}\n"
        f"Sample cost: requested waived against future order; we cover DHL Express to {spec.ship_to_country}.\n"
        f"QC checklist: dimensions, weight, material composition, finish, packaging.\n"
        f"Required by: within {min(spec.timeline_days, 14)} days."
    )


# ---------- 15. LandedCostCalculator ----------
def landed_cost(s: Supplier, spec: ProductSpec) -> tuple[float, dict[str, float]]:
    fob = s.quoted_price
    shipping_per_unit = round(0.30 + (1.0 / max(s.moq, 1)) * 50, 2)  # rough
    duty = round(fob * DUTY_RATES.get(spec.ship_to_country, 0.05), 2)
    vat_base = fob + shipping_per_unit + duty
    vat = round(vat_base * VAT_RATES.get(spec.ship_to_country, 0.0), 2)
    total = round(fob + shipping_per_unit + duty + vat, 2)
    return total, {
        "fob": fob,
        "shipping_per_unit": shipping_per_unit,
        "duty": duty,
        "vat": vat,
        "total": total,
    }


# ---------- 16. ReportGenerator (ranking) ----------
def rank_suppliers(suppliers: List[Supplier], spec: ProductSpec) -> List[Supplier]:
    """Composite final score (0..100) then assign ranks."""
    if not suppliers:
        return suppliers
    landed = [s.landed_cost for s in suppliers if s.landed_cost > 0] or [1.0]
    cheapest = min(landed)
    most_expensive = max(landed)
    span = max(most_expensive - cheapest, 0.01)

    for s in suppliers:
        # Trust: 40%
        trust_part = s.trust_score * 0.40
        # Price (cheaper = better): 30%
        price_part = (1 - (s.landed_cost - cheapest) / span) * 30 if s.landed_cost else 0
        # Cert match: 15%
        cert_part = 15 if s.cert_verified else 5
        # Sentiment: 10%
        sent_part = ((s.review_sentiment + 1) / 2) * 10
        # Compliance: 5%
        comp_part = 5 if s.compliance_ok else 0
        # Penalty for red flags
        flag_penalty = min(len(s.red_flags) * 4, 20)

        s.final_score = round(max(trust_part + price_part + cert_part + sent_part + comp_part - flag_penalty, 0), 1)

    suppliers.sort(key=lambda x: x.final_score, reverse=True)
    for i, s in enumerate(suppliers, start=1):
        s.rank = i
    return suppliers


def run_negotiation_pipeline(suppliers: List[Supplier], spec: ProductSpec) -> List[Supplier]:
    _, median, _ = benchmark_prices(suppliers)
    for s in suppliers:
        s.landed_cost, s.landed_cost_breakdown = landed_cost(s, spec)
        s.negotiation_strategy = negotiation_strategy(s, spec, median)
        s.sample_request = sample_request(s, spec)
    # Email drafting can hit LLM — only do it for top candidates after a quick pre-rank.
    pre_ranked = rank_suppliers(list(suppliers), spec)
    top_ids = {s.id for s in pre_ranked[:10]}
    for s in suppliers:
        if s.id in top_ids:
            s.inquiry_email = draft_email(s, spec)
        else:
            s.inquiry_email = ""  # save tokens
    return rank_suppliers(suppliers, spec)
