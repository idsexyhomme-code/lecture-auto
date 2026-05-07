"""기존 blog_post가 있는 모든 코스에 대해 blog_publisher republish brief 생성.

데몬(long_poll)이 picks up → 새 system_prompt(20년 경력 블로그 마케터 톤)로 본문 재생성 → 티스토리 자동 발행.

생성 위치: briefs/cascade-blog-{course_id}-blog_publisher-{ts}-{i}.json
"""
from __future__ import annotations
import json, glob, os, time, sys
from pathlib import Path
from collections import defaultdict

REPO = Path(__file__).resolve().parent.parent
BRIEFS = REPO / "briefs"
APPROVED = REPO / "content" / "approved"


def latest_by_kind(kind: str) -> dict[str, dict]:
    """course_id -> 가장 최신 approved JSON of given kind."""
    out = {}
    for f in APPROVED.glob("*.json"):
        try:
            d = json.load(open(f))
        except Exception:
            continue
        if d.get("kind") != kind:
            continue
        cid = d.get("course_id")
        if not cid:
            continue
        ts = d.get("created_at") or ""
        if cid not in out or ts > out[cid].get("created_at", ""):
            out[cid] = d
    return out


def collect_blog_courses() -> set[str]:
    s = set()
    for f in APPROVED.glob("*.json"):
        try:
            d = json.load(open(f))
        except Exception:
            continue
        if d.get("kind") == "blog_post" and d.get("course_id"):
            s.add(d["course_id"])
    return s


def main():
    landings = latest_by_kind("landing_copy")
    currs = latest_by_kind("curriculum_outline")
    courses = collect_blog_courses()
    print(f"blog_post 보유 코스: {len(courses)}")

    BRIEFS.mkdir(parents=True, exist_ok=True)
    base_ts = int(time.time())
    written = 0
    for i, cid in enumerate(sorted(courses)):
        landing = landings.get(cid, {})
        curr = currs.get(cid, {})
        # extract relevant raw fields
        landing_raw = landing.get("data") or landing.get("raw") or landing
        if isinstance(landing_raw, dict) and "raw" in landing_raw:
            landing_raw = landing_raw["raw"]
        curr_raw = curr.get("data") or curr.get("raw") or curr
        if isinstance(curr_raw, dict) and "raw" in curr_raw:
            curr_raw = curr_raw["raw"]

        course_title = (
            (landing_raw or {}).get("course_title")
            or (curr_raw or {}).get("course_title")
            or cid
        )
        # blog_publisher.run expects: course_id, course_title, landing_copy, curriculum
        brief_obj = {
            "agent": "blog_publisher",
            "brief": {
                "course_id": cid,
                "course_title": course_title,
                "landing_copy": {"raw": landing_raw} if landing_raw else {},
                "curriculum": curr_raw or {},
                "_republish_reason": "human_tone_v2_2026-05-08",
            },
        }
        ts = base_ts + i  # unique
        fname = f"cascade-blog-{cid}-blog_publisher-{ts}-0.json"
        path = BRIEFS / fname
        path.write_text(json.dumps(brief_obj, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  ✓ {fname}")
        written += 1

    print(f"\n=== {written} briefs written to {BRIEFS} ===")
    print("데몬이 5초 내에 픽업해서 순차 처리합니다 (한 시간 한도 15편).")


if __name__ == "__main__":
    main()
