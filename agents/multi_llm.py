"""
멀티 LLM 동시 호출 + 검증 모듈 — Core Compass "6 AI 다중 검증" 백엔드.

핵심 사용 패턴:
    from agents.multi_llm import MultiLLMValidator

    validator = MultiLLMValidator()
    result = await validator.run(
        prompt="1인 사업가의 강점·약점·90일 액션 진단해주세요.",
        system="당신은 1인 사업 진단 전문가입니다.",
        require_min_success=3,   # 6개 중 최소 3개 성공해야 결과 인정
    )

    result.consensus      # 종합 텍스트 (Claude가 6개 응답을 통합)
    result.responses      # 6개 LLM 개별 응답 (LLMResponse 리스트)
    result.agreement      # 응답 간 합의도 (0.0~1.0, 임베딩 유사도)
    result.total_cost_usd # 총 비용
    result.elapsed_ms     # 총 시간
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from .llm_adapters import (
    BaseAdapter, ClaudeAdapter, OpenAIAdapter, GeminiAdapter,
    PerplexityAdapter, GrokAdapter, MistralAdapter, LLMResponse,
)

log = logging.getLogger("agents.multi_llm")


@dataclass
class MultiLLMResult:
    """6 LLM 통합 호출 결과."""

    consensus: str = ""                          # 통합된 최종 텍스트
    responses: list[LLMResponse] = field(default_factory=list)  # 6개 개별 응답
    success_count: int = 0                       # 성공한 LLM 수
    fail_count: int = 0                          # 실패한 LLM 수
    enabled_llms: list[str] = field(default_factory=list)  # 활성화된 LLM 이름
    disabled_llms: list[str] = field(default_factory=list) # API key 없는 LLM
    total_cost_usd: float = 0.0
    elapsed_ms: int = 0
    agreement: float = 0.0                       # 응답 간 일치도 (length 기반 휴리스틱)

    def to_dict(self) -> dict[str, Any]:
        return {
            "consensus": self.consensus,
            "responses": [r.to_dict() for r in self.responses],
            "success_count": self.success_count,
            "fail_count": self.fail_count,
            "enabled_llms": self.enabled_llms,
            "disabled_llms": self.disabled_llms,
            "total_cost_usd": round(self.total_cost_usd, 6),
            "elapsed_ms": self.elapsed_ms,
            "agreement": round(self.agreement, 3),
        }


class MultiLLMValidator:
    """6개 LLM 병렬 호출 + 결과 통합/검증 오케스트레이터.

    설계:
    - API key 없는 LLM은 graceful skip (disabled로 분류)
    - 모든 호출은 asyncio.gather()로 동시 진행 (총 시간 = 가장 느린 1개)
    - 통합 단계: Claude가 6개 응답을 받아 consensus 작성 (또는 첫 성공 응답 그대로)
    - tier 시스템: basic(3 AI, 9,900원) vs premium(6 AI, 19,900원+)
    """

    # 티어별 LLM 셋 — 가격대별 차별화 (회원 결정)
    TIER_BASIC: list[type[BaseAdapter]] = [
        ClaudeAdapter, OpenAIAdapter, GeminiAdapter,
    ]  # 9,900원 상품 — 3 AI 핵심 분석
    TIER_PREMIUM: list[type[BaseAdapter]] = [
        ClaudeAdapter, OpenAIAdapter, GeminiAdapter,
        PerplexityAdapter, GrokAdapter, MistralAdapter,
    ]  # 19,900원+ 상품 — 6 AI 다중 검증 + 시장 트렌드

    # 기본은 모든 6개 (직접 adapters 지정도 가능)
    DEFAULT_ADAPTERS = TIER_PREMIUM

    def __init__(self, adapters: list[BaseAdapter] | None = None,
                 tier: str | None = None):
        """
        Args:
            adapters: 명시적으로 어댑터 리스트 지정 (tier 무시됨)
            tier: "basic" (3 AI) | "premium" (6 AI) — 상품 가격대별 선택
        """
        if adapters is not None:
            self.adapters = adapters
        elif tier == "basic":
            self.adapters = [cls() for cls in self.TIER_BASIC]
            self.tier = "basic"
        elif tier == "premium":
            self.adapters = [cls() for cls in self.TIER_PREMIUM]
            self.tier = "premium"
        else:
            self.adapters = [cls() for cls in self.DEFAULT_ADAPTERS]
            self.tier = "premium"

        # 명시적 adapter 지정 시 tier 추론
        if not hasattr(self, "tier"):
            self.tier = "custom"

    @property
    def enabled_adapters(self) -> list[BaseAdapter]:
        return [a for a in self.adapters if a.enabled]

    @property
    def disabled_adapters(self) -> list[BaseAdapter]:
        return [a for a in self.adapters if not a.enabled]

    def status(self) -> dict[str, Any]:
        """현재 LLM 활성화 상태 — health check 용."""
        return {
            "tier": getattr(self, "tier", "custom"),
            "total": len(self.adapters),
            "enabled": len(self.enabled_adapters),
            "disabled": len(self.disabled_adapters),
            "enabled_llms": [a.llm_name for a in self.enabled_adapters],
            "disabled_llms": [
                {"llm": a.llm_name, "needs": a.env_key}
                for a in self.disabled_adapters
            ],
        }

    @classmethod
    def for_product(cls, product_price_krw: int) -> "MultiLLMValidator":
        """가격대로 자동 티어 선택 — 9,900원 이하 basic, 초과 premium."""
        tier = "basic" if product_price_krw <= 9900 else "premium"
        return cls(tier=tier)

    async def run(self, prompt: str, system: str = "",
                  max_tokens: int = 2000,
                  require_min_success: int = 2,
                  build_consensus: bool = True) -> MultiLLMResult:
        """6개 LLM 병렬 호출 + 통합.

        Args:
            prompt: 사용자 질의
            system: 시스템 프롬프트 (공통)
            max_tokens: 각 LLM 응답 최대 토큰
            require_min_success: 최소 성공 응답 수 (이 이하면 ValueError raise)
            build_consensus: Claude로 6개 응답 통합 텍스트 생성 여부
        """
        t0 = time.time()

        # 1. 6개 LLM 병렬 호출 (활성화된 것만)
        active = self.enabled_adapters
        if not active:
            raise ValueError(
                "활성화된 LLM이 없음. .env에 최소 1개 이상 API key 추가 필요."
            )

        log.info("multi_llm.run start — enabled=%d (%s)",
                 len(active), [a.llm_name for a in active])

        tasks = [a.generate(prompt, system, max_tokens) for a in active]
        responses: list[LLMResponse] = await asyncio.gather(
            *tasks, return_exceptions=False
        )

        # 2. 비활성화된 LLM도 결과 리스트에 표시 (disabled로)
        for a in self.disabled_adapters:
            responses.append(a.disabled_response())

        # 3. 성공/실패 카운트
        success = [r for r in responses if r.success and r.text.strip()]
        fail = [r for r in responses if not r.success]

        if len(success) < require_min_success:
            log.warning("multi_llm fail — success=%d/%d (min required: %d)",
                       len(success), len(active), require_min_success)
            raise RuntimeError(
                f"최소 {require_min_success}개 LLM 성공 필요했으나 "
                f"실제 {len(success)}개만 성공. "
                f"errors: {[(r.llm, r.error) for r in fail]}"
            )

        # 4. 합의도 계산 (휴리스틱: 응답 길이 표준편차로)
        agreement = self._compute_agreement(success)

        # 5. consensus 생성 (옵션)
        consensus_text = ""
        if build_consensus and success:
            consensus_text = await self._build_consensus(
                prompt=prompt, system=system, responses=success,
            )
        elif success:
            consensus_text = success[0].text  # 첫 성공 응답 그대로

        total_cost = sum(r.cost_usd for r in responses)

        result = MultiLLMResult(
            consensus=consensus_text,
            responses=responses,
            success_count=len(success),
            fail_count=len(fail),
            enabled_llms=[a.llm_name for a in active],
            disabled_llms=[a.llm_name for a in self.disabled_adapters],
            total_cost_usd=total_cost,
            elapsed_ms=int((time.time() - t0) * 1000),
            agreement=agreement,
        )
        log.info("multi_llm done — success=%d fail=%d cost=$%.4f elapsed=%dms",
                 result.success_count, result.fail_count,
                 result.total_cost_usd, result.elapsed_ms)
        return result

    def _compute_agreement(self, responses: list[LLMResponse]) -> float:
        """응답 간 일치도 (휴리스틱 0.0~1.0).

        현재는 응답 길이의 변동계수로 간이 측정 — 추후 임베딩 유사도로 업그레이드 가능.
        같은 길이대면 1.0에 가까움, 변동 크면 0.0에 가까움.
        """
        if len(responses) < 2:
            return 1.0
        lengths = [len(r.text) for r in responses]
        mean = sum(lengths) / len(lengths)
        if mean == 0:
            return 0.0
        variance = sum((x - mean) ** 2 for x in lengths) / len(lengths)
        std = variance ** 0.5
        cv = std / mean  # coefficient of variation
        # cv 0 → 1.0, cv 1+ → 0.0
        return max(0.0, min(1.0, 1.0 - cv))

    async def _build_consensus(self, prompt: str, system: str,
                                responses: list[LLMResponse]) -> str:
        """Claude로 N개 응답을 통합한 consensus 텍스트 생성.

        Claude가 enabled되어 있지 않으면 그냥 첫 성공 응답 반환.
        """
        claude = next(
            (a for a in self.enabled_adapters if a.llm_name == "claude"), None
        )
        if claude is None:
            return responses[0].text

        consensus_prompt = self._format_consensus_prompt(
            original_prompt=prompt, responses=responses,
        )
        consensus_system = (
            "당신은 여러 AI 응답을 통합하는 메타 검토자입니다. "
            "각 AI의 강점을 살리되 모순은 명시하고, 공통 합의는 강조하세요. "
            "원문 요청에 직접 답하는 통합 응답을 작성하세요. "
            "중간에 'AI 1', 'AI 2' 같은 라벨링은 쓰지 말고 자연스러운 글로."
        )
        res = await claude.generate(
            prompt=consensus_prompt, system=consensus_system, max_tokens=3000,
        )
        return res.text if res.success else responses[0].text

    @staticmethod
    def _format_consensus_prompt(original_prompt: str,
                                  responses: list[LLMResponse]) -> str:
        sections = []
        for i, r in enumerate(responses, 1):
            sections.append(
                f"\n## 응답 {i} (출처: {r.llm}/{r.model})\n\n{r.text}"
            )
        bundle = "\n".join(sections)
        return (
            f"# 원문 요청\n\n{original_prompt}\n\n"
            f"---\n\n# {len(responses)}개 AI의 응답\n{bundle}\n\n"
            f"---\n\n"
            f"위 {len(responses)}개 응답을 통합해서 "
            f"원문 요청에 답하는 하나의 일관된 응답을 작성하세요. "
            f"공통 합의 사항은 신뢰도 높음으로 강조하고, "
            f"엇갈리는 부분은 '의견 차이가 있음 — A 관점 vs B 관점'으로 명시하세요."
        )


# ── 편의 함수 ──────────────────────────────────────────────────────────
async def quick_run(prompt: str, system: str = "",
                    max_tokens: int = 2000) -> MultiLLMResult:
    """1줄 사용: result = await quick_run("...")"""
    return await MultiLLMValidator().run(prompt, system, max_tokens)


def check_status() -> dict[str, Any]:
    """현재 환경의 LLM 활성화 상태 빠르게 확인."""
    return MultiLLMValidator().status()
