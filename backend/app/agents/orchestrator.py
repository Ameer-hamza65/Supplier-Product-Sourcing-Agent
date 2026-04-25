"""LangGraph orchestrator wiring all 16 agents.

Graph stages:
   intake → discovery → vetting → negotiation → done
"""
from __future__ import annotations

import asyncio
from typing import TypedDict

from langgraph.graph import END, StateGraph

from ..models.schemas import ProductSpec, SourcingJob, Supplier
from .negotiators import run_negotiation_pipeline
from .sourcers import run_all_sourcers
from .spec_parser import parse_spec
from .vetters import run_vetting


class GraphState(TypedDict):
    job: SourcingJob


def _log(state: GraphState, msg: str, progress: int, stage: str) -> None:
    job = state["job"]
    job.log.append(msg)
    job.progress = progress
    job.current_stage = stage


# --- Nodes ---
def node_intake(state: GraphState) -> GraphState:
    job = state["job"]
    job.spec = parse_spec(job.spec)
    _log(state, f"SpecParser: HS={job.spec.hs_code} materials={job.spec.materials}", 10, "intake")
    return state


def node_discovery(state: GraphState) -> GraphState:
    job = state["job"]
    suppliers = asyncio.run(run_all_sourcers(job.spec))
    job.suppliers = suppliers
    _log(state, f"Discovery: {len(suppliers)} suppliers found across 4 platforms", 35, "discovery")
    return state


def node_vetting(state: GraphState) -> GraphState:
    job = state["job"]
    job.suppliers = run_vetting(job.suppliers, job.spec)
    _log(state, f"Vetting complete: trust scores, certs, red flags applied", 60, "vetting")
    return state


def node_negotiation(state: GraphState) -> GraphState:
    job = state["job"]
    job.suppliers = run_negotiation_pipeline(job.suppliers, job.spec)
    _log(state, f"Negotiation pipeline done; top {min(10, len(job.suppliers))} ranked", 95, "negotiation")
    return state


def node_done(state: GraphState) -> GraphState:
    job = state["job"]
    job.status = "done"
    job.progress = 100
    job.current_stage = "done"
    job.log.append("Job complete.")
    return state


def build_graph():
    g = StateGraph(GraphState)
    g.add_node("intake", node_intake)
    g.add_node("discovery", node_discovery)
    g.add_node("vetting", node_vetting)
    g.add_node("negotiation", node_negotiation)
    g.add_node("done", node_done)

    g.set_entry_point("intake")
    g.add_edge("intake", "discovery")
    g.add_edge("discovery", "vetting")
    g.add_edge("vetting", "negotiation")
    g.add_edge("negotiation", "done")
    g.add_edge("done", END)
    return g.compile()


GRAPH = build_graph()


def run_job(job: SourcingJob) -> SourcingJob:
    job.status = "running"
    try:
        result = GRAPH.invoke({"job": job})
        return result["job"]
    except Exception as e:  # noqa: BLE001
        job.status = "error"
        job.error = str(e)
        job.log.append(f"ERROR: {e}")
        return job
