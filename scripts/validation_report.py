"""일일 검증 리포트 생성 — logs/validation-report-{date}.md

[자율 결정 — 2026-05-15]
- 매일 23:55 KST 자동 트리거 (long_poll.py에 추가)
- 사이클별 산출물·성공률·비용·실패 사유 정리
- Slack 대신 *텔레그램*으로 발송 (Slack webhook 없으면)
"""
from __future__ import annotations

import json
import logging
import os
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path

log = logging.getLogger("validation_report")
KST = timezone(timedelta(hours=9))

REPO = Path(__file__).resolve().parent.parent
REPORT_DIR = REPO / "logs"
REPORT_DIR.mkdir(parents=True, exist_ok=True)


def _today() -> str:
    return datetime.now(KST).strftime("%Y-%m-%d")


def _today_iso() -> str:
    return datetime.now(KST).strftime("%Y-%m-%dT%H:%M:%S%z")


def collect_today_stats() -> dict:
    """오늘 사이클 통계."""
    today = _today()

    # 산출물
    approved = []
    pending = []
    rejected = []
    for f in (REPO / "content" / "approved").glob("*.json"):
        try:
            d = json.load(open(f))
        except Exception:
            continue
        if (d.get("created_at") or "")[:10] == today:
            approved.append(d)
    for f in (REPO / "content" / "pending").glob("*.json"):
        try:
            d = json.load(open(f))
        except Exception:
            continue
        if (d.get("created_at") or "")[:10] == today:
            pending.append(d)

    kind_counter = Counter(d.get("kind", "?") for d in approved)
    agent_counter = Counter(d.get("agent", "?") for d in approved)

    # Self_review 통계
    sr_counter = Counter()
    for d in approved:
        sr = (d.get("meta") or {}).get("self_review") or {}
        sr_counter[sr.get("severity", "unknown")] += 1

    # 비용
    daily_file = REPO / "content" / "state" / "daily_total.json"
    cost = {}
    if daily_file.exists():
        try:
            cost = json.load(open(daily_file))
        except Exception:
            pass

    # 블로그 발행
    blog_pub = blog_fail = blog_sched = 0
    for d in approved:
        if d.get("kind") != "blog_post":
            continue
        m = d.get("meta") or {}
        st = m.get("tistory_status")
        if st == "scheduled":
            blog_sched += 1
        elif st == "failed":
            blog_fail += 1
        elif m.get("tistory_url"):
            blog_pub += 1

    # 실패한 brief
    failed_briefs = list((REPO / "briefs" / "_failed").glob("*.json"))

    return {
        "date_kst": today,
        "generated_at": _today_iso(),
        "approved_today": len(approved),
        "pending_today": len(pending),
        "kind_counts": dict(kind_counter),
        "agent_counts": dict(agent_counter),
        "self_review_counts": dict(sr_counter),
        "cost": cost,
        "blog": {"published": blog_pub, "scheduled": blog_sched, "failed": blog_fail},
        "failed_briefs": len(failed_briefs),
        "failed_brief_files": [p.name for p in failed_briefs[-10:]],
    }


def render_markdown(stats: dict) -> str:
    cost = stats.get("cost", {})
    cap = float(os.environ.get("DAILY_BUDGET_USD", "50"))
    lines = [
        f"# Core Campus — 일일 검증 리포트 {stats['date_kst']}",
        f"생성: {stats['generated_at']}",
        "",
        "## 1. 산출물 요약",
        f"- 오늘 승인: **{stats['approved_today']}**개",
        f"- 오늘 대기(pending): {stats['pending_today']}개",
        f"- 실패 brief: {stats['failed_briefs']}건",
        "",
        "## 2. kind별 분포",
    ]
    for k, n in sorted(stats["kind_counts"].items(), key=lambda x: -x[1]):
        lines.append(f"- `{k}`: {n}")
    lines.append("")
    lines.append("## 3. 에이전트별")
    for a, n in sorted(stats["agent_counts"].items(), key=lambda x: -x[1]):
        lines.append(f"- `{a}`: {n}")
    lines.append("")
    lines.append("## 4. 자가 검수 (F1)")
    sr = stats.get("self_review_counts", {})
    for sev in ("pass", "warn", "fail", "unknown"):
        lines.append(f"- {sev}: {sr.get(sev, 0)}")
    lines.append("")
    lines.append("## 5. 비용 (Anthropic API)")
    lines.append(f"- 오늘 누적: **${cost.get('total_usd', 0):.4f}** / 한도 ${cap:.2f}")
    pct = (cost.get("total_usd", 0) / cap * 100) if cap > 0 else 0
    lines.append(f"- 사용률: {pct:.1f}%")
    lines.append("")
    lines.append("## 6. 블로그 발행")
    b = stats["blog"]
    lines.append(f"- 발행: {b['published']} · 예약: {b['scheduled']} · 실패: {b['failed']}")
    lines.append("")
    if stats["failed_brief_files"]:
        lines.append("## 7. 실패 brief (최근 10개)")
        for n in stats["failed_brief_files"]:
            lines.append(f"- `{n}`")
        lines.append("")
    lines.append("## 8. 운영 평가")
    if stats["approved_today"] == 0:
        lines.append("- ⚠️ 오늘 승인된 산출물 0 — 데몬 상태 확인 필요")
    elif stats["blog"]["failed"] > 5:
        lines.append("- ⚠️ 블로그 실패 5건↑ — 티스토리 세션 점검 권장")
    elif pct > 90:
        lines.append("- ⚠️ 일일 예산 90%↑ 사용 — 내일까지 대기 또는 한도 상향")
    elif sr.get("fail", 0) > sr.get("pass", 0):
        lines.append("- ⚠️ self_review fail이 pass보다 많음 — system_prompt 점검")
    else:
        lines.append("- ✓ 정상 운영")
    return "\n".join(lines)


def generate() -> Path:
    stats = collect_today_stats()
    md = render_markdown(stats)
    out = REPORT_DIR / f"validation-report-{stats['date_kst']}.md"
    out.write_text(md, encoding="utf-8")
    log.info("[validation] %s 생성 — %d bytes", out.name, len(md))

    # Slack 또는 텔레그램으로 발송
    try:
        _send_to_channels(md)
    except Exception as e:
        log.warning("[validation] 알림 발송 실패: %s", e)
    return out


def _send_to_channels(md: str):
    """Slack webhook 또는 텔레그램으로 리포트 발송."""
    slack_url = os.environ.get("SLACK_WEBHOOK_URL")
    if slack_url:
        try:
            import requests
            requests.post(slack_url, json={"text": md[:3500]}, timeout=10)
            return
        except Exception:
            pass

    # 텔레그램 fallback (이미 가동 중)
    try:
        import sys
        sys.path.insert(0, str(REPO))
        from telegram_bot import client as tg
        tg.send_text(f"📊 *일일 검증 리포트*\n\n{md[:3500]}", parse_mode="Markdown")
    except Exception:
        pass


if __name__ == "__main__":
    p = generate()
    print(f"✓ {p}")
