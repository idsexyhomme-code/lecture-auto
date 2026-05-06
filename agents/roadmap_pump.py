"""roadmap.json 자동 펌프 — N시간마다 새 코스 brief 1개 자동 발주.

흐름:
    1. roadmap.json의 status='planned' 코스 중 priority 가장 낮은 거 1개 선택
    2. curriculum brief 작성 → briefs/{ts}-roadmap-{cid}.json
    3. roadmap.json 상태 갱신: status='proposed', log에 기록
    4. content/state/roadmap_pump.json에 last_pump_at 저장

로직:
    long_poll 데몬이 매 사이클(5초)마다 should_pump_now() 호출.
    interval (default 6시간) 안 지났으면 즉시 None 반환 (무해).
    interval 지났으면 새 brief 1개 발주 → 데몬이 잡아서 cascade.

설정 (roadmap.json):
    "schedule": {
        "interval_hours": 6,        # N시간마다 (default 6)
        "max_per_day": 4            # 일일 최대 (안전장치)
    }
"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
ROADMAP_FILE = REPO_ROOT / "roadmap.json"
PUMP_STATE = REPO_ROOT / "content" / "state" / "roadmap_pump.json"
BRIEFS_DIR = REPO_ROOT / "briefs"

KST = timezone(timedelta(hours=9))
DEFAULT_INTERVAL_HOURS = 6
DEFAULT_MAX_PER_DAY = 4

log = logging.getLogger("roadmap_pump")


def _load_state() -> dict:
    if PUMP_STATE.exists():
        try:
            return json.loads(PUMP_STATE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"last_pump_at": None, "today": None, "today_count": 0}


def _save_state(state: dict) -> None:
    PUMP_STATE.parent.mkdir(parents=True, exist_ok=True)
    PUMP_STATE.write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _load_roadmap() -> dict:
    if not ROADMAP_FILE.exists():
        return {"courses": [], "log": []}
    try:
        return json.loads(ROADMAP_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        log.error("[roadmap_pump] roadmap.json 파싱 실패: %s", e)
        return {"courses": [], "log": []}


def _save_roadmap(d: dict) -> None:
    ROADMAP_FILE.write_text(
        json.dumps(d, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _interval_and_limit() -> tuple[int, int]:
    rm = _load_roadmap()
    sched = rm.get("schedule") or {}
    h = sched.get("interval_hours") or DEFAULT_INTERVAL_HOURS
    m = sched.get("max_per_day") or DEFAULT_MAX_PER_DAY
    return int(h) if isinstance(h, (int, float)) else DEFAULT_INTERVAL_HOURS, \
           int(m) if isinstance(m, (int, float)) else DEFAULT_MAX_PER_DAY


def should_pump_now() -> bool:
    """현재 시점에 새 코스 발주해야 하는지 — interval + 일일 한도 체크."""
    state = _load_state()
    interval_h, max_day = _interval_and_limit()
    now = datetime.now(KST)
    today = now.strftime("%Y-%m-%d")

    # 날짜 바뀌면 카운터 리셋
    if state.get("today") != today:
        state = {"last_pump_at": state.get("last_pump_at"), "today": today, "today_count": 0}
        _save_state(state)

    # 일일 한도 체크
    if state.get("today_count", 0) >= max_day:
        return False

    # interval 체크
    last = state.get("last_pump_at")
    if not last:
        return True
    try:
        last_dt = datetime.fromisoformat(last)
        if last_dt.tzinfo is None:
            last_dt = last_dt.replace(tzinfo=KST)
    except Exception:
        return True

    return (now - last_dt) >= timedelta(hours=interval_h)


def pump_next() -> Optional[Path]:
    """status='planned' 중 priority 가장 낮은 코스 1개 → curriculum brief 발주."""
    if not should_pump_now():
        return None

    rm = _load_roadmap()
    courses = rm.get("courses") or []
    planned = [c for c in courses if c.get("status") == "planned"]
    if not planned:
        log.info("[roadmap_pump] 대기 큐 비어있음 — 모든 코스 처리됨")
        return None

    planned.sort(key=lambda c: c.get("priority", 999))
    pick = planned[0]

    cid = pick.get("course_id")
    if not cid:
        return None

    # curriculum brief 작성
    brief = {
        "agent": "curriculum",
        "brief": {
            "course_id": cid,
            "topic": pick.get("topic") or pick.get("title"),
            "audience": pick.get("audience", "1인 사업가"),
            "duration_weeks": pick.get("duration_weeks", 3),
            "lesson_count": pick.get("lesson_count", 6),
            "format": pick.get("format", "video"),
            "promises_hint": pick.get("promises_hint") or [],
        },
    }
    BRIEFS_DIR.mkdir(parents=True, exist_ok=True)
    ts = int(time.time())
    bp = BRIEFS_DIR / f"{ts}-roadmap-{cid}.json"
    bp.write_text(
        json.dumps(brief, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # roadmap.json 상태 갱신
    now_iso = datetime.now(KST).isoformat()
    for c in courses:
        if c.get("course_id") == cid:
            c["status"] = "proposed"
            c["proposed_at"] = now_iso
    rm["log"] = (rm.get("log") or []) + [{
        "course_id": cid,
        "action": "auto_pump",
        "at": now_iso,
        "brief_file": bp.name,
    }]
    _save_roadmap(rm)

    # pump state 갱신
    state = _load_state()
    today = datetime.now(KST).strftime("%Y-%m-%d")
    if state.get("today") != today:
        state = {"today": today, "today_count": 0}
    state["last_pump_at"] = now_iso
    state["today_count"] = state.get("today_count", 0) + 1
    _save_state(state)

    log.info("[roadmap_pump] ✓ 신규 코스 자동 발주: %s (brief: %s, 오늘 %d번째)",
             cid, bp.name, state["today_count"])
    return bp


if __name__ == "__main__":
    # CLI 테스트 — 즉시 펌프 시도
    logging.basicConfig(level="INFO", format="%(message)s")
    interval_h, max_day = _interval_and_limit()
    state = _load_state()
    print(f"=== roadmap_pump 진단 ===")
    print(f"  interval: {interval_h}시간마다, 일일 최대: {max_day}개")
    print(f"  last_pump_at: {state.get('last_pump_at') or '(없음)'}")
    print(f"  today_count: {state.get('today_count', 0)}/{max_day}")
    print(f"  should_pump_now: {should_pump_now()}")
    print()
    rm = _load_roadmap()
    planned = [c for c in (rm.get('courses') or []) if c.get('status') == 'planned']
    proposed = [c for c in (rm.get('courses') or []) if c.get('status') == 'proposed']
    print(f"  planned (대기): {len(planned)}개")
    print(f"  proposed (발주됨): {len(proposed)}개")
    if planned:
        print(f"  다음 발주 후보: {planned[0]['course_id']} (priority {planned[0].get('priority')})")
    print()
    bp = pump_next()
    if bp:
        print(f"✓ 발주 완료: {bp.name}")
    else:
        print("(발주 안 함 — interval 안 지났거나 큐 비어있음)")
