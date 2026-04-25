"""Agents #6-10 — Vetting pipeline.

CredibilityScorer, ReviewSentimentAgent, CertVerifier,
RedFlagDetector, ComplianceChecker.
"""
from __future__ import annotations

from typing import List

from ..models.schemas import ProductSpec, Supplier

# Sanctioned / forced-labor concern regions (illustrative — not legal advice)
HIGH_RISK_REGIONS = {"north korea", "iran", "syria"}


# ---------- 6. CredibilityScorer ----------
def credibility_score(s: Supplier) -> float:
    """0..100 trust score from operational signals."""
    score = 0.0
    score += min(s.years_active, 15) * 3              # max 45
    score += s.response_rate * 25                     # max 25
    score += min(s.transaction_volume_usd / 100_000, 15)  # max 15
    score += min(s.staff_count / 50, 10)              # max 10
    score += min(s.factory_size_sqm / 5000, 5)        # max 5
    return round(min(score, 100), 1)


# ---------- 7. ReviewSentimentAgent ----------
def review_sentiment(s: Supplier) -> float:
    """Lightweight proxy: rating + review volume → -1..1."""
    if s.review_count == 0:
        return 0.0
    base = (s.avg_rating - 3.0) / 2.0          # 3.0→0, 5.0→1
    volume_boost = min(s.review_count / 500, 1.0) * 0.2
    return round(max(min(base + volume_boost, 1.0), -1.0), 2)


# ---------- 8. CertVerifier ----------
def verify_certs(s: Supplier, required: List[str]) -> bool:
    if not required:
        return True
    sup_certs = {c.upper() for c in s.certifications}
    needed = {c.upper() for c in required}
    return needed.issubset(sup_certs)


# ---------- 9. RedFlagDetector ----------
def detect_red_flags(s: Supplier, spec: ProductSpec) -> List[str]:
    flags: List[str] = []
    if s.years_active < 2:
        flags.append("New account (<2 years)")
    if s.response_rate < 0.6:
        flags.append("Low response rate")
    if s.review_count < 5:
        flags.append("Almost no reviews")
    if s.avg_rating and s.avg_rating < 3.8:
        flags.append("Low avg rating")
    if spec.target_price and s.quoted_price < spec.target_price * 0.5:
        flags.append("Suspiciously cheap")
    if s.moq > spec.moq * 4 and spec.moq > 0:
        flags.append("MOQ much higher than requested")
    return flags


# ---------- 10. ComplianceChecker ----------
def compliance_check(s: Supplier) -> bool:
    return s.country.lower() not in HIGH_RISK_REGIONS


# ---------- Aggregate runner ----------
def run_vetting(suppliers: List[Supplier], spec: ProductSpec) -> List[Supplier]:
    for s in suppliers:
        s.trust_score = credibility_score(s)
        s.review_sentiment = review_sentiment(s)
        s.cert_verified = verify_certs(s, spec.certifications)
        s.red_flags = detect_red_flags(s, spec)
        s.compliance_ok = compliance_check(s)
    return suppliers
