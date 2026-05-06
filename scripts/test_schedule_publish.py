"""티스토리 *예약 발행* 검증 — claude-intro-email 1개를 +1시간 후 예약.

검증 항목:
  1. 모달의 '예약' 토글 클릭됨
  2. datepicker input/select 덤프 — 셀렉터 학습
  3. 시각 입력 + 공개 발행 클릭
  4. final URL 검증 (예약 글 = /manage/posts/ 또는 entry/...)

실행:
    .venv/bin/python scripts/test_schedule_publish.py
"""
from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
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

# TISTORY_SKIP은 무시 — 검증 모드
os.environ.pop("TISTORY_SKIP", None)

APPROVED = REPO_ROOT / "content" / "approved"
COURSE = "claude-intro-email"


def find_blog_post():
    """approved/에서 해당 코스의 blog_post 가져오기."""
    for f in sorted(APPROVED.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if d.get("kind") == "blog_post" and d.get("course_id") == COURSE:
            return d
    return None


def main():
    bp = find_blog_post()
    if not bp:
        print(f"✗ {COURSE} blog_post 없음")
        sys.exit(1)

    meta = bp.get("meta") or {}
    title = meta.get("title") or bp.get("title") or COURSE
    body_html = meta.get("body_html") or ""

    if not body_html:
        print(f"✗ body_html 비어있음")
        sys.exit(1)

    # KST 기준 +1시간 후 (분 단위 0으로 절삭하면 입력 단순)
    kst = timezone(timedelta(hours=9))
    schedule_at = (datetime.now(kst) + timedelta(hours=1)).replace(second=0, microsecond=0)

    print(f"\n{'='*60}")
    print(f"📅 예약 발행 검증")
    print(f"{'='*60}")
    print(f"코스: {COURSE}")
    print(f"제목: {title[:60]}")
    print(f"본문: {len(body_html)} chars")
    print(f"예약 시각: {schedule_at.strftime('%Y-%m-%d %H:%M')} (KST, +1h)")
    print(f"{'='*60}\n")

    blog = os.environ.get("TISTORY_BLOG", "jejumomdad")

    from tistory_helpers.publisher import publish_post

    try:
        url = publish_post(
            blog=blog,
            title=f"[예약 검증] {title}",
            body_html=body_html,
            tags=["예약발행", "검증", COURSE[:20]],
            publish=True,
            schedule_at=schedule_at,
            headless=False,  # 진단 — 브라우저 보임
        )
        print(f"\n✅ 검증 완료")
        print(f"   final URL: {url}")
        print(f"\n다음 확인:")
        print(f"  → https://{blog}.tistory.com/manage/posts (예약 탭)")
        print(f"  → 예약 시각 {schedule_at.strftime('%H:%M')} 글 확인")
        print(f"  → 디버그 스크린샷: content/state/tistory_debug/")
    except Exception as e:
        print(f"\n❌ 실패: {e}")
        print(f"   디버그 스크린샷: content/state/tistory_debug/")
        print(f"   특히 5b-schedule-set.png 봐서 datepicker 상태 확인")
        sys.exit(1)


if __name__ == "__main__":
    main()
