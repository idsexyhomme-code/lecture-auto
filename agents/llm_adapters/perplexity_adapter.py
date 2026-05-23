"""Perplexity adapter — 6 AI 중 #4.

Perplexity는 검색 기반 LLM — 최신 시장 정보 가져올 때 강력.
1인 사업 진단에서 "최신 시장 트렌드" 영역 담당.

API key 발급: https://www.perplexity.ai/settings/api
환경변수: PERPLEXITY_API_KEY
"""
from __future__ import annotations

import time

import httpx

from .base_adapter import BaseAdapter, LLMResponse


class PerplexityAdapter(BaseAdapter):
    llm_name = "perplexity"
    default_model = "sonar-pro"
    env_key = "PERPLEXITY_API_KEY"
    # Sonar Pro pricing (2026-05)
    pricing = {"input_per_1k": 0.003, "output_per_1k": 0.015}

    API_URL = "https://api.perplexity.ai/chat/completions"

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
                # Perplexity는 검색 출처를 함께 반환 — meta에 저장
                meta={"citations": data.get("citations", [])},
            )
        except Exception as e:
            return LLMResponse(
                llm=self.llm_name, model=self.model, text="", success=False,
                latency_ms=int((time.time() - t0) * 1000),
                error=f"{type(e).__name__}: {str(e)[:200]}",
            )
