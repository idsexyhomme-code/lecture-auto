"""모든 미발행 blog_post → 자동 분산 예약 발행.

흐름:
  1. content/approved/에서 kind=blog_post 산출물 수집 (course_id별 최신)
  2. 이미 published/scheduled 인 것 스킵
  3. 각 코스마다 next_publish_slot()로 시각 자동 분산 (12:00, 13:00, 14:00 ...)
  4. publish_post(schedule_at=...) 호출 → 티스토리 예약 발행
  5. commit_slot() + meta 업데이트 (tistory_status='scheduled')

실행:
    .venv/bin/python scripts/publish_all_pending.py
"""
from __future__ import annotations

import json
import logging
import os
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(name)s] %(message)s",
    stream=sys.stdout,
    force=True,
)

try:
    from dotenv import load_dotenv
    load_dotenv(REPO_ROOT / ".env")
except ImportError:
    pass

# TISTORY_SKIP 강제 해제 (검증 모드)
os.environ.pop("TISTORY_SKIP", None)

from tistory_helpers.publisher import publish_post
from tistory_helpers.scheduler import next_publish_slot, commit_slot

APPROVED = REPO_ROOT / "content" / "approved"


def collect_pending_blog_posts() -> list[tuple[str, dict, Path]]:
    """course_id별 최신 blog_post 모음 — 미발행만."""
    seen = set()
    todo = []
    for f in sorted(APPROVED.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if d.get("kind") != "blog_post":
            continue
        cid = d.get("course_id")
        if not cid or cid in seen:
            continue
        seen.add(cid)

        meta = d.get("meta") or {}
        body_html = meta.get("body_html") or ""
        if not body_html:
            print(f"  skip {cid}: body_html 비어있음")
            continue

        # 이미 예약/발행됨 스킵
        status = meta.get("tistory_status", "")
        url = meta.get("tistory_url") or ""
        if status in ("scheduled",) and meta.get("scheduled_at"):
            print(f"  skip {cid}: 이미 예약됨 ({meta.get('scheduled_at', '')[:16]})")
            continue
        if status == "draft" and url and "manage/posts" in url:
            # 어제 발행된 글 (final URL이 /manage/posts/) — 이미 라이브
            print(f"  skip {cid}: 이미 발행됨 (어제)")
            continue

        todo.append((cid, d, f))
    return todo


def main():
    todo = collect_pending_blog_posts()

    print(f"\n{'='*60}")
    print(f"📋 발행 대상: {len(todo)}개")
    print(f"{'='*60}")
    for cid, d, _ in todo:
        title = (d.get("meta") or {}).get("title", cid)
        print(f"  · {cid}: {title[:50]}")
    print(f"{'='*60}\n")

    if not todo:
        print("발행할 글 없음.")
        return

    blog = os.environ.get("TISTORY_BLOG", "jejumomdad")
    results = []
    failures = []

    for i, (cid, d, file_path) in enumerate(todo, 1):
        meta = d.get("meta") or {}
        title = meta.get("title") or d.get("title") or cid
        body_html = meta.get("body_html") or ""

        schedule_at = next_publish_slot()
        if not schedule_at:
            print(f"\n[{i}/{len(todo)}] ✗ {cid}: 더 이상 슬롯 없음 — 중단")
            break

        print(f"\n[{i}/{len(todo)}] {cid}")
        print(f"  제목: {title[:60]}")
        print(f"  예약: {schedule_at.strftime('%Y-%m-%d %H:%M')} (KST)")

        try:
            url = publish_post(
                blog=blog,
                title=title,
                body_html=body_html,
                tags=["Claude", "1인 사업가", "코어 캠퍼스", cid[:20]],
                publish=True,
                schedule_at=schedule_at,
                headless=False,
            )
            commit_slot(schedule_at)

            # meta 업데이트 — 다음 실행 시 이 글 스킵하도록
            meta["tistory_url"] = url
            meta["tistory_status"] = "scheduled"
            meta["scheduled_at"] = schedule_at.isoformat()
            d["meta"] = meta
            file_path.write_text(
                json.dumps(d, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            print(f"  ✅ 예약 완료: {url}")
            results.append((cid, schedule_at, url))
        except Exception as e:
            print(f"  ❌ 실패: {e}")
            failures.append((cid, str(e)))

        # 부하 방지 — 코스 간 3초 대기
        time.sleep(3)

    # 최종 정리
    print(f"\n\n{'='*60}")
    print(f"📊 결과 — 성공 {len(results)}개 / 실패 {len(failures)}개")
    print(f"{'='*60}")
    if results:
        print("\n✅ 예약 발행 완료 시각:")
        for cid, at, _ in sorted(results, key=lambda x: x[1]):
            print(f"  {at.strftime('%H:%M')} — {cid}")
    if failures:
        print("\n❌ 실패 (수동 재시도 필요):")
        for cid, err in failures:
            print(f"  {cid}: {err[:80]}")
    print()
    print(f"확인: https://{blog}.tistory.com/manage/posts (예약 탭)")


if __name__ == "__main__":
    main()
