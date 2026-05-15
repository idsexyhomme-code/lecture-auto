"""F3: KPI·self_review 통계 → system_prompt 자동 갱신.

[자가 학습 루프]
1. 매번 산출물 생성 시 self_review 결과가 meta에 기록됨 (F1)
2. F3는 *누적 통계*를 보고 학습된 패턴을 추출 → copy_principles_v2.json에 저장
3. _copy_principles.HUMAN_TONE_GUIDE 가 v2 파일을 자동 inject (시간이 갈수록 가이드가 진화)

[안전 보장]
- v2 파일 수정은 *추가만* (기존 항목 삭제 X)
- 임계값 초과 시에만 banned_words에 추가 (5회 이상 위반 등)
- 회원이 v2 파일 직접 수정해서 *오버라이드* 가능
"""
from __future__ import annotations

import json
import logging
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path

from .base import REPO_ROOT, APPROVED_DIR

log = logging.getLogger("learning")

LEARNING_DIR = REPO_ROOT / "data" / "learning"
LEARNING_DIR.mkdir(parents=True, exist_ok=True)
V2_FILE = LEARNING_DIR / "copy_principles_v2.json"
KST = timezone(timedelta(hours=9))


def _empty_v2() -> dict:
    return {
        "_version": 1,
        "_last_updated": datetime.now(KST).isoformat(),
        "learned_banned_words": [],          # F5에서 누적
        "fail_pattern_counts": {},            # 단어 → 누적 위반 횟수
        "warn_pattern_counts": {},
        "success_signals": [],                # 잘 통과한 패턴 (참고용)
        "stats": {
            "total_reviews": 0,
            "fail_count": 0,
            "warn_count": 0,
            "pass_count": 0,
        },
    }


def load_v2() -> dict:
    if not V2_FILE.exists():
        return _empty_v2()
    try:
        return json.loads(V2_FILE.read_text(encoding="utf-8"))
    except Exception:
        return _empty_v2()


def save_v2(data: dict):
    data["_last_updated"] = datetime.now(KST).isoformat()
    V2_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def analyze_recent(*, days: int = 7) -> dict:
    """최근 N일 산출물의 self_review 통계 분석.

    Returns:
        {total, fail, warn, pass, hard_violation_counts, soft_violation_counts}
    """
    cutoff = (datetime.now(KST) - timedelta(days=days)).isoformat()
    total = fail = warn = pas = 0
    hard_c = Counter()
    soft_c = Counter()
    fail_kinds = Counter()

    for f in APPROVED_DIR.glob("*.json"):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if d.get("created_at", "") < cutoff:
            continue
        meta = d.get("meta") or {}
        sr = meta.get("self_review")
        if not sr:
            continue
        total += 1
        sev = sr.get("severity")
        if sev == "fail":
            fail += 1
            fail_kinds[d.get("kind", "?")] += 1
        elif sev == "warn":
            warn += 1
        else:
            pas += 1
        for w in sr.get("hard_violations", []):
            hard_c[w] += 1
        for w in sr.get("soft_violations", []):
            soft_c[w] += 1

    return {
        "days": days,
        "total": total,
        "fail": fail,
        "warn": warn,
        "pass": pas,
        "hard_violation_counts": dict(hard_c.most_common(20)),
        "soft_violation_counts": dict(soft_c.most_common(20)),
        "fail_by_kind": dict(fail_kinds.most_common(10)),
    }


def update_from_recent(*, days: int = 7) -> dict:
    """최근 통계를 v2 파일에 누적. F5 (memory) 와 함께 호출됨."""
    stats = analyze_recent(days=days)
    v2 = load_v2()

    # 통계 누적
    v2["stats"]["total_reviews"] += stats["total"]
    v2["stats"]["fail_count"] += stats["fail"]
    v2["stats"]["warn_count"] += stats["warn"]
    v2["stats"]["pass_count"] += stats["pass"]

    # 누적 위반 카운트 (F5 임계값 판정용)
    fc = Counter(v2.get("fail_pattern_counts", {}))
    wc = Counter(v2.get("warn_pattern_counts", {}))
    fc.update(stats["hard_violation_counts"])
    wc.update(stats["soft_violation_counts"])
    v2["fail_pattern_counts"] = dict(fc)
    v2["warn_pattern_counts"] = dict(wc)

    save_v2(v2)
    log.info(
        "[learning] v2 갱신: total=%d fail=%d warn=%d pass=%d",
        stats["total"], stats["fail"], stats["warn"], stats["pass"],
    )
    return stats


def get_learned_addendum() -> str:
    """_copy_principles.HUMAN_TONE_GUIDE 끝에 자동 inject되는 학습된 가이드.

    v2 파일에서 *임계값 초과* banned_words를 추출해 system_prompt에 추가.
    """
    v2 = load_v2()
    learned = v2.get("learned_banned_words", [])
    if not learned:
        return ""
    return (
        "\n\n[학습된 추가 금기어 — F3·F5 자동 갱신]\n"
        f"  {', '.join(learned)}\n"
        "  (위 단어는 누적 위반 횟수가 임계값을 초과해 자동 추가됨. "
        "수동 제거는 data/learning/copy_principles_v2.json 편집.)"
    )
