from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ProductSpec(BaseModel):
    product_name: str
    description: str = ""
    moq: int = 100
    target_price: float = 1.0
    currency: str = "USD"
    certifications: list[str] = Field(default_factory=list)
    ship_to_country: str = "US"
    timeline_days: int = 30
    materials: list[str] = Field(default_factory=list)
    hs_code: Optional[str] = None


class Supplier(BaseModel):
    id: str
    name: str
    platform: str  # alibaba | indiamart | globalsources | madeinchina
    country: str
    years_active: int = 0
    response_rate: float = 0.0  # 0..1
    transaction_volume_usd: float = 0.0
    staff_count: int = 0
    factory_size_sqm: int = 0
    certifications: list[str] = Field(default_factory=list)
    quoted_price: float = 0.0
    moq: int = 0
    lead_time_days: int = 30
    review_count: int = 0
    avg_rating: float = 0.0
    profile_url: str = ""
    contact_email: str = ""

    # Filled by vetting agents
    trust_score: float = 0.0
    review_sentiment: float = 0.0  # -1..1
    cert_verified: bool = False
    red_flags: list[str] = Field(default_factory=list)
    compliance_ok: bool = True

    # Filled by negotiation agents
    negotiation_strategy: str = ""
    inquiry_email: str = ""
    sample_request: str = ""
    landed_cost: float = 0.0
    landed_cost_breakdown: dict[str, float] = Field(default_factory=dict)
    final_score: float = 0.0
    rank: int = 0


class SourcingJob(BaseModel):
    job_id: str
    spec: ProductSpec
    status: str = "pending"  # pending | running | done | error
    progress: int = 0
    current_stage: str = ""
    log: list[str] = Field(default_factory=list)
    suppliers: list[Supplier] = Field(default_factory=list)
    error: str = ""


class StartJobRequest(BaseModel):
    spec: ProductSpec


class StartJobResponse(BaseModel):
    job_id: str
