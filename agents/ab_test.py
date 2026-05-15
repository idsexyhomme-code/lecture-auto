"""F4: A/B 테스트 — 같은 brief을 두 버전으로 실행, 우승안 채택.

[목적]
어떤 system_prompt·prompt가 더 나은지 *추측 X, 측정 O*.
self_review·CEO 평가 점수로 비교 → 우승안의 *변경점*을 v2에 학습.

[활성]
- CC_AB_TEST=1 환경변수
- 또는 brief에 명시: brief["ab_test"] = {"variants": ["v1","v2"]}

[안전]
- 한 brief당 최대 2배 비용 (2회 호출). 기본 OFF.
- CEO 게이트 산출물은 자동 A/B X (사용자 혼란 방지). 회원이 명시할 때만.
- 우승안만 pending에 저장. 패자는 meta에 기록.

[v1·v2 정의]
- v1 = 현재 system_prompt (control)
- v2 = system_prompt + 학습된 가이드 (treatment — F3 가이드)
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path

from .base import REPO_ROOT, AgentResult, BaseAgent

log = logging.getLogger("ab_test")

AB_RESULTS_DIR = REPO_ROOT / "data" / "learning" / "ab_results"
AB_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
KST = timezone(timedelta(hours=9))


def is_ab_enabled() -> bool:
    return os.environ.get("CC_AB_TEST", "").lower() in ("1", "true", "yes")


def _score_result(text: str, kind: str = "") -> dict:
    """결과 텍스트를 점수화. 높을수록 좋음.

    점수 항목:
    - severity (pass=10, warn=5, fail=0)
    - 길이 (적정 범위 가산점)
    - hard/soft 위반 감산
    """
    review = BaseAgent.self_review(text, kind=kind)
    score = 0
    sev = review["severity"]
    if sev == "pass":
        score += 10
    elif sev == "warn":
        score += 5
    # fail = 0

    # 길이 적정 (200~3000자)
    n = len(text or "")
    if 200 <= n <= 3000:
        score += 3
    elif 100 <= n < 200:
        score += 1

    # 위반 감산
    score -= len(review.get("hard_violations", [])) * 5
    score -= len(review.get("soft_violations", [])) * 1

    return {"score": score, "severity": sev, "len": n, "review": review}


async def run_ab(
    agent: BaseAgent,
    user_prompt: str,
    *,
    max_tokens: int = 4000,
    kind: str = "",
    save_loser: bool = True,
) -> tuple[str, dict]:
    """A/B 테스트 실행. 두 버전 동시 생성 → 점수 비교 → 우승안 반환.

    Returns:
        (winner_text, metadata_dict)
        metadata_dict: {winner, scores, variants_text}
    """
    # 두 변형:
    # v1 (control) — 현재 system_prompt 그대로
    # v2 (treatment) — system_prompt + 추가 가이드 (학습된 패턴 강조)
    extra_v2 = (
        "\n\n[A/B 변형 v2 — 추가 강조]\n"
        "- 위 헌법·금기어를 *모두 자가 검수*한 후 출력하라.\n"
        "- 일상 장면·숫자·구체 사례를 *반드시* 1개 이상 포함.\n"
        "- 출력 전 자가 검수에서 hard 위반·soft 위반 3개 이상이면 다시 쓴다."
    )

    # 비동기 동시 호출
    coros = [
        agent.acall(user_prompt, max_tokens=max_tokens, extra_system=""),
        agent.acall(user_prompt, max_tokens=max_tokens, extra_system=extra_v2),
    ]
    try:
        v1_text, v2_text = await asyncio.gather(*coros)
    except Exception as e:
        log.warning("[ab] 호출 실패 — fallback to v1 only: %s", e)
        v1_text = agent.call(user_prompt, max_tokens=max_tokens)
        v2_text = v1_text  # fallback — 동률

    s1 = _score_result(v1_text, kind=kind)
    s2 = _score_result(v2_text, kind=kind)

    winner = "v1" if s1["score"] >= s2["score"] else "v2"
    winner_text = v1_text if winner == "v1" else v2_text

    metadata = {
        "ab_winner": winner,
        "ab_scores": {"v1": s1, "v2": s2},
        "ab_diff": s2["score"] - s1["score"],
        "ab_kind": kind,
        "ab_timestamp": datetime.now(KST).isoformat(),
    }
    if save_loser:
        # 패자도 별도 저장 — 분석용
        loser_text = v2_text if winner == "v1" else v1_text
        result_id = f"ab-{int(datetime.now(KST).timestamp())}-{kind or 'unknown'}"
        AB_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        (AB_RESULTS_DIR / f"{result_id}.json").write_text(
            json.dumps({
                "winner": winner,
                "scores": {"v1": s1, "v2": s2},
                "v1_text": v1_text[:2000],
                "v2_text": v2_text[:2000],
                "kind": kind,
                "timestamp": metadata["ab_timestamp"],
            }, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    log.info(
        "[ab] %s winner=%s (v1=%d v2=%d diff=%+d)",
        kind, winner, s1["score"], s2["score"], metadata["ab_diff"],
    )
    return winner_text, metadata


def get_recent_ab_stats(*, days: int = 7) -> dict:
    """대시보드용 — 최근 N일 A/B 결과 통계."""
    cutoff = (datetime.now(KST) - timedelta(days=days)).isoformat()
    total = 0
    winners = Counter()
    diff_sum = 0
    for f in AB_RESULTS_DIR.glob("ab-*.json"):
        try:
            d = json.loads(f.read_text())
        except Exception:
            continue
        if d.get("timestamp", "") < cutoff:
            continue
        total += 1
        winners[d.get("winner", "?")] += 1
        diff_sum += (
            d.get("scores", {}).get("v2", {}).get("score", 0)
            - d.get("scores", {}).get("v1", {}).get("score", 0)
        )
    return {
        "days": days,
        "total": total,
        "v1_wins": winners.get("v1", 0),
        "v2_wins": winners.get("v2", 0),
        "avg_diff": (diff_sum / total) if total else 0,
    }
