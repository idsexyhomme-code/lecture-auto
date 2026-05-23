"""Google Gemini adapter — 6 AI 중 #3.

Gemini API key 발급: https://aistudio.google.com/apikey (무료 tier 있음).
환경변수: GOOGLE_GENERATIVEAI_API_KEY 또는 GEMINI_API_KEY
"""
from __future__ import annotations

import os
import time

from .base_adapter import BaseAdapter, LLMResponse


class GeminiAdapter(BaseAdapter):
    llm_name = "gemini"
    default_model = "gemini-2.0-flash"
    env_key = "GOOGLE_GENERATIVEAI_API_KEY"
    # Gemini 2.0 Flash pricing (2026-05) — 매우 저렴
    pricing = {"input_per_1k": 0.000075, "output_per_1k": 0.0003}

    def __init__(self, model: str | None = None, api_key: str | None = None):
        super().__init__(model=model, api_key=api_key)
        # 폴백: GEMINI_API_KEY로도 시도
        if not self.api_key:
            self.api_key = os.environ.get("GEMINI_API_KEY", "")
            self.enabled = bool(self.api_key and not self.api_key.startswith("sk-..."))
        self._client = None

    @property
    def client(self):
        if self._client is None:
            from google import genai
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    async def generate(self, prompt: str, system: str = "",
                       max_tokens: int = 2000) -> LLMResponse:
        if not self.enabled:
            return self.disabled_response()

        t0 = time.time()
        try:
            # Gemini는 system을 별도 필드로 받음
            full_prompt = prompt if not system else f"{system}\n\n---\n\n{prompt}"

            # google-genai SDK는 sync API — asyncio.to_thread로 비동기화
            import asyncio
            res = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model,
                contents=full_prompt,
            )
            text = res.text or ""
            usage = getattr(res, "usage_metadata", None)
            in_tok = getattr(usage, "prompt_token_count", 0) if usage else 0
            out_tok = getattr(usage, "candidates_token_count", 0) if usage else 0
            return LLMResponse(
                llm=self.llm_name, model=self.model, text=text, success=True,
                latency_ms=int((time.time() - t0) * 1000),
                input_tokens=in_tok, output_tokens=out_tok,
                cost_usd=self.estimate_cost(in_tok, out_tok),
            )
        except ImportError:
            return LLMResponse(
                llm=self.llm_name, model=self.model, text="", success=False,
                error="google-genai 패키지 미설치 — pip install google-genai>=0.7",
            )
        except Exception as e:
            return LLMResponse(
                llm=self.llm_name, model=self.model, text="", success=False,
                latency_ms=int((time.time() - t0) * 1000),
                error=f"{type(e).__name__}: {str(e)[:200]}",
            )
