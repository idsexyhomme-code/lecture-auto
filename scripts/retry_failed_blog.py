"""실패한 blog_post 일괄 재발행 — 기존 본문 재사용 (Claude API 비용 0).

전제: content/state/tistory_session.json이 *최신*이어야 함.
  → 먼저 login-tistory.command 더블클릭으로 세션 재캡처.

사용:
    python scripts/retry_failed_blog.py --dry-run        # 대상만 확인
    python scripts/retry_failed_blog.py                  # 실제 재발행 (즉시 발행)
    python scripts/retry_failed_blog.py --schedule       # 예약 분산 (publish_schedule)
    python scripts/retry_failed_blog.py --limit 5        # 5건만

흐름:
1. content/approved 에서 tistory_status=failed 인 blog_post 추출
2. 중복 제거 (course_id 기준 1개씩 — 같은 코스 여러번 실패 시 최신만)
3. 기존 body_html · title 재사용
4. tistory_helpers.publisher.publish_post() 직접 호출
5. 성공 시 meta.tistory_status=draft·scheduled / tistory_url 갱신
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

try:
    from dotenv import load_dotenv
    load_dotenv(REPO / ".env")
except Exception:
    pass

log = logging.getLogger("retry_failed_blog")
logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"),
                    format="%(asctime)s [%(name)s] %(message)s")


def find_failed_posts() -> list[dict]:
    """실패한 blog_post 추출 + course_id별 최신만."""
    by_course: dict[str, dict] = {}
    for f in (REPO / "content" / "approved").glob("*.json"):
        try:
            d = json.load(open(f))
        except Exception:
            continue
        if d.get("kind") != "blog_post":
            continue
        m = d.get("meta") or {}
        if m.get("tistory_status") != "failed":
            continue
        if not m.get("body_html"):
            continue  # 본문 없으면 재발행 불가

        cid = d.get("course_id", "unknown")
        mtime = f.stat().st_mtime
        existing = by_course.get(cid)
        if existing is None or mtime > existing["__mtime"]:
            by_course[cid] = {
                "__path": f,
                "__mtime": mtime,
                "course_id": cid,
                "title": d.get("title", "").replace("[블로그 임시저장] ", ""),
                "body_html": m.get("body_html", ""),
                "agent_result": d,
            }
    return list(by_course.values())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--schedule", action="store_true", help="예약 시각 분산")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    posts = find_failed_posts()
    posts.sort(key=lambda x: x["__mtime"], reverse=True)

    print(f"=== 재발행 대상: {len(posts)}개 (course_id별 1개씩) ===\n")
    for i, p in enumerate(posts, 1):
        print(f"  {i:2}. [{p['course_id']}] {p['title'][:55]}")

    if args.limit > 0:
        posts = posts[: args.limit]
        print(f"\nlimit 적용: {len(posts)}개만")

    if args.dry_run:
        print("\n→ --dry-run 모드 — 실제 발행 안 함")
        return

    if not posts:
        print("재발행 대상 없음.")
        return

    print()
    print("실제 재발행 시작 — 한 건당 약 30~60초")
    print()

    # publish_post import
    try:
        from tistory_helpers.publisher import publish_post
    except Exception as e:
        log.error("publisher import 실패: %s", e)
        return

    if args.schedule:
        try:
            from tistory_helpers.scheduler import next_publish_slot, commit_slot
        except Exception:
            args.schedule = False
            log.warning("scheduler 없음 — 즉시 발행으로 진행")

    success = 0
    fail = 0
    for i, p in enumerate(posts, 1):
        print(f"[{i}/{len(posts)}] {p['course_id']}: {p['title'][:50]}")
        try:
            schedule_at = None
            if args.schedule:
                schedule_at = next_publish_slot()
                if schedule_at:
                    print(f"    예약 시각: {schedule_at.strftime('%Y-%m-%d %H:%M (KST)')}")

            published_url = publish_post(
                title=p["title"],
                body_html=p["body_html"],
                category=None,
                tags=None,
                schedule_at=schedule_at,
            )

            if published_url:
                print(f"    ✓ 성공: {published_url}")
                success += 1
                # meta 갱신
                d = p["agent_result"]
                d.setdefault("meta", {})
                d["meta"]["tistory_url"] = published_url
                d["meta"]["tistory_status"] = "scheduled" if schedule_at else "draft"
                if schedule_at:
                    d["meta"]["scheduled_at"] = schedule_at.isoformat()
                    if args.schedule:
                        try:
                            commit_slot(schedule_at)
                        except Exception:
                            pass
                p["__path"].write_text(
                    json.dumps(d, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
            else:
                print(f"    ✗ 실패 (URL 없음)")
                fail += 1
        except Exception as e:
            print(f"    ✗ 예외: {type(e).__name__}: {str(e)[:200]}")
            fail += 1
            # 세션 만료라면 더 이상 시도 X
            if "세션" in str(e) or "login" in str(e).lower():
                print()
                print("⚠️ 세션 만료 감지 — login-tistory.command 더블클릭 후 다시 실행해 주세요.")
                break

        # rate limit 보호
        time.sleep(2)

    print()
    print(f"=== 완료 ===")
    print(f"  성공: {success}개")
    print(f"  실패: {fail}개")


if __name__ == "__main__":
    main()
