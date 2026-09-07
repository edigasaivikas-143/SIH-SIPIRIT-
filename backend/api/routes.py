"""
Core REST API: parcel lookup, geometry retrieval, rights retrieval,
validation status, 3D ULPIN generation, pipeline triggers, RERA check, export.

Runs in DEMO_MODE (in-memory store) when no Postgres/PostGIS connection is
configured, so the API is runnable on a judge's laptop without a DB —
see the project guide's "Data & demo risk plan" (Section 6).
"""

import os
import uuid
from datetime import datetime, date
from typing import Optional, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(tags=["cadastre"])

DEMO_MODE = os.getenv("ULPIN_DEMO_MODE", "true").lower() == "true"

# ------------------------------------------------------------------
# In-memory demo store (swapped for asyncpg/PostGIS in production —
# see database/schema.sql for the real table shapes this mirrors)
# ------------------------------------------------------------------
_PARCELS: dict = {}
_SPACES: dict = {}
_RIGHTS: dict = {}
_VALIDATIONS: dict = {}
_RERA_CHECKS: dict = {}

VALID_SPACE_CLASSES = {"V", "S", "U", "E"}   # Vertical, Surface, Underground, Elevated
VALID_RIGHTS_CODES = {"PRV", "COM", "UTL", "CML"}


# ------------------------------------------------------------------
# Schemas
# ------------------------------------------------------------------
class ParcelIn(BaseModel):
    parent_ulpin: str = Field(..., min_length=14, max_length=14)
    geometry_2d: dict  # GeoJSON polygon


class Space3DIn(BaseModel):
    parcel_id: str
    z_level: str        # F03 / B01 / G00 / R00
    space_class: str
    rights_code: str
    unit_id: str
    z_min: float
    z_max: float
    geometry_3d: Optional[dict] = None
    confidence: Optional[float] = None
    source_ids: List[str] = []


class RightIn(BaseModel):
    party_id: str
    right_type: str
    valid_from: date
    valid_to: Optional[date] = None
    source_document: Optional[str] = None


class RERACheckIn(BaseModel):
    declared_carpet_m2: float
    measured_carpet_m2: float
    confidence: float


# ------------------------------------------------------------------
# 3D ULPIN code generation
# Format: [Parent ULPIN]-[Z-Level]-[Space Class]-[Rights/Use Code]-[Unit ID]-[Version]
# ------------------------------------------------------------------
def generate_ulpin_3d_code(parent_ulpin: str, z_level: str, space_class: str,
                            rights_code: str, unit_id: str, version: int = 1) -> str:
    if space_class not in VALID_SPACE_CLASSES:
        raise ValueError(f"space_class must be one of {VALID_SPACE_CLASSES}")
    if rights_code not in VALID_RIGHTS_CODES:
        raise ValueError(f"rights_code must be one of {VALID_RIGHTS_CODES}")
    return f"{parent_ulpin}-{z_level}-{space_class}-{rights_code}-{unit_id}-V{version:02d}"


# ------------------------------------------------------------------
# Parcel endpoints
# ------------------------------------------------------------------
@router.post("/parcels")
async def create_parcel(parcel: ParcelIn):
    parcel_id = str(uuid.uuid4())
    _PARCELS[parcel_id] = {
        "parcel_id": parcel_id,
        "parent_ulpin": parcel.parent_ulpin,
        "geometry_2d": parcel.geometry_2d,
        "status": "ACTIVE",
        "created_at": datetime.utcnow().isoformat(),
    }
    return _PARCELS[parcel_id]


@router.get("/parcels/{parcel_id}")
async def get_parcel(parcel_id: str):
    parcel = _PARCELS.get(parcel_id)
    if not parcel:
        raise HTTPException(status_code=404, detail="Parcel not found")
    return parcel


@router.get("/parcels")
async def list_parcels():
    return list(_PARCELS.values())


# ------------------------------------------------------------------
# 3D space (volumetric cadastral object) endpoints
# ------------------------------------------------------------------
@router.post("/spaces")
async def create_space(space: Space3DIn):
    if space.parcel_id not in _PARCELS:
        raise HTTPException(status_code=404, detail="Parent parcel not found")
    if space.z_max <= space.z_min:
        raise HTTPException(status_code=400, detail="z_max must be greater than z_min")

    parent_ulpin = _PARCELS[space.parcel_id]["parent_ulpin"]
    try:
        code = generate_ulpin_3d_code(
            parent_ulpin, space.z_level, space.space_class, space.rights_code, space.unit_id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    space_id = str(uuid.uuid4())
    _SPACES[space_id] = {
        "parcel_3d_id": space_id,
        "ulpin_3d_code": code,
        "parcel_id": space.parcel_id,
        "z_level": space.z_level,
        "space_class": space.space_class,
        "rights_code": space.rights_code,
        "unit_id": space.unit_id,
        "version": 1,
        "z_min": space.z_min,
        "z_max": space.z_max,
        "geometry_3d": space.geometry_3d,
        "status": "AI_GENERATED",
        "confidence": space.confidence,
        "source_ids": space.source_ids,
        "created_at": datetime.utcnow().isoformat(),
    }
    return _SPACES[space_id]


@router.get("/spaces/{space_id}")
async def get_space(space_id: str):
    """Full detail view for PropertyPanel.jsx: geometry, rights, confidence, provenance, validation."""
    space = _SPACES.get(space_id)
    if not space:
        raise HTTPException(status_code=404, detail="3D space not found")
    rights = [r for r in _RIGHTS.values() if r["parcel_3d_id"] == space_id]
    validations = [v for v in _VALIDATIONS.values() if v["parcel_3d_id"] == space_id]
    return {**space, "rights": rights, "validations": validations}


@router.get("/parcels/{parcel_id}/spaces")
async def list_spaces_for_parcel(parcel_id: str):
    return [s for s in _SPACES.values() if s["parcel_id"] == parcel_id]


@router.post("/spaces/{space_id}/review")
async def advance_review_state(space_id: str, reviewer: str, decision: str):
    """Human-in-the-loop state machine: AI_GENERATED -> QA_PASSED -> SURVEY_REVIEW -> APPROVED -> PUBLISHED."""
    space = _SPACES.get(space_id)
    if not space:
        raise HTTPException(status_code=404, detail="3D space not found")
    states = ["AI_GENERATED", "QA_PASSED", "SURVEY_REVIEW", "APPROVED", "PUBLISHED"]
    if decision == "approve":
        idx = states.index(space["status"])
        space["status"] = states[min(idx + 1, len(states) - 1)]
    elif decision == "reject":
        space["status"] = "SURVEY_REVIEW"
    else:
        raise HTTPException(status_code=400, detail="decision must be 'approve' or 'reject'")
    space["last_reviewer"] = reviewer
    return space


# ------------------------------------------------------------------
# Rights endpoints
# ------------------------------------------------------------------
@router.post("/spaces/{space_id}/rights")
async def add_right(space_id: str, right: RightIn):
    if space_id not in _SPACES:
        raise HTTPException(status_code=404, detail="3D space not found")
    right_id = str(uuid.uuid4())
    _RIGHTS[right_id] = {
        "right_id": right_id,
        "parcel_3d_id": space_id,
        "party_id": right.party_id,
        "right_type": right.right_type,
        "valid_from": right.valid_from.isoformat(),
        "valid_to": right.valid_to.isoformat() if right.valid_to else None,
        "source_document": right.source_document,
        "active": True,
    }
    return _RIGHTS[right_id]


@router.get("/spaces/{space_id}/rights")
async def get_rights(space_id: str):
    return [r for r in _RIGHTS.values() if r["parcel_3d_id"] == space_id]


# ------------------------------------------------------------------
# Validation status
# ------------------------------------------------------------------
@router.get("/spaces/{space_id}/validation")
async def get_validation_status(space_id: str):
    return [v for v in _VALIDATIONS.values() if v["parcel_3d_id"] == space_id]


# ------------------------------------------------------------------
# RERA carpet-area verification (Section 9 "NEW" use case)
# ------------------------------------------------------------------
@router.post("/spaces/{space_id}/rera-check")
async def run_rera_check(space_id: str, check: RERACheckIn):
    if space_id not in _SPACES:
        raise HTTPException(status_code=404, detail="3D space not found")
    check_id = str(uuid.uuid4())
    delta = round(check.measured_carpet_m2 - check.declared_carpet_m2, 2)
    _RERA_CHECKS[check_id] = {
        "check_id": check_id,
        "parcel_3d_id": space_id,
        "declared_carpet_m2": check.declared_carpet_m2,
        "measured_carpet_m2": check.measured_carpet_m2,
        "delta_m2": delta,
        "confidence": check.confidence,
        "checked_at": datetime.utcnow().isoformat(),
    }
    return _RERA_CHECKS[check_id]


# ------------------------------------------------------------------
# Export
# ------------------------------------------------------------------
@router.get("/export/{parcel_id}")
async def export_parcel(parcel_id: str, fmt: str = "geojson"):
    if parcel_id not in _PARCELS:
        raise HTTPException(status_code=404, detail="Parcel not found")
    spaces = [s for s in _SPACES.values() if s["parcel_id"] == parcel_id]
    if fmt == "geojson":
        return {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {k: v for k, v in s.items() if k != "geometry_3d"},
                    "geometry": s.get("geometry_3d"),
                }
                for s in spaces
            ],
        }
    raise HTTPException(status_code=400, detail=f"Unsupported export format: {fmt}")


# expose the in-memory stores so other modules (job_queue, nl_query) can
# read/write the same demo data without a real DB connection
def get_demo_store():
    return {
        "parcels": _PARCELS,
        "spaces": _SPACES,
        "rights": _RIGHTS,
        "validations": _VALIDATIONS,
        "rera_checks": _RERA_CHECKS,
    }
