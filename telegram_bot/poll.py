"""텔레그램 콜백/메시지 폴링 → pending 항목을 approved/rejected로 이동.

state/telegram_offset.json에 마지막 update_id를 저장해 중복 처리 방지.
"""
from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.base import PENDING_DIR, APPROVED_DIR, REJECTED_DIR, STATE_DIR, REPO_ROOT, AgentResult
from telegram_bot import client as tg

OFFSET_FILE = STATE_DIR / "telegram_offset.json"
SITE_CONFIG_PATH = REPO_ROOT / "site_config.json"
log = logging.getLogger("poll")


def _load_offset() -> int | None:
    if not OFFSET_FILE.exists():
        return None
    return json.loads(OFFSET_FILE.read_text(encoding="utf-8")).get("offset")


def _save_offset(offset: int):
    OFFSET_FILE.write_text(json.dumps({"offset": offset}, ensure_ascii=False, indent=2), encoding="utf-8")


def _find_pending(result_id: str) -> Path | None:
    p = PENDING_DIR / f"{result_id}.json"
    return p if p.exists() else None


def _move(src: Path, dst_dir: Path) -> Path:
    dst = dst_dir / src.name
    src.replace(dst)
    return dst


def handle_callback(cq: dict):
    data = cq.get("data", "")
    msg = cq.get("message", {})
    chat_id = msg.get("chat", {}).get("id")
    message_id = msg.get("message_id")

    if ":" not in data:
        tg.answer_callback(cq["id"], "알 수 없는 명령")
        return

    action, result_id = data.split(":", 1)
    p = _find_pending(result_id)

    if not p:
        tg.answer_callback(cq["id"], "이미 처리되었거나 만료된 카드입니다.")
        try:
            tg.edit_message_reply_markup(chat_id, message_id, None)
        except Exception:
            pass
        return

    r = AgentResult.load(p)

    if action == "approve":
        r.status = "approved"
        r.save(p.parent)
        _move(p, APPROVED_DIR)

        # site_developer가 만든 메타데이터 변경은 즉시 site_config.json에 적용
        if r.kind == "site_config_change":
            new_cfg = r.meta.get("new_config") if r.meta else None
            if isinstance(new_cfg, dict):
                SITE_CONFIG_PATH.write_text(
                    json.dumps(new_cfg, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                log.info("site_config.json updated from %s", r.id)

        tg.answer_callback(cq["id"], "✅ 승인 완료 — 사이트에 반영됩니다")
        tg.edit_message_text(
            chat_id, message_id,
            f"✅ *승인됨* — `{r.kind}`\n*{r.title}*\n\n다음 빌드에서 사이트에 반영돼요.",
        )

    elif action == "reject":
        r.status = "rejected"
        r.save(p.parent)
        _move(p, REJECTED_DIR)
        tg.answer_callback(cq["id"], "❌ 거절 완료")
        tg.edit_message_text(
            chat_id, message_id,
            f"❌ *거절됨* — `{r.kind}`\n*{r.title}*",
        )

    elif action == "revise":
        # 사용자가 수정요청을 표시한 상태로만 둔다 (실제 재생성은 다음 단계)
        tg.answer_callback(cq["id"], "수정요청 표시 — 답장으로 수정사항을 보내주세요")
        tg.edit_message_text(
            chat_id, message_id,
            f"✏️ *수정요청 대기* — `{r.kind}`\n*{r.title}*\n\n"
            f"이 메시지에 답장(reply)으로 수정 지시를 보내주세요. 다음 실행에서 반영됩니다.",
        )
        # state에 revise 표시
        r.meta["revise_requested"] = True
        r.save(p.parent)

    elif action == "view":
        # 본문 전체를 새 메시지로 발송
        tg.answer_callback(cq["id"], "전체 본문 전송")
        tg.send_text(f"*{r.title}*\n\n{r.body_md[:3500]}")

    else:
        tg.answer_callback(cq["id"], "알 수 없는 액션")


def handle_message(m: dict):
    """텍스트 메시지/명령 처리. 현재는 reply 기반 ‘revise 지시’만 인식."""
    reply_to = m.get("reply_to_message")
    text = m.get("text", "").strip()
    if not text:
        return
    if reply_to and reply_to.get("from", {}).get("is_bot"):
        # 사용자가 봇 카드에 답장을 달았다 → revise instruction
        # message_id로 매칭
        target_id = reply_to.get("message_id")
        # pending/rejected 어디에 있어도 찾기
        for d in (PENDING_DIR, REJECTED_DIR):
            for p in d.glob("*.json"):
                r = AgentResult.load(p)
                if r.telegram_message_id == target_id:
                    r.meta.setdefault("revise_log", []).append({"text": text})
                    r.meta["revise_requested"] = True
                    r.save(d)
                    tg.send_text(
                        f"📝 수정 지시 저장됨 — `{r.id}`\n다음 실행에서 반영합니다.",
                    )
                    return
    if text.startswith("/help") or text == "/start":
        tg.send_text(
            "안녕하세요. 강의 자동화 컨트롤 패널입니다.\n\n"
            "- ✅/❌ 버튼으로 승인·거절\n"
            "- ✏️ 누르고 답장(reply)으로 수정 지시\n"
            "- /pending — 대기 중인 항목 목록\n"
        )
    elif text.startswith("/pending"):
        items = list(PENDING_DIR.glob("*.json"))
        tg.send_text(f"대기 중: {len(items)}건")


def run() -> int:
    offset = _load_offset()
    next_offset = offset + 1 if offset is not None else None
    updates = tg.get_updates(offset=next_offset)
    if not updates:
        log.info("no updates")
        return 0
    last_id = offset or 0
    for u in updates:
        last_id = max(last_id, u["update_id"])
        try:
            if "callback_query" in u:
                handle_callback(u["callback_query"])
            elif "message" in u:
                handle_message(u["message"])
        except Exception as e:
            log.exception("update %s failed: %s", u.get("update_id"), e)
    _save_offset(last_id)
    return len(updates)


if __name__ == "__main__":
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s [%(name)s] %(message)s",
    )
    n = run()
    print(f"Processed {n} update(s)")
