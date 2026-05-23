"""xAI Grok adapter — 6 AI 중 #5 (Microsoft Copilot 대체).

이유: Microsoft Copilot은 일반 사용자 API가 없음. xAI Grok이 6번째 LLM으로 적합:
- 다른 5개와 완전 독립된 회사·모델 (다양성↑)
- OpenAI 호환 API라 통합 쉬움
- 가격 합리적

API key 발급: https://console.x.ai/
환경변수: XAI_API_KEY
"""
from __future__ import annotations

import time

import httpx

from .base_adapter import BaseAdapter, LLMResponse


class GrokAdapter(BaseAdapter):
    llm_name = "grok"
    default_model = "grok-2-latest"
    env_key = "XAI_API_KEY"
    # Grok-2 pricing (2026-05)
    pricing = {"input_per_1k": 0.002, "output_per_1k": 0.010}

    API_URL = "https://api.x.ai/v1/chat/completions"

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

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": self.model,
                "messages": messages,
                "max_tokens": max_tokens,
            }

            async with httpx.AsyncClient(timeout=60.0) as cli:
                res = await cli.post(self.API_URL, headers=headers, json=payload)
                res.raise_for_status()
                data = res.json()

            text = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            in_tok = usage.get("prompt_tokens", 0)
            out_tok = usage.get("completion_tokens", 0)
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
