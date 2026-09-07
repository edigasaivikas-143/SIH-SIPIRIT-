"""
Module B — Floor segmentation: elevation clustering + floor-plan alignment.
Module C — Unit delineation: rule-based polygon splitting from floor plan + envelope.

Per Section 7's hackathon build vs. roadmap split, these are the heuristic
versions to actually build in the event window. Learned point-transformer /
sparse-convolution segmentation is roadmap-only.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np

from processing.building_extractor import BuildingEnvelope

logger = logging.getLogger("ulpin3d.segmentation")


@dataclass
class Floor:
    z_level: str        # F01, F02, ..., B01, G00, R00
    z_min: float
    z_max: float
    point_count: int


@dataclass
class Unit:
    unit_id: str
    floor_z_level: str
    space_class: str    # V / S / U / E
    rights_code: str    # PRV / COM / UTL / CML
    footprint: List[Tuple[float, float]]
    z_min: float
    z_max: float


def segment_floors(
    envelope: BuildingEnvelope,
    floor_height_m: float = 3.2,
    ground_offset_m: float = 0.0,
) -> List[Floor]:
    """
    Elevation clustering: bin points into horizontal bands of `floor_height_m`.
    Labels bands below `ground_offset_m` as basements (B01, B02, ...), the band
    at ground as G00, and floors above as F01, F02, ...

    A real deployment would align these bands against an ingested floor plan's
    declared storey heights rather than assuming a uniform height; that
    alignment step is stubbed here as `_align_to_floor_plan` for clarity.
    """
    if envelope.points is None:
        raise ValueError("envelope has no raw points to segment — pass points from extract_building()")

    z = envelope.points[:, 2]
    n_bands = int(np.ceil((z.max() - z.min()) / floor_height_m)) or 1

    floors: List[Floor] = []
    for i in range(n_bands):
        z0 = z.min() + i * floor_height_m
        z1 = z0 + floor_height_m
        mask = (z >= z0) & (z < z1 + 1e-6)
        count = int(mask.sum())
        if count == 0:
            continue
        z_level = _z_level_label(z0, ground_offset_m, floor_height_m)
        floors.append(Floor(z_level=z_level, z_min=float(z0), z_max=float(z1), point_count=count))

    logger.info("Segmented %d floors from %d points", len(floors), len(z))
    return floors


def _z_level_label(z0: float, ground_offset_m: float, floor_height_m: float) -> str:
    rel = z0 - ground_offset_m
    idx = round(rel / floor_height_m)
    if idx < 0:
        return f"B{abs(idx):02d}"
    if idx == 0:
        return "G00"
    return f"F{idx:02d}"


def _align_to_floor_plan(floors: List[Floor], floor_plan_metadata: Optional[dict]) -> List[Floor]:
    """
    Roadmap hook: reconcile point-cloud floor bands with declared storey
    heights/names from an ingested BIM/floor-plan file. Not required for the
    hackathon MVP (uniform floor_height_m is a reasonable synthetic-data
    assumption) but kept as an explicit seam so real floor plans slot in
    without changing segment_floors()'s call signature.
    """
    if not floor_plan_metadata:
        return floors
    raise NotImplementedError("floor-plan alignment is roadmap scope — see Section 7")


def delineate_units(
    floor: Floor,
    envelope: BuildingEnvelope,
    unit_layout: Optional[List[dict]] = None,
) -> List[Unit]:
    """
    Rule-based polygon splitting: divide a floor's footprint into units.

    If `unit_layout` is supplied (from an ingested floor plan: list of
    {unit_id, space_class, rights_code, footprint}), use it directly. Otherwise
    fall back to a simple deterministic grid split of the building footprint —
    good enough to demo the pipeline end-to-end on the synthetic dataset.
    """
    if unit_layout:
        return [
            Unit(
                unit_id=u["unit_id"],
                floor_z_level=floor.z_level,
                space_class=u.get("space_class", "V"),
                rights_code=u.get("rights_code", "PRV"),
                footprint=u["footprint"],
                z_min=floor.z_min,
                z_max=floor.z_max,
            )
            for u in unit_layout
        ]

    poly = np.array(envelope.footprint)
    x_min, y_min = poly.min(axis=0)
    x_max, y_max = poly.max(axis=0)
    mid_x = (x_min + x_max) / 2

    # deterministic two-unit split (left/right) plus a shared corridor strip,
    # matching the "at least private + common" demo requirement in Section 13
    units = [
        Unit(
            unit_id=f"A{floor.z_level}01",
            floor_z_level=floor.z_level,
            space_class="V",
            rights_code="PRV",
            footprint=[(x_min, y_min), (mid_x - 0.5, y_min), (mid_x - 0.5, y_max), (x_min, y_max)],
            z_min=floor.z_min,
            z_max=floor.z_max,
        ),
        Unit(
            unit_id=f"A{floor.z_level}02",
            floor_z_level=floor.z_level,
            space_class="V",
            rights_code="PRV",
            footprint=[(mid_x + 0.5, y_min), (x_max, y_min), (x_max, y_max), (mid_x + 0.5, y_max)],
            z_min=floor.z_min,
            z_max=floor.z_max,
        ),
        Unit(
            unit_id=f"COR{floor.z_level}",
            floor_z_level=floor.z_level,
            space_class="V",
            rights_code="COM",
            footprint=[(mid_x - 0.5, y_min), (mid_x + 0.5, y_min), (mid_x + 0.5, y_max), (mid_x - 0.5, y_max)],
            z_min=floor.z_min,
            z_max=floor.z_max,
        ),
    ]
    logger.info("Delineated %d units on floor %s", len(units), floor.z_level)
    return units


if __name__ == "__main__":
    from processing.building_extractor import extract_building, generate_synthetic_building

    logging.basicConfig(level=logging.INFO)
    env = extract_building(generate_synthetic_building())
    floors = segment_floors(env)
    for f in floors:
        units = delineate_units(f, env)
        print(f"{f.z_level}: {[u.unit_id for u in units]}")
