"""모든 도메인 에이전트의 공용 베이스 클래스."""
from __future__ import annotations

import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from anthropic import Anthropic, AsyncAnthropic

REPO_ROOT = Path(__file__).resolve().parents[1]
PENDING_DIR = REPO_ROOT / "content" / "pending"
APPROVED_DIR = REPO_ROOT / "content" / "approved"
REJECTED_DIR = REPO_ROOT / "content" / "rejected"
STATE_DIR = REPO_ROOT / "content" / "state"
CONVERSATIONS_DIR = REPO_ROOT / "content" / "conversations"

for d in (PENDING_DIR, APPROVED_DIR, REJECTED_DIR, STATE_DIR, CONVERSATIONS_DIR):
    d.mkdir(parents=True, exist_ok=True)

log = logging.getLogger("agents")


@dataclass
class AgentResult:
    """에이전트가 만든 단일 산출물."""
    id: str
    agent: str            # "curriculum" | "producer" | "marketing" | "success"
    kind: str             # "curriculum_outline" | "lecture_script" | "landing_copy" | ...
    title: str
    body_md: str
    summary: str          # 텔레그램 카드용 한 줄 요약 (≤120자)
    meta: dict = field(default_factory=dict)
    course_id: str = ""
    created_at: str = ""
    status: str = "pending"   # pending → approved | rejected
    telegram_message_id: int | None = None

    @classmethod
    def new(cls, agent: str, kind: str, title: str, body_md: str,
            summary: str, course_id: str = "", meta: dict | None = None) -> "AgentResult":
        return cls(
            id=f"{int(time.time())}-{uuid.uuid4().hex[:6]}",
            agent=agent,
            kind=kind,
            title=title.strip(),
            body_md=body_md.strip(),
            summary=summary.strip()[:120],
            meta=meta or {},
            course_id=course_id,
            created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        )

    # ── 영속화 ────────────────────────────────────────────────────
    def path(self, dir_: Path) -> Path:
        return dir_ / f"{self.id}.json"

    def save(self, dir_: Path) -> Path:
        p = self.path(dir_)
        p.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8")
        return p

    @classmethod
    def load(cls, path: Path) -> "AgentResult":
        return cls(**json.loads(path.read_text(encoding="utf-8")))


class BaseAgent:
    """모든 도메인 에이전트가 상속하는 공용 베이스.

    동기 .call() 과 비동기 .acall() 둘 다 지원.
    - 직렬 처리(기존): 그대로 .call() 사용 (변경 없음)
    - 병렬 처리(Phase 1 P2 worker_pool): .acall() + asyncio.gather()
    """

    name: str = "base"           # 영문 키
    display_name: str = "Base"   # 한글 표시명
    system_prompt: str = ""

    # async client는 lazy init — 동기 워크플로우에서는 만들지 않음
    _async_client: AsyncAnthropic | None = None

    def __init__(self, client: Anthropic | None = None, model: str | None = None,
                 async_client: AsyncAnthropic | None = None):
        self.client = client or Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        self.model = model or os.environ.get("WORKER_MODEL", "claude-sonnet-4-6")
        if async_client is not None:
            self._async_client = async_client

    @property
    def async_client(self) -> AsyncAnthropic:
        """비동기 클라이언트 — 처음 .acall() 호출 시 lazy 생성."""
        if self._async_client is None:
            self._async_client = AsyncAnthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        return self._async_client

    # ── 동기 호출 (기존 직렬 워크플로우 그대로) ─────────────────────
    def call(self, user_prompt: str, *, max_tokens: int = 4000,
             extra_system: str = "") -> str:
        # 비용 가드 (Step 27) — 한도 초과 시 즉시 차단
        try:
            from .budget_guard import check_budget, record_usage
            ok, current, cap = check_budget(agent=self.name)
            if not ok:
                raise RuntimeError(
                    f"DAILY_BUDGET_USD 한도 초과: {current:.4f}/{cap:.2f} USD — "
                    f"agent={self.name} 호출 거부. 한도 상향 또는 다음날까지 대기."
                )
        except ImportError:
            pass

        sys = self.system_prompt
        if extra_system:
            sys = sys + "\n\n" + extra_system
        log.info("[%s] calling model=%s", self.name, self.model)
        msg = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=sys,
            messages=[{"role": "user", "content": user_prompt}],
        )

        # 비용 기록 (Step 18)
        try:
            from .budget_guard import record_usage
            usage = getattr(msg, "usage", None)
            if usage:
                record_usage(
                    agent=self.name,
                    model=self.model,
                    input_tokens=usage.input_tokens,
                    output_tokens=usage.output_tokens,
                )
        except Exception:
            pass

        # 텍스트 블록만 모아서 반환
        return "".join(b.text for b in msg.content if getattr(b, "type", None) == "text")

    # ── 비동기 호출 (Phase 1·2 병렬 처리용) ─────────────────────────
    async def acall(self, user_prompt: str, *, max_tokens: int = 4000,
                    extra_system: str = "") -> str:
        """동일한 의미·시그니처. asyncio.gather()로 N개 동시 호출 가능.

        Anthropic API는 IO 작업이므로 asyncio가 효율적이다 (CPU bound 아님).
        예시:
            results = await asyncio.gather(
                agent_a.acall("prompt 1"),
                agent_b.acall("prompt 2"),
                agent_c.acall("prompt 3"),
            )
        """
        sys = self.system_prompt
        if extra_system:
            sys = sys + "\n\n" + extra_system
        # 비용 가드
        try:
            from .budget_guard import check_budget
            ok, current, cap = check_budget(agent=self.name)
            if not ok:
                raise RuntimeError(
                    f"DAILY_BUDGET_USD 한도 초과: {current:.4f}/{cap:.2f} USD — "
                    f"agent={self.name} async 호출 거부."
                )
        except ImportError:
            pass

        log.info("[%s] async calling model=%s", self.name, self.model)
        msg = await self.async_client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=sys,
            messages=[{"role": "user", "content": user_prompt}],
        )

        try:
            from .budget_guard import record_usage
            usage = getattr(msg, "usage", None)
            if usage:
                record_usage(
                    agent=self.name, model=self.model,
                    input_tokens=usage.input_tokens, output_tokens=usage.output_tokens,
                )
        except Exception:
            pass

        return "".join(b.text for b in msg.content if getattr(b, "type", None) == "text")

    # ── 자기 검수 (F1 — 룰 기반, LLM 호출 X — 빠름) ────────────────
    # 헌법 §4 hard ban — 1개라도 들어가면 fail
    HARD_BANNED = [
        "월 1000만 원 자동 수익", "월 천만 원 자동", "하루 10분으로 자동화 완성",
        "100% 보장", "100% 환불 보장", "획기적인 자동 수익",
        "누구나 쉽게 돈 버는", "클릭 몇 번으로 사업 자동화",
        "투자 없이 월 수익", "원금 보장",
    ]
    # 헌법 §8 soft ban — 들어가면 경고 (재생성 시도 후보)
    SOFT_BANNED = [
        "워크플로우", "워크플로", "솔루션", "효율적", "체계적", "최적화",
        "자동화 시스템", "AI 활용", "혁신적", "획기적", "패러다임",
        "여러분", "한 차원 높은", "바쁜 일상 속에서도", "고민이 있으신가요",
        "산출물",
    ]

    @classmethod
    def self_review(cls, text: str, *, kind: str = "", min_len: int = 80) -> dict:
        """결과 텍스트를 룰 기반으로 1차 검사. LLM 호출 없음 — 즉시.

        Returns dict:
            ok: bool — 통과 여부 (hard 위반 X, empty X)
            severity: "pass" | "warn" | "fail"
            hard_violations: list[str] — §4 금기 매치
            soft_violations: list[str] — §8 금기 매치 (최대 10개)
            len: int
            checks: dict (각 항목 OK/FAIL)
        """
        text = text or ""
        text_strip = text.strip()

        hard_hits = [w for w in cls.HARD_BANNED if w in text]
        soft_hits = [w for w in cls.SOFT_BANNED if w in text]
        empty = not text_strip
        too_short = len(text_strip) < min_len

        # 결과
        if empty or hard_hits:
            severity = "fail"
        elif too_short or len(soft_hits) >= 3:
            severity = "warn"
        elif soft_hits:
            severity = "warn"
        else:
            severity = "pass"

        return {
            "ok": severity != "fail",
            "severity": severity,
            "hard_violations": hard_hits,
            "soft_violations": soft_hits[:10],
            "len": len(text_strip),
            "checks": {
                "no_hard_ban": not hard_hits,
                "no_empty": not empty,
                "min_length": not too_short,
                "soft_ban_count": len(soft_hits),
            },
        }

    # ── 산출물 빌드 (서브클래스에서 구현) ─────────────────────────
    def run(self, brief: dict) -> list[AgentResult]:
        raise NotImplementedError

    async def arun(self, brief: dict) -> list[AgentResult]:
        """비동기 버전 run(). 기본은 동기 run()을 thread pool에서 실행.

        에이전트가 *.acall()*을 본격적으로 쓰려면 이 메서드를 override해서
        내부 호출을 .acall()로 바꿔야 진짜 비동기 효과 (CPU 점유 해제).
        그렇지 않으면 *동기 run()을 별도 스레드에서 실행*하는 fallback.
        """
        import asyncio
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.run, brief)


def list_pending() -> list[AgentResult]:
    return [AgentResult.load(p) for p in sorted(PENDING_DIR.glob("*.json"))]

def list_approved() -> list[AgentResult]:
    return [AgentResult.load(p) for p in sorted(APPROVED_DIR.glob("*.json"))]
