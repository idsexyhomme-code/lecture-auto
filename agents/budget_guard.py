"""비용 가드레일 — 일일 한도 초과 시 사이클 즉시 종료.

[자율 결정 — 2026-05-15]
SQLite 없이 파일 기반 (content/state/usage.jsonl + daily_total.json).
Anthropic 가격표 기반 토큰 단가 사용.

[Anthropic Sonnet 4.6 가격 (2026 시점 기준)]
- input: $3 / 1M tokens
- output: $15 / 1M tokens
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

log = logging.getLogger("budget_guard")
KST = timezone(timedelta(hours=9))

REPO_ROOT = Path(__file__).resolve().parents[1]
USAGE_LOG = REPO_ROOT / "content" / "state" / "usage.jsonl"
DAILY_FILE = REPO_ROOT / "content" / "state" / "daily_total.json"
USAGE_LOG.parent.mkdir(parents=True, exist_ok=True)

# Anthropic Sonnet 4.6 가격 (USD / 1M tokens)
PRICING = {
    "claude-sonnet-4-6": {"input": 3.0, "output": 15.0},
    "claude-opus-4-6": {"input": 15.0, "output": 75.0},
    "claude-haiku-4-5-20251001": {"input": 0.8, "output": 4.0},
}


def calc_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    p = PRICING.get(model) or PRICING["claude-sonnet-4-6"]
    return (input_tokens / 1_000_000) * p["input"] + (output_tokens / 1_000_000) * p["output"]


def today_kst() -> str:
    return datetime.now(KST).strftime("%Y-%m-%d")


def get_daily_total() -> float:
    """오늘 누적 비용 (USD)."""
    if not DAILY_FILE.exists():
        return 0.0
    try:
        d = json.loads(DAILY_FILE.read_text())
    except Exception:
        return 0.0
    if d.get("date") != today_kst():
        return 0.0  # 날짜 바뀌면 자동 0
    return float(d.get("total_usd", 0.0))


def get_daily_cap() -> float:
    """일일 한도 — .env의 DAILY_BUDGET_USD."""
    return float(os.environ.get("DAILY_BUDGET_USD", "50"))


def record_usage(
    agent: str, model: str, input_tokens: int, output_tokens: int,
    *, kind: str = "", brief: str = "",
):
    """사용량 기록 + daily 누적 갱신."""
    cost = calc_cost(model, input_tokens, output_tokens)
    entry = {
        "ts": datetime.now(KST).isoformat(),
        "agent": agent,
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": round(cost, 6),
        "kind": kind,
        "brief": brief,
    }
    # append usage log
    with USAGE_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    # daily 누적
    today = today_kst()
    prev = 0.0
    if DAILY_FILE.exists():
        try:
            d = json.loads(DAILY_FILE.read_text())
            if d.get("date") == today:
                prev = float(d.get("total_usd", 0.0))
        except Exception:
            pass
    new_total = prev + cost
    DAILY_FILE.write_text(
        json.dumps({"date": today, "total_usd": round(new_total, 4), "last_update": entry["ts"]},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return cost


def check_budget(*, agent: str = "?") -> tuple[bool, float, float]:
    """예산 한도 점검.

    Returns:
        (ok, current_usd, cap_usd)
        ok=False면 호출 거부 권장
    """
    current = get_daily_total()
    cap = get_daily_cap()
    ok = current < cap
    if not ok:
        log.warning(
            "[budget] 한도 초과 — agent=%s current=%.4f USD cap=%.2f USD",
            agent, current, cap,
        )
    return ok, current, cap


def get_status() -> dict:
    """대시보드용."""
    current = get_daily_total()
    cap = get_daily_cap()
    return {
        "date_kst": today_kst(),
        "current_usd": round(current, 4),
        "cap_usd": cap,
        "remaining_usd": round(cap - current, 4),
        "pct": round(100 * current / cap, 1) if cap > 0 else 0,
        "exceeded": current >= cap,
    }
