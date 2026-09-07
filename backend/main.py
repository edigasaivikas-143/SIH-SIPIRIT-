"""
3D ULPIN Generation & Vertical Property Mapping — API entrypoint.

Run with:  uvicorn main:app --reload --port 8000
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router as api_router
from api.nl_query import router as nl_query_router
from services.job_queue import job_queue

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ulpin3d")

app = FastAPI(
    title="3D ULPIN Generation & Vertical Property Mapping",
    description=(
        "API for generating standardized 3D cadastral identifiers, mapping "
        "vertical/underground ownership rights, and validating volumetric "
        "cadastre topology."
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten before production
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")
app.include_router(nl_query_router, prefix="/api/v1/query")


@app.on_event("startup")
async def on_startup():
    logger.info("Starting 3D ULPIN backend...")
    await job_queue.start()


@app.on_event("shutdown")
async def on_shutdown():
    logger.info("Shutting down job queue...")
    await job_queue.stop()


@app.get("/health")
async def health():
    return {"status": "ok", "service": "3d-ulpin-backend"}
