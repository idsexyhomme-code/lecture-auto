"""OpenAI (ChatGPT) adapter — 6 AI 중 #2. 회원이 이미 OPENAI_API_KEY 보유."""
from __future__ import annotations

import time

from .base_adapter import BaseAdapter, LLMResponse


class OpenAIAdapter(BaseAdapter):
    llm_name = "openai"
    default_model = "gpt-4o"
    env_key = "OPENAI_API_KEY"
    # GPT-4o pricing (2026-05)
    pricing = {"input_per_1k": 0.0025, "output_per_1k": 0.010}

    def __init__(self, model: str | None = None, api_key: str | None = None):
        super().__init__(model=model, api_key=api_key)
        self._client = None

    @property
    def client(self):
        if self._client is None:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(api_key=self.api_key)
        return self._client

    async def generate(self, prompt: str, system: str = "",
                       max_tokens: int = 2000) -> LLMResponse:
        if not self.enabled:
            return self.disabled_response()

        t0 = time.time()
        try:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            res = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
            )
            text = res.choices[0].message.content or ""
            usage = res.usage
            in_tok = getattr(usage, "prompt_tokens", 0) if usage else 0
            out_tok = getattr(usage, "completion_tokens", 0) if usage else 0
            return LLMResponse(
                llm=self.llm_name, model=self.model, text=text, success=True,
                latency_ms=int((time.time() - t0) * 1000),
                input_tokens=in_tok, output_tokens=out_tok,
                cost_usd=self.estimate_cost(in_tok, out_tok),
            )
        except ImportError:
            return LLMResponse(
                llm=self.llm_name, model=self.model, text="", success=False,
                error="openai 패키지 미설치 — pip install openai>=1.0",
            )
        except Exception as e:
            return LLMResponse(
                llm=self.llm_name, model=self.model, text="", success=False,
                latency_ms=int((time.time() - t0) * 1000),
                error=f"{type(e).__name__}: {str(e)[:200]}",
            )
