"""Mock supplier database — replace with real Playwright scrapers later."""
from __future__ import annotations

import random
from typing import List

from ..models.schemas import ProductSpec, Supplier

# Country pool per platform (realistic distribution)
PLATFORM_COUNTRIES = {
    "alibaba": ["China", "China", "China", "Vietnam", "Hong Kong"],
    "indiamart": ["India", "India", "India", "Bangladesh"],
    "globalsources": ["China", "Hong Kong", "Taiwan", "China"],
    "madeinchina": ["China", "China", "China"],
}

NAME_PREFIXES = [
    "Shenzhen", "Guangzhou", "Yiwu", "Ningbo", "Hangzhou",
    "Mumbai", "Delhi", "Bangalore", "Chennai", "Kolkata",
    "Hong Kong", "Taipei", "Hanoi", "Hefei", "Qingdao",
]
NAME_SUFFIXES = [
    "Industrial Co., Ltd", "Trading Co.", "Manufacturing Inc.",
    "Exports Pvt Ltd", "Global Trade Co.", "Eco Products Co.",
    "Green Goods Ltd", "Premium Supplies", "Smart Manufacturing",
]

CERT_POOL = ["ISO9001", "ISO14001", "FSC", "FDA", "CE", "BSCI", "REACH", "RoHS", "GOTS"]


def _make_supplier(idx: int, platform: str, spec: ProductSpec) -> Supplier:
    rng = random.Random(f"{platform}-{idx}-{spec.product_name}")
    country = rng.choice(PLATFORM_COUNTRIES[platform])
    name = f"{rng.choice(NAME_PREFIXES)} {spec.product_name.split()[0].title()} {rng.choice(NAME_SUFFIXES)}"

    years = rng.randint(1, 18)
    response_rate = round(rng.uniform(0.45, 0.99), 2)
    quoted = round(spec.target_price * rng.uniform(0.70, 1.45), 2)
    moq = rng.choice([100, 200, 300, 500, 500, 1000, 2000])

    # Cert overlap with requested
    n_certs = rng.randint(0, min(5, len(CERT_POOL)))
    certs = rng.sample(CERT_POOL, n_certs)
    # boost: include requested certs sometimes
    for c in spec.certifications:
        if rng.random() < 0.55 and c not in certs:
            certs.append(c)

    return Supplier(
        id=f"{platform}-{idx:03d}",
        name=name,
        platform=platform,
        country=country,
        years_active=years,
        response_rate=response_rate,
        transaction_volume_usd=rng.randint(50_000, 5_000_000),
        staff_count=rng.choice([10, 25, 50, 100, 250, 500]),
        factory_size_sqm=rng.choice([500, 1500, 3000, 8000, 20000]),
        certifications=certs,
        quoted_price=quoted,
        moq=moq,
        lead_time_days=rng.randint(15, 60),
        review_count=rng.randint(0, 850),
        avg_rating=round(rng.uniform(3.2, 4.95), 2),
        profile_url=f"https://{platform}.com/supplier/{idx}",
        contact_email=f"sales{idx}@{platform.replace('.', '')}-supplier.com",
    )


def fetch_mock_suppliers(spec: ProductSpec, platform: str, n: int = 6) -> List[Supplier]:
    return [_make_supplier(i, platform, spec) for i in range(1, n + 1)]
