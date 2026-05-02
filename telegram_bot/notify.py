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
    "site_developer": "🛠 사이트 개발자",
    "ui_designer": "🎨 UI/UX 디자이너",
}

log = logging.getLogger("notify")


def _pages_base_url() -> str | None:
    """GitHub Pages 베이스 URL 추정. 예: https://user.github.io/repo."""
    repo = os.environ.get("GITHUB_REPOSITORY") or ""
    if "/" not in repo:
        return None
    owner, name = repo.split("/", 1)
    if not owner or not name:
        return None
    # owner는 username. github.io는 소문자 변환됨
    return f"https://{owner.lower()}.github.io/{name}"


def notify_new_pending() -> int:
    sent = 0
    pages_base = _pages_base_url()

    for path in sorted(PENDING_DIR.glob("*.json")):
        r = AgentResult.load(path)
        if r.telegram_message_id:
            continue  # 이미 발송됨
        try:
            # 디자인 시안 — 전용 카드 (v1/v2/v3 미리보기 + 채택 버튼)
            if r.kind == "design_variants":
                target = (r.meta or {}).get("target", "hero")
                variants = (r.meta or {}).get("variants") or []
                if not variants:
                    log.warning("design_variants에 variants 비어있음: %s", r.id)
                    continue
                res = tg.send_design_variants_card(
                    result_id=r.id,
                    title=r.title,
                    summary=r.summary or "",
                    target=target,
                    variants=variants,
                    preview_base_url=pages_base,
                )
            else:
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
