"""F5: 실패 메모리 — 패턴 누적·임계값 초과 시 자동 banned_words 확장.

[흐름]
1. F1 self_review가 hard/soft 위반을 meta에 기록
2. F3 learning.update_from_recent()가 v2 파일에 누적 카운트
3. F5는 v2의 카운트를 보고 *임계값 초과 패턴*을 learned_banned_words로 승격
4. _copy_principles가 자동으로 그 단어들을 system_prompt에 inject (F3에서 구현)

[임계값]
- hard 위반: 누적 3회 이상 → learned_banned_words 자동 추가
- soft 위반: 누적 10회 이상 → learned_banned_words 자동 추가
- 회원이 v2 파일 직접 편집으로 임계값 우회 가능
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

from .learning import LEARNING_DIR, load_v2, save_v2, update_from_recent

log = logging.getLogger("memory")

KST = timezone(timedelta(hours=9))
HARD_THRESHOLD = 3   # hard 위반 3회 → learned ban
SOFT_THRESHOLD = 10  # soft 위반 10회 → learned ban
PROMOTION_LOG = LEARNING_DIR / "promotion_log.json"


def promote_patterns() -> dict:
    """임계값 초과 패턴을 learned_banned_words로 자동 승격.

    Returns:
        {promoted_hard, promoted_soft, total_learned, log}
    """
    v2 = load_v2()
    fail_c = v2.get("fail_pattern_counts", {})
    warn_c = v2.get("warn_pattern_counts", {})
    learned = set(v2.get("learned_banned_words", []))

    promoted_hard, promoted_soft = [], []

    for word, count in fail_c.items():
        if word and count >= HARD_THRESHOLD and word not in learned:
            learned.add(word)
            promoted_hard.append({"word": word, "count": count, "source": "hard"})

    for word, count in warn_c.items():
        if word and count >= SOFT_THRESHOLD and word not in learned:
            learned.add(word)
            promoted_soft.append({"word": word, "count": count, "source": "soft"})

    v2["learned_banned_words"] = sorted(learned)
    save_v2(v2)

    # 승격 로그 별도 보관
    if promoted_hard or promoted_soft:
        log_data = []
        if PROMOTION_LOG.exists():
            try:
                log_data = json.loads(PROMOTION_LOG.read_text(encoding="utf-8"))
            except Exception:
                log_data = []
        log_data.append({
            "timestamp": datetime.now(KST).isoformat(),
            "promoted_hard": promoted_hard,
            "promoted_soft": promoted_soft,
        })
        PROMOTION_LOG.write_text(
            json.dumps(log_data[-200:], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    result = {
        "promoted_hard": promoted_hard,
        "promoted_soft": promoted_soft,
        "total_learned": len(learned),
    }
    if promoted_hard or promoted_soft:
        log.info(
            "[memory] 학습된 금기어 +%d (hard) +%d (soft) — 총 %d 단어",
            len(promoted_hard), len(promoted_soft), len(learned),
        )
    return result


def update_and_promote(*, days: int = 7) -> dict:
    """원샷 호출 — 통계 갱신 + 승격.

    데몬에서 매일 1회 호출 (CEO daily 트리거 옆에서).
    """
    stats = update_from_recent(days=days)
    promo = promote_patterns()
    return {"stats": stats, "promotion": promo}


def get_status() -> dict:
    """대시보드용."""
    v2 = load_v2()
    log_data = []
    if PROMOTION_LOG.exists():
        try:
            log_data = json.loads(PROMOTION_LOG.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "total_learned_words": len(v2.get("learned_banned_words", [])),
        "learned_words": v2.get("learned_banned_words", []),
        "top_fail_patterns": dict(
            sorted(v2.get("fail_pattern_counts", {}).items(),
                   key=lambda x: -x[1])[:10]
        ),
        "top_warn_patterns": dict(
            sorted(v2.get("warn_pattern_counts", {}).items(),
                   key=lambda x: -x[1])[:10]
        ),
        "stats": v2.get("stats", {}),
        "recent_promotions": log_data[-5:],
    }
