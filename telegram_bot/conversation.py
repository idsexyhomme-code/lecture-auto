"""Idea Intake 대화 영속화.

대화 한 세션 = JSON 파일 한 개 (content/conversations/<id>.json).
같은 chat_id에서 status="active"인 가장 최근 대화를 이어쓰고, READY/cancelled 등
종료 상태가 되면 새 대화를 시작.

데이터 구조:
  id: "<unix_ts>-<chat_id>"
  chat_id: telegram chat id (정수)
  status: "active" | "ready" | "approved" | "rejected" | "cancelled"
  history: [{"role": "user"|"assistant", "content": str}, ...]
  draft_brief: { "agent": "...", "brief": {...} } | null   (READY 도달 시)
  last_telegram_message_id: int | null   (봇의 가장 최근 응답 message_id)
  created_at, updated_at: ISO8601 UTC
"""
from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# 부모 디렉토리(repo root)를 path에 추가 — agents.base 사용 위해
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agents.base import CONVERSATIONS_DIR  # noqa: E402

# 활성 대화 만료 — 24시간 이상 응답 없으면 stale로 간주, 새 대화 시작
ACTIVE_TTL_SECONDS = 24 * 60 * 60


@dataclass
class Conversation:
    id: str
    chat_id: int
    status: str = "active"
    history: list = field(default_factory=list)
    draft_brief: Optional[dict] = None
    last_telegram_message_id: Optional[int] = None
    created_at: str = ""
    updated_at: str = ""

    # ── 생성 ──────────────────────────────────────────
    @classmethod
    def new(cls, chat_id: int) -> "Conversation":
        now = _now_iso()
        return cls(
            id=f"{int(time.time())}-{chat_id}",
            chat_id=chat_id,
            status="active",
            history=[],
            draft_brief=None,
            last_telegram_message_id=None,
            created_at=now,
            updated_at=now,
        )

    # ── 조회 ──────────────────────────────────────────
    @classmethod
    def load_active(cls, chat_id: int) -> Optional["Conversation"]:
        """같은 chat_id에서 status="active"인 가장 최근 대화 (TTL 안에 있는)."""
        candidates = []
        cutoff = time.time() - ACTIVE_TTL_SECONDS
        for p in CONVERSATIONS_DIR.glob("*.json"):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                continue
            if data.get("chat_id") != chat_id:
                continue
            if data.get("status") != "active":
                continue
            # mtime 기반 TTL 체크 (updated_at 파싱보다 단순)
            if p.stat().st_mtime < cutoff:
                continue
            candidates.append((p.stat().st_mtime, data))
        if not candidates:
            return None
        candidates.sort(reverse=True)
        data = candidates[0][1]
        # dataclass 초기화 시 모르는 키는 무시
        keys = {f.name for f in cls.__dataclass_fields__.values()}
        clean = {k: v for k, v in data.items() if k in keys}
        return cls(**clean)

    @classmethod
    def load(cls, conv_id: str) -> Optional["Conversation"]:
        p = CONVERSATIONS_DIR / f"{conv_id}.json"
        if not p.exists():
            return None
        data = json.loads(p.read_text(encoding="utf-8"))
        keys = {f.name for f in cls.__dataclass_fields__.values()}
        clean = {k: v for k, v in data.items() if k in keys}
        return cls(**clean)

    # ── 저장 ──────────────────────────────────────────
    def save(self) -> Path:
        self.updated_at = _now_iso()
        p = CONVERSATIONS_DIR / f"{self.id}.json"
        p.write_text(
            json.dumps(asdict(self), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return p

    # ── 헬퍼 ──────────────────────────────────────────
    def append_user(self, text: str):
        self.history.append({"role": "user", "content": text})

    def append_assistant(self, payload: dict):
        """LLM 응답(JSON dict)을 문자열로 history에 누적."""
        self.history.append({
            "role": "assistant",
            "content": json.dumps(payload, ensure_ascii=False),
        })

    def mark_ready(self, brief: dict):
        self.status = "ready"
        self.draft_brief = brief

    def mark_approved(self):
        self.status = "approved"

    def mark_rejected(self):
        self.status = "rejected"

    def mark_cancelled(self):
        self.status = "cancelled"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
