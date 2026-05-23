"""LLM 어댑터 공통 인터페이스 — 모든 6개 LLM이 이걸 상속."""
from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class LLMResponse:
    """단일 LLM 호출 결과 — 멀티 LLM 검증/앙상블의 단위."""

    llm: str                      # "claude" | "openai" | "gemini" | ...
    model: str                    # 실제 모델명 (예: "claude-sonnet-4-6")
    text: str                     # 응답 본문
    success: bool = True          # API 호출 성공 여부
    latency_ms: int = 0           # 응답 시간
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0         # 추정 비용
    error: str = ""               # 실패 시 사유
    meta: dict = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "llm": self.llm, "model": self.model, "text": self.text,
            "success": self.success, "latency_ms": self.latency_ms,
            "input_tokens": self.input_tokens, "output_tokens": self.output_tokens,
            "cost_usd": round(self.cost_usd, 6), "error": self.error, "meta": self.meta,
        }


class BaseAdapter:
    """모든 LLM 어댑터의 공통 베이스.

    서브클래스는 다음을 구현해야 함:
    - llm_name      : "claude" | "openai" | "gemini" | "perplexity" | "grok" | "mistral"
    - default_model : 기본 모델명
    - env_key       : API key 환경변수 이름 (예: "ANTHROPIC_API_KEY")
    - async def generate(prompt, system, max_tokens) -> LLMResponse
    """

    llm_name: str = "base"
    default_model: str = ""
    env_key: str = ""

    # 1K input/output token 당 USD 비용 (대략치, 2026-05 기준)
    pricing: dict[str, float] = {"input_per_1k": 0.0, "output_per_1k": 0.0}

    def __init__(self, model: str | None = None, api_key: str | None = None):
        self.model = model or self.default_model
        self.api_key = api_key or os.environ.get(self.env_key, "")
        self.enabled = bool(self.api_key and not self.api_key.startswith("sk-..."))

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        in_usd = (input_tokens / 1000) * self.pricing["input_per_1k"]
        out_usd = (output_tokens / 1000) * self.pricing["output_per_1k"]
        return in_usd + out_usd

    async def generate(self, prompt: str, system: str = "",
                       max_tokens: int = 2000) -> LLMResponse:
        raise NotImplementedError(f"{self.__class__.__name__}.generate() 미구현")

    def disabled_response(self) -> LLMResponse:
        """API key 없을 때 반환하는 placeholder. 멀티 LLM 호출에서 graceful skip."""
        return LLMResponse(
            llm=self.llm_name, model=self.model, text="",
            success=False,
            error=f"{self.env_key} 환경변수 미설정 — .env에 추가 필요",
        )
