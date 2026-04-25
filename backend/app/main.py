"""FastAPI app — start jobs, poll status, download report."""
from __future__ import annotations

import threading
import uuid
from typing import Dict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from .agents.orchestrator import run_job
from .models.schemas import SourcingJob, StartJobRequest, StartJobResponse
from .services.report import build_zip

app = FastAPI(title="Supplier Sourcing Agent API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory job store (good enough for demo)
JOBS: Dict[str, SourcingJob] = {}


def _run_in_thread(job_id: str) -> None:
    job = JOBS[job_id]
    JOBS[job_id] = run_job(job)


@app.get("/")
def root() -> dict:
    return {"ok": True, "service": "Supplier Sourcing Agent", "jobs": len(JOBS)}


@app.post("/jobs", response_model=StartJobResponse)
def start_job(req: StartJobRequest) -> StartJobResponse:
    job_id = str(uuid.uuid4())[:8]
    job = SourcingJob(job_id=job_id, spec=req.spec, status="pending")
    JOBS[job_id] = job
    threading.Thread(target=_run_in_thread, args=(job_id,), daemon=True).start()
    return StartJobResponse(job_id=job_id)


@app.get("/jobs/{job_id}", response_model=SourcingJob)
def get_job(job_id: str) -> SourcingJob:
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job


@app.get("/jobs/{job_id}/report")
def download_report(job_id: str) -> Response:
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if job.status != "done":
        raise HTTPException(400, f"Job not finished (status={job.status})")
    data = build_zip(job)
    return Response(
        content=data,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="sourcing_{job_id}.zip"'},
    )
