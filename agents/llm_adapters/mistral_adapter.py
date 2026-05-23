"""Mistral adapter — 6 AI 중 #6 (Bing 검색 대체).

이유: Bing은 검색 엔진이지 LLM 아님. Mistral은 유럽 기반 LLM으로 다양성 추가:
- 미국 LLM(OpenAI·Claude·Gemini·Grok)에 편향된 합의를 견제
- 합리적 가격
- Mistral Large = GPT-4 클래스 성능

API key 발급: https://console.mistral.ai/api-keys/
환경변수: MISTRAL_API_KEY
"""
from __future__ import annotations

import time

import httpx

from .base_adapter import BaseAdapter, LLMResponse


class MistralAdapter(BaseAdapter):
    llm_name = "mistral"
    default_model = "mistral-large-latest"
    env_key = "MISTRAL_API_KEY"
    # Mistral Large pricing (2026-05)
    pricing = {"input_per_1k": 0.004, "output_per_1k": 0.012}

    API_URL = "https://api.mistral.ai/v1/chat/completions"

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
