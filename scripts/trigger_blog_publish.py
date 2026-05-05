"""기존 approved/ 의 landing_copy 결과물 → blog_publisher brief 일괄 생성.

사용 시점:
    회원님이 *기존 코스의 landing_copy*를 *지금 즉시* 티스토리에 임시저장
    하고 싶을 때. 캐스케이드로 자동 발주되지 않은 옛 코스도 한 번에 처리.

흐름:
    1. content/approved/*.json 중 kind=='landing_copy' 모두 검색
    2. course_id별로 *가장 최근* 1건만 (중복 게시 방지)
    3. blog_publisher brief을 briefs/에 저장
    4. 데몬이 다음 사이클(60초)에 자동 처리 → 티스토리 임시저장

실행:
    .venv/bin/python scripts/trigger_blog_publish.py
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

# .env 로드
try:
    from dotenv import load_dotenv
    load_dotenv(REPO_ROOT / ".env")
except ImportError:
    pass

APPROVED_DIR = REPO_ROOT / "content" / "approved"
BRIEFS_DIR = REPO_ROOT / "briefs"


def main():
    BRIEFS_DIR.mkdir(parents=True, exist_ok=True)

    # 1) landing_copy 검색 + course별 최신 1건
    by_course = {}
    for f in sorted(APPROVED_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if d.get("kind") != "landing_copy":
            continue
        cid = d.get("course_id")
        if not cid or cid in by_course:
            continue
        by_course[cid] = d

    print(f"발견된 unique 코스 (landing_copy 보유): {len(by_course)}개")
    for cid in by_course:
        print(f"  • {cid}")

    if not by_course:
        print("\nlanding_copy 결과물이 없습니다. cascade가 먼저 실행돼야 합니다.")
        return

    # 2) 각 course의 curriculum도 찾기 (blog post 본문 보강용)
    curriculum_by_course = {}
    for f in APPROVED_DIR.glob("*.json"):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if d.get("kind") != "curriculum_outline":
            continue
        cid = d.get("course_id")
        if cid and cid not in curriculum_by_course:
            curriculum_by_course[cid] = (d.get("meta") or {}).get("raw") or {}

    # 3) blog_publisher brief 생성
    ts = int(time.time())
    n = 0
    for cid, landing in by_course.items():
        landing_raw = (landing.get("meta") or {}).get("raw") or {}
        curriculum_raw = curriculum_by_course.get(cid, {})

        course_title = curriculum_raw.get("title") or landing.get("title", cid)

        brief = {
            "agent": "blog_publisher",
            "brief": {
                "course_id": cid,
                "course_title": course_title,
                "landing_copy": landing_raw,
                "curriculum": curriculum_raw,
            },
        }
        brief_path = BRIEFS_DIR / f"manual-blog-{cid}-{ts}.json"
        brief_path.write_text(
            json.dumps(brief, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"  ✓ {brief_path.name} 생성")
        n += 1

    print(f"\n총 {n}개 blog_publisher brief 큐에 등록됨")
    print("데몬이 다음 사이클(60초)에 자동 처리 → 티스토리 임시저장")
    print(f"확인: https://jejumomdad.tistory.com/manage/posts")


if __name__ == "__main__":
    main()
