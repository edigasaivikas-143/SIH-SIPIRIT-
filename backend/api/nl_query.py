"""
Module H — Natural-language query layer.

Per the project guide (Section 7): "Keep the query scope narrow and
schema-constrained (structured query generation, not open-ended chat) so
it stays reliable live." This module does NOT do open-ended chat — it
maps a plain-language question onto a small, fixed set of structured
query intents against the space_3d / rights / validation schema, then
executes that structured query. An LLM (if configured) is only used to
pick the intent + fill slots, never to answer freely.
"""

import os
import re
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from api.routes import get_demo_store

router = APIRouter(tags=["nl-query"])

ANTHROPIC_MODEL = os.getenv("ULPIN_NL_MODEL", "claude-sonnet-4-6")


class NLQueryIn(BaseModel):
    question: str
    parcel_id: Optional[str] = None  # scope the query to one parcel, if known


class NLQueryOut(BaseModel):
    question: str
    matched_intent: str
    sql_equivalent: str
    results: list


# ------------------------------------------------------------------
# Schema-constrained intents. Each pattern maps a phrasing to one
# structured query over the demo store (mirrors what a real PostGIS
# query would filter on).
# ------------------------------------------------------------------
INTENT_PATTERNS = [
    (re.compile(r"conflict|dispute|contested|overlap", re.I), "spaces_with_conflicts"),
    (re.compile(r"basement|underground|utility|tunnel|corridor", re.I), "underground_spaces"),
    (re.compile(r"terrace|roof|common|shared", re.I), "common_spaces"),
    (re.compile(r"air.?right|elevated|overhead", re.I), "elevated_spaces"),
    (re.compile(r"unclear ownership|missing rights|no rights", re.I), "spaces_missing_active_rights"),
    (re.compile(r"low confidence|uncertain", re.I), "low_confidence_spaces"),
]


def _match_intent(question: str) -> str:
    for pattern, intent in INTENT_PATTERNS:
        if pattern.search(question):
            return intent
    return "list_all_spaces"


def _execute(intent: str, parcel_id: Optional[str]) -> tuple[list, str]:
    store = get_demo_store()
    spaces = list(store["spaces"].values())
    if parcel_id:
        spaces = [s for s in spaces if s["parcel_id"] == parcel_id]

    if intent == "spaces_with_conflicts":
        conflicted_ids = {
            v["parcel_3d_id"] for v in store["validations"].values()
            if v["result"] == "FAIL" and v["rule"] == "RIGHTS_CONSISTENCY"
        }
        results = [s for s in spaces if s["parcel_3d_id"] in conflicted_ids]
        sql = ("SELECT s.* FROM space_3d s JOIN validation v ON v.parcel_3d_id = s.parcel_3d_id "
               "WHERE v.rule = 'RIGHTS_CONSISTENCY' AND v.result = 'FAIL'")

    elif intent == "underground_spaces":
        results = [s for s in spaces if s["space_class"] == "U"]
        sql = "SELECT * FROM space_3d WHERE space_class = 'U'"

    elif intent == "common_spaces":
        results = [s for s in spaces if s["rights_code"] == "COM"]
        sql = "SELECT * FROM space_3d WHERE rights_code = 'COM'"

    elif intent == "elevated_spaces":
        results = [s for s in spaces if s["space_class"] == "E"]
        sql = "SELECT * FROM space_3d WHERE space_class = 'E'"

    elif intent == "spaces_missing_active_rights":
        active_ids = {r["parcel_3d_id"] for r in store["rights"].values() if r["active"]}
        results = [s for s in spaces if s["parcel_3d_id"] not in active_ids]
        sql = ("SELECT s.* FROM space_3d s LEFT JOIN rights r "
               "ON r.parcel_3d_id = s.parcel_3d_id AND r.active "
               "WHERE r.right_id IS NULL")

    elif intent == "low_confidence_spaces":
        results = [s for s in spaces if (s.get("confidence") or 100) < 70]
        sql = "SELECT * FROM space_3d WHERE confidence < 70"

    else:
        results = spaces
        sql = "SELECT * FROM space_3d"

    return results, sql


@router.post("", response_model=NLQueryOut)
async def natural_language_query(payload: NLQueryIn):
    intent = _match_intent(payload.question)
    results, sql = _execute(intent, payload.parcel_id)
    return NLQueryOut(
        question=payload.question,
        matched_intent=intent,
        sql_equivalent=sql,
        results=results,
    )
