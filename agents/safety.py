"""안전장치 — 자동 캐스케이드의 폭주를 막는 가드레일.

자동화 레벨이 올라갈수록 *사람이 안 보는 사이* 시스템이 무한루프에 빠지거나
비용을 폭주시킬 위험이 커진다. 이 모듈이 그 위험을 제한한다.

기록되는 신호 (state/safety.json에 누적):
  - daily_brief_count: 오늘 처리한 brief 수
  - daily_agent_calls: 에이전트별 호출 횟수
  - daily_estimated_cost_usd: 누적 추정 비용 (Sonnet 가격표 기반)
  - last_reset_date: 일일 카운터 리셋 기준일 (UTC)

한도 초과 시:
  - 일일 brief 50개 → 처리 거부
  - 일일 추정 비용 $5 → 처리 거부
  - 같은 에이전트 5분 내 10회 → 일시 정지 (루프 방어)

각 한도는 .env로 오버라이드 가능 (SAFETY_*).
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path

from .base import STATE_DIR

log = logging.getLogger("safety")

SAFETY_FILE = STATE_DIR / "safety.json"

# 기본 한도 (env로 override 가능)
DEFAULT_LIMITS = {
    "daily_brief_max":         int(os.environ.get("SAFETY_DAILY_BRIEF_MAX", "50")),
    "daily_cost_usd_max":      float(os.environ.get("SAFETY_DAILY_COST_USD_MAX", "5.0")),
    "burst_window_minutes":    int(os.environ.get("SAFETY_BURST_WINDOW_MINUTES", "5")),
    "burst_max_per_agent":     int(os.environ.get("SAFETY_BURST_MAX_PER_AGENT", "10")),
}

# Sonnet 4.6 추정 가격 (USD per 1M tokens) — 보수적
COST_PER_1M_INPUT_USD = 3.0
COST_PER_1M_OUTPUT_USD = 15.0
# 대략적 평균 호출 = 입력 2K + 출력 4K → ~$0.066/호출
APPROX_USD_PER_CALL = 0.07


@dataclass
class SafetyState:
    last_reset_date: str = ""               # YYYY-MM-DD
    daily_brief_count: int = 0
    daily_agent_calls: dict = field(default_factory=dict)   # {agent: count}
    daily_estimated_cost_usd: float = 0.0
    recent_call_timestamps: list = field(default_factory=list)  # epoch sec
    paused: bool = False
    pause_reason: str = ""
    # AUTO 모드 — 모든 산출물에 대해 ✅ 클릭 없이 자동 승인 + 적용 + 캐스케이드.
    # 일일 한도·비용 한도는 여전히 작동 (자동 모드라도 한도 초과 시 정지).
    auto_mode: bool = False

    @classmethod
    def load(cls) -> "SafetyState":
        if not SAFETY_FILE.exists():
            return cls(last_reset_date=_today_utc())
        try:
            data = json.loads(SAFETY_FILE.read_text(encoding="utf-8"))
            keys = {f for f in cls.__dataclass_fields__}
            clean = {k: v for k, v in data.items() if k in keys}
            return cls(**clean)
        except Exception:
            return cls(last_reset_date=_today_utc())

    def save(self):
        SAFETY_FILE.parent.mkdir(parents=True, exist_ok=True)
        SAFETY_FILE.write_text(
            json.dumps(asdict(self), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def reset_if_new_day(self):
        today = _today_utc()
        if self.last_reset_date != today:
            log.info("[safety] new day — resetting daily counters")
            self.last_reset_date = today
            self.daily_brief_count = 0
            self.daily_agent_calls = {}
            self.daily_estimated_cost_usd = 0.0
            self.recent_call_timestamps = []
            # paused 플래그는 *유지* — 운영자가 명시적으로 풀어야 함

    def check_and_record(self, agent_key: str) -> tuple[bool, str]:
        """한 brief 처리 *직전* 호출. (allowed, reason).

        allowed=False면 reason을 텔레그램으로 알리고 brief 처리 중단.
        """
        import time
        self.reset_if_new_day()

        # 1) 명시적 일시정지 상태?
        if self.paused:
            return False, f"⏸ *시스템 일시정지 중*\n사유: {self.pause_reason or '(미상)'}\n관리자가 `state/safety.json`의 paused=false로 풀 때까지 대기."

        # 2) 일일 brief 한도
        if self.daily_brief_count >= DEFAULT_LIMITS["daily_brief_max"]:
            self.paused = True
            self.pause_reason = f"일일 brief {DEFAULT_LIMITS['daily_brief_max']}개 한도 도달"
            self.save()
            return False, f"🛑 *일일 brief 한도 초과*\n오늘 {self.daily_brief_count}개 처리 — 한도 {DEFAULT_LIMITS['daily_brief_max']}개\n자동 정지됨. UTC 자정 또는 수동 해제 시 재가동."

        # 3) 일일 비용 한도
        if self.daily_estimated_cost_usd >= DEFAULT_LIMITS["daily_cost_usd_max"]:
            self.paused = True
            self.pause_reason = f"일일 추정 비용 ${self.daily_estimated_cost_usd:.2f} 한도 도달"
            self.save()
            return False, f"🛑 *일일 비용 한도 초과*\n오늘 추정 ${self.daily_estimated_cost_usd:.2f} — 한도 ${DEFAULT_LIMITS['daily_cost_usd_max']:.2f}\n자동 정지됨."

        # 4) 버스트 보호 — 같은 에이전트 5분 내 10회 = 루프 의심
        now = time.time()
        cutoff = now - (DEFAULT_LIMITS["burst_window_minutes"] * 60)
        # 오래된 timestamp 정리
        self.recent_call_timestamps = [
            t for t in self.recent_call_timestamps if t >= cutoff
        ]
        same_agent_recent = sum(
            1 for entry in self.recent_call_timestamps
            if isinstance(entry, dict) and entry.get("agent") == agent_key
        )
        # recent_call_timestamps은 호환을 위해 dict 또는 float 허용
        # 단순화 — 같은 agent 호출만 새로 카운트
        if same_agent_recent >= DEFAULT_LIMITS["burst_max_per_agent"]:
            self.paused = True
            self.pause_reason = (
                f"버스트 감지 — {agent_key} {DEFAULT_LIMITS['burst_window_minutes']}분 내 "
                f"{same_agent_recent}회 (한도 {DEFAULT_LIMITS['burst_max_per_agent']})"
            )
            self.save()
            return False, f"🛑 *버스트 보호 발동*\n`{agent_key}`가 {DEFAULT_LIMITS['burst_window_minutes']}분 내 {same_agent_recent}회 호출됨. 무한루프 의심. 자동 정지."

        # 통과 — 카운터 증가
        self.daily_brief_count += 1
        self.daily_agent_calls[agent_key] = self.daily_agent_calls.get(agent_key, 0) + 1
        self.daily_estimated_cost_usd += APPROX_USD_PER_CALL
        self.recent_call_timestamps.append({"agent": agent_key, "ts": now})
        self.save()

        return True, ""

    def status_text(self) -> str:
        """현재 안전 상태 한 줄 요약."""
        bits = [
            f"📊 오늘 {self.daily_brief_count}/{DEFAULT_LIMITS['daily_brief_max']} brief",
            f"💰 ~${self.daily_estimated_cost_usd:.2f}/${DEFAULT_LIMITS['daily_cost_usd_max']:.2f}",
        ]
        if self.auto_mode:
            bits.append("⚡ AUTO 모드")
        if self.paused:
            bits.append(f"⏸ *정지: {self.pause_reason}*")
        return " · ".join(bits)


def _today_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


# ─────────────────────────────────────────────────────────────────────────
# 편의 헬퍼 — 외부에서 import해서 사용
# ─────────────────────────────────────────────────────────────────────────

def gate(agent_key: str) -> tuple[bool, str]:
    """한 brief 처리 직전 호출. (allowed, deny_message)."""
    state = SafetyState.load()
    return state.check_and_record(agent_key)


def status() -> str:
    return SafetyState.load().status_text()


def force_resume(reason: str = "수동 해제"):
    """관리자 수동 해제 — paused=false로 풀고 카운터는 유지."""
    state = SafetyState.load()
    state.paused = False
    state.pause_reason = ""
    state.save()
    log.info("[safety] manually resumed: %s", reason)


def is_auto_mode() -> bool:
    return SafetyState.load().auto_mode


def set_auto_mode(on: bool, reason: str = ""):
    state = SafetyState.load()
    state.auto_mode = bool(on)
    state.save()
    log.info("[safety] auto_mode = %s (%s)", on, reason)


def force_pause(reason: str):
    state = SafetyState.load()
    state.paused = True
    state.pause_reason = reason
    state.auto_mode = False    # 정지 시 AUTO도 자동 OFF
    state.save()
    log.info("[safety] force paused: %s", reason)


if __name__ == "__main__":
    # CLI: python -m agents.safety [status|resume]
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "resume":
        force_resume("CLI 수동 해제")
        print("✓ resumed")
    else:
        print(status())
