"""pending에 새로 들어온 결과물을 텔레그램으로 발송하는 1회 실행 스크립트.

이미 발송된 항목은 result.json의 telegram_message_id로 식별해 중복 발송 방지.
"""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

# repo root를 path에 추가
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.base import PENDING_DIR, AgentResult
from telegram_bot import client as tg

LABEL = {
    "curriculum": "📚 강의 기획",
    "producer": "🎬 콘텐츠 제작",
    "marketing": "📣 홍보·마케팅",
    "success": "🎓 수강생 관리",
}

log = logging.getLogger("notify")


def notify_new_pending() -> int:
    sent = 0
    for path in sorted(PENDING_DIR.glob("*.json")):
        r = AgentResult.load(path)
        if r.telegram_message_id:
            continue  # 이미 발송됨
        try:
            res = tg.send_approval_card(
                result_id=r.id,
                title=r.title,
                summary=r.summary or "(요약 없음)",
                agent_label=LABEL.get(r.agent, r.agent),
                kind=r.kind,
                body_preview=r.body_md,
            )
            r.telegram_message_id = res["message_id"]
            r.save(PENDING_DIR)
            sent += 1
            log.info("sent %s → message_id=%s", r.id, res["message_id"])
        except Exception as e:
            log.exception("send failed for %s: %s", r.id, e)
    return sent


if __name__ == "__main__":
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s [%(name)s] %(message)s",
    )
    n = notify_new_pending()
    print(f"Sent {n} new approval cards.")
