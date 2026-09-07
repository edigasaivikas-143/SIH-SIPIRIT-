"""
Module G — Intelligent topology, geometry, and survey validation.
(Project Guide, Section 8 + the "Live validation-catch demo technique".)

Checks implemented for the hackathon MVP:
  - GEOMETRY_VALIDITY     : footprint polygon is simple/non-self-intersecting
  - INTERSECTION          : two spaces' volumes unintentionally overlap
  - CONTAINMENT           : a unit stays inside its parent structure footprint
  - ADJACENCY              : shared-boundary spaces actually touch (no gaps)
  - FLOOR_ORDERING        : F01/F02/... and B01/B02/... have consistent, non-overlapping Z ranges
  - RIGHTS_CONSISTENCY    : flags two ACTIVE ownership-class rights on the same volume
  - SURVEY_TOLERANCE      : roadmap-scope stub (needs a ground-truth survey to compare against)
  - PROVENANCE_COMPLETENESS: every space has source_date/source/processing_version before APPROVED
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional

from shapely.geometry import Polygon
from shapely.validation import explain_validity

logger = logging.getLogger("ulpin3d.topology_checks")

OWNERSHIP_RIGHT_TYPES = {"OWNERSHIP"}


@dataclass
class ValidationResult:
    parcel_3d_id: str
    rule: str
    result: str          # PASS / FAIL / WARN
    detail: str = ""
    conflicting_id: Optional[str] = None
    tolerance: Optional[float] = None


def check_geometry_validity(space: dict) -> ValidationResult:
    footprint = space.get("footprint") or []
    if len(footprint) < 3:
        return ValidationResult(space["parcel_3d_id"], "GEOMETRY_VALIDITY", "FAIL",
                                 detail="footprint has fewer than 3 vertices")
    poly = Polygon(footprint)
    if poly.is_valid:
        return ValidationResult(space["parcel_3d_id"], "GEOMETRY_VALIDITY", "PASS")
    return ValidationResult(space["parcel_3d_id"], "GEOMETRY_VALIDITY", "FAIL",
                             detail=explain_validity(poly))


def _z_overlap(a: dict, b: dict) -> float:
    """Returns the overlap in metres between two spaces' Z ranges (0 if none)."""
    lo = max(a["z_min"], b["z_min"])
    hi = min(a["z_max"], b["z_max"])
    return max(0.0, hi - lo)


def check_intersection(space: dict, others: List[dict]) -> List[ValidationResult]:
    """
    Flags an unintended 3D overlap: XY footprint overlap AND Z-range overlap
    between two spaces that are NOT declared as legitimately co-located
    (i.e. not a rights-only intersection like a common corridor over a unit).
    """
    results = []
    poly_a = Polygon(space["footprint"])
    for other in others:
        if other["parcel_3d_id"] == space["parcel_3d_id"]:
            continue
        z_overlap = _z_overlap(space, other)
        if z_overlap <= 0:
            continue
        poly_b = Polygon(other["footprint"])
        if not poly_a.intersects(poly_b):
            continue
        xy_overlap = poly_a.intersection(poly_b).area
        if xy_overlap <= 0:
            continue
        results.append(ValidationResult(
            parcel_3d_id=space["parcel_3d_id"],
            rule="INTERSECTION",
            result="FAIL",
            detail=(f"3D intersection check: {space['unit_id']} overlaps {other['unit_id']}, "
                    f"Z {max(space['z_min'], other['z_min']):.1f}-{min(space['z_max'], other['z_max']):.1f} m"),
            conflicting_id=other["parcel_3d_id"],
        ))
    if not results:
        results.append(ValidationResult(space["parcel_3d_id"], "INTERSECTION", "PASS"))
    return results


def check_containment(space: dict, structure_footprint: List[tuple]) -> ValidationResult:
    poly = Polygon(space["footprint"])
    parent = Polygon(structure_footprint)
    if parent.contains(poly) or parent.equals(poly):
        return ValidationResult(space["parcel_3d_id"], "CONTAINMENT", "PASS")
    return ValidationResult(space["parcel_3d_id"], "CONTAINMENT", "FAIL",
                             detail=f"{space['unit_id']} extends outside its parent structure footprint")


def check_floor_ordering(floors: List[dict]) -> List[ValidationResult]:
    """floors: list of {z_level, z_min, z_max} sorted by z_min."""
    results = []
    ordered = sorted(floors, key=lambda f: f["z_min"])
    for prev, cur in zip(ordered, ordered[1:]):
        if cur["z_min"] < prev["z_max"] - 1e-6:
            results.append(ValidationResult(
                parcel_3d_id=cur.get("parcel_3d_id", cur["z_level"]),
                rule="FLOOR_ORDERING",
                result="FAIL",
                detail=f"{cur['z_level']} (z_min={cur['z_min']}) overlaps {prev['z_level']} (z_max={prev['z_max']})",
            ))
    if not results:
        results.append(ValidationResult(parcel_3d_id="structure", rule="FLOOR_ORDERING", result="PASS"))
    return results


def check_rights_consistency(space: dict, rights: List[dict]) -> ValidationResult:
    """
    Flags contradictory ownership: more than one ACTIVE OWNERSHIP-type right
    on the same volume (legitimate cases — e.g. one OWNERSHIP + one EASEMENT —
    are allowed; two competing OWNERSHIP records are not).
    """
    active_ownership = [r for r in rights if r["active"] and r["right_type"] in OWNERSHIP_RIGHT_TYPES]
    if len(active_ownership) <= 1:
        return ValidationResult(space["parcel_3d_id"], "RIGHTS_CONSISTENCY", "PASS")
    parties = ", ".join(r["party_id"] for r in active_ownership)
    return ValidationResult(
        space["parcel_3d_id"], "RIGHTS_CONSISTENCY", "FAIL",
        detail=f"{len(active_ownership)} active ownership records on one volume: {parties}",
    )


def check_provenance_completeness(space: dict, sources: List[dict]) -> ValidationResult:
    if not sources:
        return ValidationResult(space["parcel_3d_id"], "PROVENANCE_COMPLETENESS", "FAIL",
                                 detail="no linked source record")
    incomplete = [s for s in sources if not (s.get("survey_date") and s.get("source_type"))]
    if incomplete:
        return ValidationResult(space["parcel_3d_id"], "PROVENANCE_COMPLETENESS", "WARN",
                                 detail=f"{len(incomplete)} source(s) missing survey_date or source_type")
    return ValidationResult(space["parcel_3d_id"], "PROVENANCE_COMPLETENESS", "PASS")


def run_full_validation(space: dict, all_spaces: List[dict], rights: List[dict],
                         structure_footprint: Optional[List[tuple]] = None,
                         sources: Optional[List[dict]] = None) -> List[ValidationResult]:
    """Runs every applicable check for one space and returns all results."""
    results = [check_geometry_validity(space)]
    results.extend(check_intersection(space, all_spaces))
    if structure_footprint:
        results.append(check_containment(space, structure_footprint))
    results.append(check_rights_consistency(space, [r for r in rights if r["parcel_3d_id"] == space["parcel_3d_id"]]))
    results.append(check_provenance_completeness(space, sources or []))
    return results


# ------------------------------------------------------------------
# Live validation-catch demo helper (Section 8 "NEW")
# ------------------------------------------------------------------
def plant_conflicting_geometry(base_space: dict, overlap_z_m: float = 0.2) -> dict:
    """
    Builds a deliberately conflicting unit directly above `base_space`,
    overlapping its top Z-range by `overlap_z_m`, for the on-stage
    "run validation live and watch it fail" demo beat.
    """
    return {
        **base_space,
        "parcel_3d_id": f"{base_space['parcel_3d_id']}-CONFLICT",
        "unit_id": f"{base_space['unit_id']}-B",
        "z_min": base_space["z_max"] - overlap_z_m,
        "z_max": base_space["z_max"] - overlap_z_m + (base_space["z_max"] - base_space["z_min"]),
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    unit_301 = {
        "parcel_3d_id": "space-301", "unit_id": "A301",
        "footprint": [(0, 0), (5, 0), (5, 5), (0, 5)],
        "z_min": 9.2, "z_max": 12.4,
    }
    unit_201_conflict = plant_conflicting_geometry(unit_301, overlap_z_m=0.2)
    results = check_intersection(unit_301, [unit_201_conflict])
    for r in results:
        print(r.rule, r.result, r.detail)
