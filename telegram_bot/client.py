"""순수 requests 기반 Telegram Bot API 래퍼.

GitHub Actions에서 짧게 도는 워크플로우라 python-telegram-bot의 비동기 폴러 대신
HTTPS Bot API를 직접 호출하는 단순 함수 묶음으로 충분.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

import requests

log = logging.getLogger("telegram_bot")

API = "https://api.telegram.org/bot{token}/{method}"


def _token() -> str:
    t = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not t:
        raise RuntimeError("TELEGRAM_BOT_TOKEN 환경변수가 비어있습니다.")
    return t


def _chat_id() -> int:
    c = os.environ.get("TELEGRAM_CHAT_ID")
    if not c:
        raise RuntimeError("TELEGRAM_CHAT_ID 환경변수가 비어있습니다.")
    return int(c)


def _call(method: str, **params) -> dict:
    url = API.format(token=_token(), method=method)
    # Telegram long-poll: HTTP timeout은 params["timeout"](Telegram 대기시간)보다
    # 반드시 커야 한다. getUpdates에 timeout=30이면 HTTP는 40초까지 기다린다.
    poll_timeout = 0
    try:
        poll_timeout = int(params.get("timeout", 0) or 0)
    except (TypeError, ValueError):
        poll_timeout = 0
    http_timeout = max(20, poll_timeout + 10)
    r = requests.post(url, json=params, timeout=http_timeout)
    if r.status_code != 200:
        log.error("telegram %s failed: %s %s", method, r.status_code, r.text)
        r.raise_for_status()
    data = r.json()
    if not data.get("ok"):
        raise RuntimeError(f"telegram {method} not ok: {data}")
    return data["result"]


def send_text(text: str, *, chat_id: int | None = None,
              reply_markup: dict | None = None,
              parse_mode: str = "Markdown") -> dict:
    return _call(
        "sendMessage",
        chat_id=chat_id or _chat_id(),
        text=text,
        parse_mode=parse_mode,
        disable_web_page_preview=True,
        **({"reply_markup": reply_markup} if reply_markup else {}),
    )


def send_approval_card(*, result_id: str, title: str, summary: str,
                       agent_label: str, kind: str, body_preview: str,
                       chat_id: int | None = None) -> dict:
    """승인 카드 발송. inline_keyboard로 ✅/❌/👁 버튼."""
    text = (
        f"🟦 *{agent_label}* — `{kind}`\n"
        f"*{_md_escape(title)}*\n\n"
        f"{_md_escape(summary)}\n\n"
        f"━━━━━━━━━━━━━\n"
        f"{_md_escape(body_preview[:600])}{'…' if len(body_preview) > 600 else ''}"
    )
    keyboard = {
        "inline_keyboard": [[
            {"text": "✅ 승인", "callback_data": f"approve:{result_id}"},
            {"text": "✏️ 수정요청", "callback_data": f"revise:{result_id}"},
            {"text": "❌ 거절", "callback_data": f"reject:{result_id}"},
        ], [
            {"text": "👁 전체 보기", "callback_data": f"view:{result_id}"},
        ]]
    }
    return send_text(text, chat_id=chat_id, reply_markup=keyboard)


def send_design_variants_card(*, result_id: str, title: str, summary: str,
                              target: str, variants: list[dict],
                              preview_base_url: str | None,
                              chat_id: int | None = None) -> dict:
    """ui_designer가 만든 3변형 시안 카드.

    variants: [{"id": "v1", "name": "...", "vibe": "...", ...}, ...]
    preview_base_url: GitHub Pages 베이스 URL. 예 "https://user.github.io/repo".
                     None이면 미리보기 링크는 생략하고 텍스트로만.
    """
    lines = [
        f"🎨 *UI/UX 디자이너* — 시안 3변형",
        f"*{_md_escape(title)}*",
        "",
        f"_target_: `{target}`",
    ]
    if summary:
        lines.append("")
        lines.append(_md_escape(summary))
    lines.append("")
    lines.append("━━━━━━━━━━━━━")

    for v in variants:
        vid = v.get("id", "?")
        name = v.get("name", "")
        vibe = v.get("vibe", "")
        lines.append(f"*{vid.upper()} · {_md_escape(name)}*")
        if vibe:
            lines.append(f"_{_md_escape(vibe)}_")
        if preview_base_url:
            lines.append(
                f"👁 [미리보기]({preview_base_url}/_design_previews/{result_id}/{vid}.html)"
            )
        lines.append("")

    if preview_base_url:
        lines.append("_미리보기 링크는 30~60초 후 활성화됩니다 (Pages 배포 대기)._")

    text = "\n".join(lines)

    # 버튼 — variant 수만큼 ✅vN + 거절
    button_row = []
    for v in variants:
        vid = v.get("id", "?")
        button_row.append({
            "text": f"✅ {vid.upper()} 채택",
            "callback_data": f"design-pick:{result_id}:{vid}",
        })
    keyboard = {
        "inline_keyboard": [
            button_row,
            [
                {"text": "🔁 모두 거절·재의뢰", "callback_data": f"design-reject:{result_id}"},
                {"text": "👁 본문 보기", "callback_data": f"view:{result_id}"},
            ],
        ]
    }
    return send_text(text, chat_id=chat_id, reply_markup=keyboard)


def get_updates(offset: int | None = None, timeout: int = 0) -> list[dict]:
    params: dict[str, Any] = {"timeout": timeout, "allowed_updates": ["callback_query", "message"]}
    if offset is not None:
        params["offset"] = offset
    return _call("getUpdates", **params)


def answer_callback(callback_query_id: str, text: str = "", show_alert: bool = False):
    return _call(
        "answerCallbackQuery",
        callback_query_id=callback_query_id,
        text=text[:200],
        show_alert=show_alert,
    )


def edit_message_reply_markup(chat_id: int, message_id: int, reply_markup: dict | None = None):
    return _call(
        "editMessageReplyMarkup",
        chat_id=chat_id,
        message_id=message_id,
        **({"reply_markup": reply_markup} if reply_markup is not None else {"reply_markup": {"inline_keyboard": []}}),
    )


def edit_message_text(chat_id: int, message_id: int, text: str, *, parse_mode: str = "Markdown"):
    return _call(
        "editMessageText",
        chat_id=chat_id,
        message_id=message_id,
        text=text,
        parse_mode=parse_mode,
        disable_web_page_preview=True,
    )


# ── 마크다운 안전 처리 ────────────────────────────────────────────
_MD_ESCAPE = ("_", "*", "`", "[")


def _md_escape(s: str) -> str:
    """텔레그램 Markdown(legacy) 모드에서 깨질 만한 문자 escape."""
    out = s
    for ch in _MD_ESCAPE:
        out = out.replace(ch, "\\" + ch)
    return out
