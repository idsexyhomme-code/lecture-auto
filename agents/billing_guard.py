"""중앙 과금 차단 가드 — 모든 유료 외부 API 호출의 단일 킬스위치.

기본값은 **차단(fail-safe)**. 키가 .env/환경변수에 다시 들어와도,
명시적으로 ``CC_ALLOW_API_BILLING=1`` 을 켜지 않는 한 절대 과금 호출이 나가지 않는다.

설계 의도 (회원 정책 2026-06-08):
- 자동화 파이프라인은 구독이 아니라 콘솔 API 과금으로 새기 때문에 전면 차단한다.
- 정말 콘솔 비용으로 돌리고 싶을 때만 ``CC_ALLOW_API_BILLING=1`` 을 켠다.
- 추가로 provider별 레거시 비활성 플래그(`*_DISABLED_20260608`, `*_API_BLOCKED`)도
  계속 존중한다(이중 안전장치).

이 가드를 통과하는 경로:
- agents/base.py            (8개 핵심 에이전트 본체 — Claude API)
- agents/llm_adapters/*     (6-AI 다중검증: claude/openai/gemini/grok/perplexity/mistral)
- agents/image_gen.py       (이미지 생성: openai gpt-image-1 / gemini 나노바나나)
"""
from __future__ import annotations

import os

_TRUTHY = {"1", "true", "yes", "on"}

# provider 키워드 → 레거시 비활성 환경변수 이름
_LEGACY_FLAGS = {
    "anthropic": ("ANTHROPIC_API_KEY_DISABLED_20260608", "ANTHROPIC_API_BLOCKED"),
    "claude": ("ANTHROPIC_API_KEY_DISABLED_20260608", "ANTHROPIC_API_BLOCKED"),
    "openai": ("OPENAI_API_KEY_DISABLED_20260608", "OPENAI_API_BLOCKED"),
}


def _truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in _TRUTHY


def billing_block_reason(provider: str = "api") -> str | None:
    """유료 API 호출을 막아야 하면 사유 문자열, 통과 가능하면 None.

    1) 명시적 허용(CC_ALLOW_API_BILLING)이 켜져 있어도, provider별 레거시
       비활성 플래그가 설정돼 있으면 그 provider는 계속 차단한다.
    2) 명시적 허용이 없으면(기본값) 모든 provider를 차단한다.
    """
    p = (provider or "api").strip().lower()

    # provider별 레거시 강제 비활성 — 명시적 허용보다 우선
    for flag in _LEGACY_FLAGS.get(p, ()):  # noqa: SIM110
        if _truthy(flag) or os.environ.get(flag):
            return (
                f"[billing-blocked] {p} API 호출 차단됨 "
                f"({flag} 설정됨)."
            )

    # 마스터 허용 스위치
    if _truthy("CC_ALLOW_API_BILLING"):
        return None

    return (
        f"[billing-blocked] {p} 유료 API 호출이 기본 차단됨. "
        f"콘솔 과금을 정말 쓰려면 CC_ALLOW_API_BILLING=1 을 명시적으로 켜라."
    )


def assert_billing_allowed(provider: str = "api") -> None:
    """차단 상태면 RuntimeError를 던진다(동기 경로용)."""
    reason = billing_block_reason(provider)
    if reason:
        raise RuntimeError(reason)
