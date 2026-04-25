"""Agents #2-5 — Discovery: 4 parallel platform sourcers.

Currently uses mock data. Each function is async so a real Playwright scraper
can be plugged in later without changing the orchestrator.
"""
from __future__ import annotations

import asyncio
from typing import List

from ..models.schemas import ProductSpec, Supplier
from ..services.mock_data import fetch_mock_suppliers


async def alibaba_sourcer(spec: ProductSpec) -> List[Supplier]:
    await asyncio.sleep(0.4)
    return fetch_mock_suppliers(spec, "alibaba", n=6)


async def indiamart_sourcer(spec: ProductSpec) -> List[Supplier]:
    await asyncio.sleep(0.3)
    return fetch_mock_suppliers(spec, "indiamart", n=5)


async def globalsources_sourcer(spec: ProductSpec) -> List[Supplier]:
    await asyncio.sleep(0.3)
    return fetch_mock_suppliers(spec, "globalsources", n=4)


async def madeinchina_sourcer(spec: ProductSpec) -> List[Supplier]:
    await asyncio.sleep(0.3)
    return fetch_mock_suppliers(spec, "madeinchina", n=5)


async def run_all_sourcers(spec: ProductSpec) -> List[Supplier]:
    results = await asyncio.gather(
        alibaba_sourcer(spec),
        indiamart_sourcer(spec),
        globalsources_sourcer(spec),
        madeinchina_sourcer(spec),
    )
    flat: List[Supplier] = []
    for batch in results:
        flat.extend(batch)
    return flat
