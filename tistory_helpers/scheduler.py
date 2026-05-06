"""티스토리 예약 발행 시각 자동 분산기.

티스토리 일일 발행 한도 = 15개. 24시간 / 15 ≈ 1.6h 간격.
실제로는 *오전 9시 ~ 23시* 14시간 활동대에 분산이 자연스러움 → 약 60분 간격.

상태:
    content/state/publish_schedule.json
    {
      "last_scheduled_at": "2026-05-06T15:00:00+09:00",
      "today": "2026-05-06",
      "today_count": 5
    }

사용:
    from tistory_helpers.scheduler import next_publish_slot
    schedule_at = next_publish_slot()  # 자동으로 다음 슬롯 datetime 반환
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEDULE_FILE = REPO_ROOT / "content" / "state" / "publish_schedule.json"

KST = timezone(timedelta(hours=9))

# 정책 — 티스토리 한도 + 자연스러운 발행 시간대
DAILY_LIMIT = 15           # 티스토리 하루 발행 한도
SLOT_INTERVAL_MIN = 60     # 슬롯 간 60분 간격
ACTIVE_HOUR_START = 9      # 오전 9시부터
ACTIVE_HOUR_END = 23       # 밤 11시까지 (활동 시간대)
MIN_LEAD_MIN = 30          # 지금부터 최소 30분 후

log = logging.getLogger("publish_scheduler")


def _load() -> dict:
    if SCHEDULE_FILE.exists():
        try:
            return json.loads(SCHEDULE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"last_scheduled_at": None, "today": None, "today_count": 0}


def _save(state: dict) -> None:
    SCHEDULE_FILE.parent.mkdir(parents=True, exist_ok=True)
    SCHEDULE_FILE.write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _today_kst() -> str:
    return datetime.now(KST).strftime("%Y-%m-%d")


def next_publish_slot() -> Optional[datetime]:
    """다음 예약 발행 시각 계산 (KST timezone-aware datetime).

    Returns:
        datetime — 다음 슬롯 시각 (KST)
        None    — 오늘+내일 한도 다 찼고 모레 이상 미루는 게 부적절할 때
    """
    state = _load()
    today = _today_kst()

    # 날짜 바뀌었으면 카운터 리셋
    if state.get("today") != today:
        state = {"last_scheduled_at": None, "today": today, "today_count": 0}

    now_kst = datetime.now(KST)
    earliest = now_kst + timedelta(minutes=MIN_LEAD_MIN)

    # 마지막 예약 시각 + interval
    last_str = state.get("last_scheduled_at")
    if last_str:
        try:
            last = datetime.fromisoformat(last_str)
            candidate = last + timedelta(minutes=SLOT_INTERVAL_MIN)
        except Exception:
            candidate = earliest
    else:
        # 오늘 첫 예약 — 다음 정시 시각
        candidate = now_kst.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)

    # earliest 보다 이전이면 earliest로
    if candidate < earliest:
        candidate = earliest

    # 분 단위 정리 (정시 또는 30분)
    candidate = candidate.replace(second=0, microsecond=0)
    if candidate.minute >= 30:
        candidate = candidate.replace(minute=30)
    else:
        candidate = candidate.replace(minute=0)

    # 활동 시간대 보정
    while True:
        h = candidate.hour
        # 오늘 한도 초과 시 다음날로
        if state["today_count"] >= DAILY_LIMIT:
            tomorrow = (candidate.date() + timedelta(days=1))
            candidate = datetime.combine(tomorrow, datetime.min.time(), tzinfo=KST)
            candidate = candidate.replace(hour=ACTIVE_HOUR_START)
            state = {"last_scheduled_at": None, "today": tomorrow.strftime("%Y-%m-%d"), "today_count": 0}
            continue
        # 활동 시간 밖이면 다음 활동 시작 시점으로
        if h < ACTIVE_HOUR_START:
            candidate = candidate.replace(hour=ACTIVE_HOUR_START, minute=0)
        elif h >= ACTIVE_HOUR_END:
            tomorrow = candidate.date() + timedelta(days=1)
            candidate = datetime.combine(tomorrow, datetime.min.time(), tzinfo=KST)
            candidate = candidate.replace(hour=ACTIVE_HOUR_START)
            state = {"last_scheduled_at": None, "today": tomorrow.strftime("%Y-%m-%d"), "today_count": 0}
            continue
        break

    log.info("[scheduler] 다음 슬롯: %s (오늘 %d/%d)",
             candidate.strftime("%Y-%m-%d %H:%M"),
             state["today_count"] + 1, DAILY_LIMIT)
    return candidate


def commit_slot(at: datetime) -> None:
    """슬롯 사용 확정 — state에 기록."""
    if at.tzinfo is None:
        at = at.replace(tzinfo=KST)
    today = at.strftime("%Y-%m-%d")
    state = _load()
    if state.get("today") != today:
        state = {"today": today, "today_count": 0, "last_scheduled_at": None}
    state["last_scheduled_at"] = at.isoformat()
    state["today_count"] = state.get("today_count", 0) + 1
    _save(state)
    log.info("[scheduler] 슬롯 확정: %s (오늘 %d/%d)",
             at.strftime("%H:%M"), state["today_count"], DAILY_LIMIT)


if __name__ == "__main__":
    # CLI 테스트 — 다음 5개 슬롯 시뮬레이션
    logging.basicConfig(level="INFO", format="%(message)s")
    print("=== 다음 5개 슬롯 시뮬레이션 ===")
    for i in range(5):
        slot = next_publish_slot()
        if slot:
            print(f"  [{i+1}] {slot.strftime('%Y-%m-%d %H:%M')} (KST)")
            commit_slot(slot)
        else:
            print(f"  [{i+1}] 슬롯 없음")
            break
