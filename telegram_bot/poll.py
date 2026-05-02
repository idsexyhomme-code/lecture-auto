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
from telegram_bot.conversation import Conversation

import requests

OFFSET_FILE = STATE_DIR / "telegram_offset.json"
SITE_CONFIG_PATH = REPO_ROOT / "site_config.json"


def _dispatch_agent_loop() -> bool:
    """Step 4 — GH_PAT secret이 있으면 GitHub Actions API로 새 사이클 즉시 트리거.
    없으면 False 반환하고 cron(3분) 대기.
    """
    pat = os.environ.get("GH_PAT")
    if not pat:
        log.info("GH_PAT 없음 — 다음 cron 사이클 대기")
        return False
    repo = os.environ.get("GITHUB_REPOSITORY") or "idsexyhomme-code/lecture-auto"
    url = f"https://api.github.com/repos/{repo}/actions/workflows/agent-loop.yml/dispatches"
    try:
        r = requests.post(
            url,
            json={"ref": "main"},
            headers={
                "Authorization": f"Bearer {pat}",
                "Accept": "application/vnd.github+json",
                "User-Agent": "core-campus-bot",
            },
            timeout=15,
        )
        ok = r.status_code in (200, 201, 204)
        if not ok:
            log.warning("dispatch failed: %s %s", r.status_code, r.text[:200])
        return ok
    except Exception as e:
        log.exception("dispatch exception: %s", e)
        return False
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


def _handle_intake_callback(cq: dict, chat_id, message_id):
    """Step 3 — Idea Intake brief preview 카드의 ✅/✏️/❌ 콜백."""
    import time as _time
    data = cq["data"]
    action, conv_id = data.split(":", 1)

    conv = Conversation.load(conv_id)
    if not conv:
        tg.answer_callback(cq["id"], "이미 처리된 대화입니다")
        try:
            tg.edit_message_reply_markup(chat_id, message_id, None)
        except Exception:
            pass
        return

    if action == "intake-approve":
        # brief을 briefs/에 저장 (다음 사이클에서 conductor가 처리)
        brief_payload = conv.draft_brief
        if not brief_payload or not isinstance(brief_payload, dict):
            tg.answer_callback(cq["id"], "brief 정보가 없습니다")
            return
        slug_part = (brief_payload.get("brief", {}) or {}).get("course_id") or "intake"
        # course_id에 한글 들어가면 슬러그화
        import re
        slug_part = re.sub(r"[^0-9A-Za-z\-_]", "", str(slug_part))[:30] or "intake"
        ts = int(_time.time())
        brief_path = REPO_ROOT / "briefs" / f"intake-{slug_part}-{ts}.json"
        brief_path.write_text(
            json.dumps(brief_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        conv.mark_approved()
        conv.save()

        # Step 4 — 즉시 새 사이클 트리거 (GH_PAT 있으면)
        dispatched = _dispatch_agent_loop()
        suffix = (
            "⚡ *자동 트리거됨* — 약 1~2분 후 산출물 카드가 도착합니다."
            if dispatched
            else "다음 사이클(3분 cron)에서 처리됩니다."
        )

        tg.answer_callback(cq["id"], "✅ brief 등록")
        tg.edit_message_text(
            chat_id, message_id,
            "✅ *승인됨*\n\nbrief이 큐에 들어갔어요. " + suffix + f"\n\n_파일: `{brief_path.name}`_",
        )
        return

    if action == "intake-reject":
        conv.mark_rejected()
        conv.save()
        tg.answer_callback(cq["id"], "❌ 취소됨")
        tg.edit_message_text(
            chat_id, message_id,
            "❌ *취소됨*\n\n새 아이디어가 떠오르면 한 줄로 보내주세요.",
        )
        return

    if action == "intake-revise":
        # 대화를 active로 되돌려 추가 답변 받음
        conv.status = "active"
        conv.draft_brief = None
        conv.save()
        tg.answer_callback(cq["id"], "✏️ 수정 모드 — 무엇을 바꿀지 답해주세요")
        tg.edit_message_text(
            chat_id, message_id,
            "✏️ *수정 모드*\n\n어떻게 바꿀까요? 한 줄로 답해주세요. 예:\n"
            "- _8차시로 줄여줘_\n"
            "- _타깃을 초보자로 바꿔줘_\n"
            "- _형식은 video로_",
        )
        return

    tg.answer_callback(cq["id"], "알 수 없는 액션")


def _handle_design_callback(cq: dict, chat_id, message_id):
    """ui_designer 시안 카드의 ✅vN 채택 / 모두 거절 콜백."""
    import time as _time
    data = cq["data"]

    # design-pick:{result_id}:{vN}  또는  design-reject:{result_id}
    parts = data.split(":")
    action = parts[0]
    result_id = parts[1] if len(parts) >= 2 else ""

    p = _find_pending(result_id)
    if not p:
        tg.answer_callback(cq["id"], "이미 처리된 시안입니다")
        try:
            tg.edit_message_reply_markup(chat_id, message_id, None)
        except Exception:
            pass
        return

    r = AgentResult.load(p)

    if action == "design-reject":
        r.status = "rejected"
        r.save(p.parent)
        _move(p, REJECTED_DIR)
        tg.answer_callback(cq["id"], "🔁 시안 모두 거절")
        tg.edit_message_text(
            chat_id, message_id,
            f"🔁 *시안 모두 거절됨*\n*{r.title}*\n\n새로 의뢰하시려면 한 줄 보내주세요.",
        )
        return

    if action == "design-pick":
        if len(parts) < 3:
            tg.answer_callback(cq["id"], "버전이 지정되지 않았습니다")
            return
        vid = parts[2]
        variants = (r.meta or {}).get("variants") or []
        chosen = next((v for v in variants if v.get("id") == vid), None)
        if not chosen:
            tg.answer_callback(cq["id"], f"variant {vid}를 찾지 못했습니다")
            return

        target = (r.meta or {}).get("target", "hero")

        # 1) 디자인 결과 자체는 approved로 이동 + 선택된 variant 표시
        r.status = "approved"
        r.meta["chosen_variant_id"] = vid
        r.save(p.parent)
        _move(p, APPROVED_DIR)

        # 2) ★ site_developer 우회 — site_config.json에 직접 적용
        #    (LLM 두 번 거치면 응답이 잘려 JSONDecodeError, 또 비용 낭비)
        applied_keys = []
        try:
            cfg: dict = {}
            if SITE_CONFIG_PATH.exists():
                cfg = json.loads(SITE_CONFIG_PATH.read_text(encoding="utf-8"))

            # target별 슬롯 매핑
            slot_map = {
                "hero": "hero_html",
                "home_intro": "home_intro_html",
                "footer": "footer_html",
            }
            chosen_html = chosen.get("html", "") or ""

            if target in slot_map:
                cfg[slot_map[target]] = chosen_html
                applied_keys.append(slot_map[target])
            elif target == "landing_full":
                # 통째 시안이면 hero_html에 넣음 (추후 분할 휴리스틱 가능)
                cfg["hero_html"] = chosen_html
                applied_keys.append("hero_html")

            # design_tokens는 *기존 토큰 위에 덮어쓰기*
            chosen_tokens = chosen.get("design_tokens") or {}
            if chosen_tokens:
                existing = cfg.get("design_tokens") or {}
                if not isinstance(existing, dict):
                    existing = {}
                existing.update(chosen_tokens)
                cfg["design_tokens"] = existing
                applied_keys.append(f"design_tokens(+{len(chosen_tokens)})")

            SITE_CONFIG_PATH.write_text(
                json.dumps(cfg, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            log.info("design v%s applied to site_config.json — %s", vid, applied_keys)
        except Exception as e:
            log.exception("design apply failed: %s", e)
            tg.answer_callback(cq["id"], "적용 실패 — 로그 확인")
            tg.edit_message_text(
                chat_id, message_id,
                f"⚠️ *적용 실패* — `{type(e).__name__}: {str(e)[:200]}`",
            )
            return

        # 3) 빌드만 트리거 (LLM 호출 없음 — 빠름)
        dispatched = _dispatch_agent_loop()
        suffix = (
            "⚡ *자동 트리거됨* — 30~60초 안에 사이트에 반영됩니다."
            if dispatched
            else "다음 cron 사이클(3분)에서 빌드·배포됩니다."
        )

        applied_summary = ", ".join(applied_keys) if applied_keys else "(없음)"
        tg.answer_callback(cq["id"], f"✅ {vid.upper()} 적용 완료")
        tg.edit_message_text(
            chat_id, message_id,
            f"✅ *시안 {vid.upper()} 적용됨* — _{chosen.get('name', '')}_\n\n"
            f"📦 적용된 항목: `{applied_summary}`\n"
            f"{suffix}",
        )
        return

    tg.answer_callback(cq["id"], "알 수 없는 디자인 액션")


def handle_callback(cq: dict):
    data = cq.get("data", "")
    msg = cq.get("message", {})
    chat_id = msg.get("chat", {}).get("id")
    message_id = msg.get("message_id")

    if ":" not in data:
        tg.answer_callback(cq["id"], "알 수 없는 명령")
        return

    # Step 3 — Idea Intake 콜백
    if data.startswith("intake-"):
        return _handle_intake_callback(cq, chat_id, message_id)

    # ui_designer 시안 카드 콜백
    if data.startswith("design-"):
        return _handle_design_callback(cq, chat_id, message_id)

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
    """텍스트 메시지/명령 처리.

    우선순위:
      1) 봇 카드에 reply → revise 지시
      2) 명령어(/start, /pending, /cancel 등)
      3) 일반 텍스트 → idea_intake 대화 라우팅
    """
    text = m.get("text", "").strip()
    chat_id = m.get("chat", {}).get("id")
    if not text:
        return

    # 1) 봇 카드 reply → revise (기존 흐름)
    reply_to = m.get("reply_to_message")
    if reply_to and reply_to.get("from", {}).get("is_bot"):
        target_id = reply_to.get("message_id")
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

    # 2) 명령어
    if text == "/start" or text.startswith("/help"):
        tg.send_text(
            "*코어 캠퍼스 컨트롤 패널*\n\n"
            "✏️ *아이디어 대화* — 그냥 한 줄로 보내세요. 예: `Claude로 영상 자동화 SOP 시리즈 만들어줘`\n"
            "✅/❌ — 카드 도착 시 승인·거절\n"
            "📨 카드에 reply — 수정 지시\n\n"
            "_명령어_:\n"
            "/pending — 대기 중 항목\n"
            "/conv — 진행 중인 대화 상태\n"
            "/cancel — 진행 중인 대화 취소\n",
        )
        return
    if text.startswith("/pending"):
        items = list(PENDING_DIR.glob("*.json"))
        tg.send_text(f"대기 중: {len(items)}건", chat_id=chat_id)
        return
    if text.startswith("/conv"):
        conv = Conversation.load_active(chat_id) if chat_id else None
        if not conv:
            tg.send_text("진행 중인 대화가 없습니다. 새 아이디어를 한 줄로 보내주세요.", chat_id=chat_id)
        else:
            turns = sum(1 for h in conv.history if h.get("role") == "user")
            tg.send_text(
                f"진행 중인 대화 — {turns}턴\n상태: `{conv.status}`\n_/cancel_로 취소 가능",
                chat_id=chat_id,
            )
        return
    if text.startswith("/cancel"):
        conv = Conversation.load_active(chat_id) if chat_id else None
        if not conv:
            tg.send_text("취소할 대화가 없습니다.", chat_id=chat_id)
        else:
            conv.mark_cancelled()
            conv.save()
            tg.send_text("대화 취소됨. 새 아이디어 받을 준비 완료 ✓", chat_id=chat_id)
        return

    # 3) 일반 텍스트 → idea_intake 라우팅
    if chat_id:
        _handle_idea_message(chat_id, text)


def _handle_idea_message(chat_id: int, text: str):
    """일반 텍스트를 idea_intake 대화로 라우팅."""
    # 현재 active 대화가 있으면 이어쓰고, 없으면 새로 시작
    conv = Conversation.load_active(chat_id) or Conversation.new(chat_id)
    conv.append_user(text)

    # idea_intake 호출
    try:
        from agents.idea_intake import IdeaIntake
        intake = IdeaIntake()
        result = intake.propose(conv.history)
    except Exception as e:
        log.exception("idea_intake failed")
        tg.send_text(
            f"⚠️ 처리 중 오류가 발생했어요. 잠시 후 다시 시도해 주세요.\n_({type(e).__name__})_",
            chat_id=chat_id,
        )
        # 대화는 active 유지 (다음 메시지로 재시도 가능)
        conv.save()
        return

    # 응답 history 누적
    conv.append_assistant({
        "action": result.action,
        "message": result.message,
        "brief": result.brief,
    })

    # 텔레그램 발송
    if result.action == "ASK":
        sent = tg.send_text(result.message, chat_id=chat_id)
        conv.last_telegram_message_id = sent.get("message_id") if sent else None
        conv.status = "active"
    else:  # READY — Step 3: 인라인 키보드 카드 발송
        conv.mark_ready(result.brief)
        brief_text = json.dumps(result.brief, ensure_ascii=False, indent=2)
        if len(brief_text) > 1400:
            brief_text = brief_text[:1400] + "\n... (잘림)"
        preview = (
            "📝 *brief 준비됨*\n\n"
            + result.message
            + "\n\n```\n" + brief_text + "\n```"
        )
        keyboard = {
            "inline_keyboard": [[
                {"text": "✅ 시작", "callback_data": f"intake-approve:{conv.id}"},
                {"text": "✏️ 수정", "callback_data": f"intake-revise:{conv.id}"},
                {"text": "❌ 취소", "callback_data": f"intake-reject:{conv.id}"},
            ]]
        }
        sent = tg.send_text(preview, chat_id=chat_id, reply_markup=keyboard)
        conv.last_telegram_message_id = sent.get("message_id") if sent else None

    conv.save()


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
