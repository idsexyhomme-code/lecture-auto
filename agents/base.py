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

from anthropic import Anthropic

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
    """모든 도메인 에이전트가 상속하는 공용 베이스."""

    name: str = "base"           # 영문 키
    display_name: str = "Base"   # 한글 표시명
    system_prompt: str = ""

    def __init__(self, client: Anthropic | None = None, model: str | None = None):
        self.client = client or Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        self.model = model or os.environ.get("WORKER_MODEL", "claude-sonnet-4-6")

    # ── 호출 ─────────────────────────────────────────────────────
    def call(self, user_prompt: str, *, max_tokens: int = 4000,
             extra_system: str = "") -> str:
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
        # 텍스트 블록만 모아서 반환
        return "".join(b.text for b in msg.content if getattr(b, "type", None) == "text")

    # ── 산출물 빌드 (서브클래스에서 구현) ─────────────────────────
    def run(self, brief: dict) -> list[AgentResult]:
        raise NotImplementedError


def list_pending() -> list[AgentResult]:
    return [AgentResult.load(p) for p in sorted(PENDING_DIR.glob("*.json"))]

def list_approved() -> list[AgentResult]:
    return [AgentResult.load(p) for p in sorted(APPROVED_DIR.glob("*.json"))]
