"""
멀티 LLM 어댑터 모듈 — Core Compass "6 AI 다중 검증" 구현용.

각 어댑터는 동일한 인터페이스 (async generate(prompt, system) -> str)를 가지므로
multi_llm.py에서 일관되게 병렬 호출 가능.

지원 LLM:
- ClaudeAdapter         (Anthropic, claude-sonnet-4-6)
- OpenAIAdapter         (OpenAI, gpt-4o)
- GeminiAdapter         (Google, gemini-2.0-flash)
- PerplexityAdapter     (Perplexity, sonar-pro)
- GrokAdapter           (xAI, grok-2)
- MistralAdapter        (Mistral, mistral-large)
"""
from .base_adapter import BaseAdapter, LLMResponse
from .claude_adapter import ClaudeAdapter
from .openai_adapter import OpenAIAdapter
from .gemini_adapter import GeminiAdapter
from .perplexity_adapter import PerplexityAdapter
from .grok_adapter import GrokAdapter
from .mistral_adapter import MistralAdapter

__all__ = [
    "BaseAdapter",
    "LLMResponse",
    "ClaudeAdapter",
    "OpenAIAdapter",
    "GeminiAdapter",
    "PerplexityAdapter",
    "GrokAdapter",
    "MistralAdapter",
]
