"""Claude (Anthropic) adapter — Core Compass의 6 AI 중 #1."""
from __future__ import annotations

import time

from anthropic import AsyncAnthropic

from .base_adapter import BaseAdapter, LLMResponse


class ClaudeAdapter(BaseAdapter):
    llm_name = "claude"
    default_model = "claude-sonnet-4-6"
    env_key = "ANTHROPIC_API_KEY"
    # Claude Sonnet 4 pricing
    pricing = {"input_per_1k": 0.003, "output_per_1k": 0.015}

    def __init__(self, model: str | None = None, api_key: str | None = None):
        super().__init__(model=model, api_key=api_key)
        self._client: AsyncAnthropic | None = None

    @property
    def client(self) -> AsyncAnthropic:
        if self._client is None:
            self._client = AsyncAnthropic(api_key=self.api_key)
        return self._client

    async def generate(self, prompt: str, system: str = "",
                       max_tokens: int = 2000) -> LLMResponse:
        if not self.enabled:
            return self.disabled_response()

        t0 = time.time()
        try:
            msg = await self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system or "",
                messages=[{"role": "user", "content": prompt}],
            )
            text = "".join(
                b.text for b in msg.content if getattr(b, "type", None) == "text"
            )
            usage = getattr(msg, "usage", None)
            in_tok = getattr(usage, "input_tokens", 0) if usage else 0
            out_tok = getattr(usage, "output_tokens", 0) if usage else 0
            return LLMResponse(
                llm=self.llm_name, model=self.model, text=text, success=True,
                latency_ms=int((time.time() - t0) * 1000),
                input_tokens=in_tok, output_tokens=out_tok,
                cost_usd=self.estimate_cost(in_tok, out_tok),
            )
        except Exception as e:
            return LLMResponse(
                llm=self.llm_name, model=self.model, text="", success=False,
                latency_ms=int((time.time() - t0) * 1000),
                error=f"{type(e).__name__}: {str(e)[:200]}",
            )
