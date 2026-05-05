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

# .env 로드 — 데몬이 환경변수 못 읽고 즉시 크래시하는 문제 해결
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
except ImportError:
    pass

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


# ─────────────────────────────────────────────────────────────────────────
# Phase A2 — 자동 캐스케이드
# ─────────────────────────────────────────────────────────────────────────

def _cascade_after_approve(r: AgentResult) -> list[Path]:
    """승인된 결과물 기반으로 *다음 단계 brief*을 자동 생성.

    매핑:
      curriculum_outline → producer(1차시) + marketing + success(faq)
      lecture_script     → producer(다음 차시) [같은 코스에 다음 차시 있을 때만]
      landing_copy       → blog_publisher (티스토리 임시저장 자동 게시)
      그 외             → 캐스케이드 없음
    """
    try:
        if r.kind == "curriculum_outline":
            return _cascade_from_curriculum(r)
        if r.kind == "lecture_script":
            return _cascade_from_lecture_script(r)
        if r.kind == "landing_copy":
            return _cascade_from_landing_copy(r)
    except Exception as e:
        log.exception("[cascade] failed for %s: %s", r.id, e)
    return []


def _cascade_from_landing_copy(r: AgentResult) -> list[Path]:
    """marketing landing_copy 승인 → blog_publisher 자동 발주 (티스토리 임시저장)."""
    course_id = r.course_id or ""
    if not course_id:
        return []

    landing_raw = (r.meta or {}).get("raw") or {}

    # 같은 course_id의 curriculum 결과 찾기
    curriculum_raw = {}
    course_title = r.title
    for ap in APPROVED_DIR.glob("*.json"):
        try:
            cr = AgentResult.load(ap)
        except Exception:
            continue
        if cr.kind == "curriculum_outline" and cr.course_id == course_id:
            curriculum_raw = (cr.meta or {}).get("raw") or {}
            course_title = curriculum_raw.get("title") or cr.title
            break

    brief = {
        "agent": "blog_publisher",
        "brief": {
            "course_id": course_id,
            "course_title": course_title,
            "landing_copy": landing_raw,
            "curriculum": curriculum_raw,
        },
    }
    return _save_cascade_briefs(
        [brief],
        prefix=f"cascade-blog-{course_id}",
    )


def _cascade_from_curriculum(r: AgentResult) -> list[Path]:
    """curriculum 승인 → producer 1차시 + marketing + success FAQ 자동 발주."""
    raw = (r.meta or {}).get("raw") or {}
    lessons = raw.get("lessons") or []
    course_id = r.course_id or "unknown"
    course_title = raw.get("title") or r.title

    briefs: list[dict] = []

    # 1. Producer brief — 1차시부터 시작
    if lessons:
        l1 = lessons[0]
        briefs.append({
            "agent": "producer",
            "brief": {
                "course_id": course_id,
                "course_title": course_title,
                "lesson_no": l1.get("no", 1),
                "lesson_title": l1.get("title", ""),
                "objective": l1.get("objective", ""),
                "key_concepts": l1.get("key_concepts", []),
                "exercise": l1.get("exercise", ""),
                "duration_min": l1.get("duration_min", 15),
            },
        })

    # 2. Marketing brief — 랜딩 카피
    briefs.append({
        "agent": "marketing",
        "brief": {
            "course_id": course_id,
            "curriculum": raw,
            "price_hint": "30~70만원대",
        },
    })

    # 3. Success brief — FAQ 7개
    briefs.append({
        "agent": "success",
        "brief": {
            "mode": "faq",
            "course_id": course_id,
            "course_title": course_title,
            "topic": raw.get("tagline", ""),
            "audience": raw.get("target_audience", ""),
        },
    })

    # 4. UI Designer — 코스 hero 시안 3변형 (디자이너에게도 일 분배)
    briefs.append({
        "agent": "ui_designer",
        "brief": {
            "target": "hero",
            "purpose": f"{course_title} 코스의 핵심 메시지를 8초에 전달하는 랜딩 hero",
            "audience": raw.get("target_audience", ""),
            "style_keywords": ["editorial", "warm beige", "trustworthy", "academic"],
            "color_mood": "warm",
            "additional_context": f"코어 캠퍼스 코스 '{course_title}'의 페이지 헤더 시안.",
        },
    })

    # 5. Site Developer — 코스 메타데이터 다듬기
    briefs.append({
        "agent": "site_developer",
        "brief": {
            "instruction": (
                f"새 코스 '{course_title}' (course_id: {course_id})가 추가됐습니다. "
                f"site_config.json의 course_overrides에 이 코스의 *title_override*와 "
                f"*tagline_override*를 다듬어 주세요. 다른 필드는 절대 만지지 않습니다. "
                f"코스 톤 힌트: {raw.get('tagline', '')}"
            ),
            "brand_tone": "차분하고 단단한 한국어, 과장 표현 금지",
            "target_audience": raw.get("target_audience", ""),
            "restrictions": "course_overrides 외 다른 필드 변경 금지, WCAG AA 유지",
        },
    })

    return _save_cascade_briefs(briefs, prefix=f"cascade-curriculum-{course_id}")


def _cascade_from_lecture_script(r: AgentResult) -> list[Path]:
    """lecture_script 승인 → 같은 코스의 *다음 차시* producer brief.

    같은 course_id의 curriculum_outline을 approved/에서 찾아 lessons[]에서
    현재 lesson_no + 1을 다음 차시로 발주.
    """
    course_id = r.course_id
    if not course_id:
        return []

    cur_lesson_no = ((r.meta or {}).get("brief") or {}).get("lesson_no")
    if not cur_lesson_no:
        return []

    # 같은 course_id의 curriculum 결과를 approved에서 찾음
    curriculum_result = None
    for ap in APPROVED_DIR.glob("*.json"):
        try:
            cr = AgentResult.load(ap)
        except Exception:
            continue
        if cr.kind == "curriculum_outline" and cr.course_id == course_id:
            curriculum_result = cr
            break

    if not curriculum_result:
        log.warning("[cascade] no curriculum for course=%s, can't continue lessons", course_id)
        return []

    raw = (curriculum_result.meta or {}).get("raw") or {}
    lessons = raw.get("lessons") or []
    next_lesson = next((l for l in lessons if l.get("no") == cur_lesson_no + 1), None)

    if not next_lesson:
        log.info("[cascade] curriculum complete for course=%s (last lesson %d)", course_id, cur_lesson_no)
        return []

    course_title = raw.get("title") or curriculum_result.title
    brief = {
        "agent": "producer",
        "brief": {
            "course_id": course_id,
            "course_title": course_title,
            "lesson_no": next_lesson.get("no"),
            "lesson_title": next_lesson.get("title", ""),
            "objective": next_lesson.get("objective", ""),
            "key_concepts": next_lesson.get("key_concepts", []),
            "exercise": next_lesson.get("exercise", ""),
            "duration_min": next_lesson.get("duration_min", 15),
        },
    }

    return _save_cascade_briefs(
        [brief],
        prefix=f"cascade-lesson-{course_id}-{next_lesson.get('no')}",
    )


def _save_cascade_briefs(briefs: list[dict], prefix: str) -> list[Path]:
    """캐스케이드 brief 저장 — *중복 차단* 포함.

    같은 (agent, course_id, lesson_no) 시그니처가 이미 큐(briefs/) 또는
    최근 _processed/에 있으면 새로 만들지 않음. 중복 cascade 폭주 방지.
    """
    import time as _time
    out: list[Path] = []

    # ★ 기존 큐 + 최근 _processed의 시그니처 수집
    briefs_dir = REPO_ROOT / "briefs"
    proc_dir = briefs_dir / "_processed"

    def _sig(b: dict) -> tuple:
        agent = b.get("agent", "")
        bd = b.get("brief", {}) or {}
        # course_id + lesson_no가 있으면 그걸로, 없으면 agent + course_id만
        return (agent, bd.get("course_id", ""), bd.get("lesson_no", "") or "")

    existing_sigs: set = set()
    # 큐에 있는 모든 brief
    for p in briefs_dir.glob("*.json"):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            existing_sigs.add(_sig(d))
        except Exception:
            pass
    # 최근 _processed (mtime 기준 최근 1시간 — 너무 오래된 건 재처리 OK)
    cutoff = _time.time() - 3600
    if proc_dir.exists():
        for p in proc_dir.glob("*.json"):
            try:
                if p.stat().st_mtime < cutoff:
                    continue
                d = json.loads(p.read_text(encoding="utf-8"))
                existing_sigs.add(_sig(d))
            except Exception:
                pass

    ts = int(_time.time())
    for i, b in enumerate(briefs):
        sig = _sig(b)
        if sig in existing_sigs:
            log.info("[cascade] dedup skip: %s (이미 큐 또는 최근 처리됨)", sig)
            continue

        agent_key = b.get("agent", "unknown")
        path = briefs_dir / f"{prefix}-{agent_key}-{ts}-{i}.json"
        try:
            path.write_text(
                json.dumps(b, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            out.append(path)
            existing_sigs.add(sig)  # 같은 호출 내 중복도 차단
            log.info("[cascade] saved: %s", path.name)
        except Exception as e:
            log.error("[cascade] failed to save %s: %s", path.name, e)
    return out


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

        # ★ Phase A2 — 자동 캐스케이드 (다음 단계 brief 자동 생성)
        cascaded_briefs = _cascade_after_approve(r)
        cascade_msg = ""
        if cascaded_briefs:
            cascade_lines = [
                f"\n\n⚡ *자동 다음 단계* — {len(cascaded_briefs)}개 brief 자동 발주:"
            ]
            for cp in cascaded_briefs:
                cascade_lines.append(f"• `{cp.name}`")
            cascade_msg = "\n".join(cascade_lines)
            # 즉시 새 사이클 트리거 — 다음 작업이 1-2분 안에 시작됨
            _dispatch_agent_loop()

        tg.answer_callback(cq["id"], "✅ 승인 완료 — 사이트에 반영됩니다")
        tg.edit_message_text(
            chat_id, message_id,
            f"✅ *승인됨* — `{r.kind}`\n*{r.title}*\n\n다음 빌드에서 사이트에 반영돼요." + cascade_msg,
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
            "코어 캠퍼스 컨트롤 패널\n\n"
            "✏️ 아이디어 대화 — 그냥 한 줄로 보내세요\n"
            "✅/❌ — 카드 도착 시 승인·거절\n\n"
            "─ 명령어 ─\n"
            "/status — 시스템 상태 한눈에\n"
            "/cards  — 대기 카드 다시 띄움\n"
            "/site   — 라이브 사이트 URL\n"
            "/pending — 대기 항목 개수\n"
            "/conv   — 대화 상태\n"
            "/cancel — 대화 취소\n"
            "─ AUTO 모드 ─\n"
            "/auto on  — 모든 산출물 자동 승인 + 캐스케이드\n"
            "/auto off — 자동 모드 끄기 (HITL 복귀)\n"
            "/stop   — 즉시 정지 (auto OFF + 일시정지)\n"
            "/resume — 정지 해제",
            chat_id=chat_id, parse_mode="",
        )
        return
    if text.startswith("/status"):
        _send_status_overview(chat_id)
        return
    if text.startswith("/cards"):
        _resend_pending_cards(chat_id)
        return
    if text.startswith("/site"):
        url = _pages_url()
        tg.send_text(f"🌐 라이브 사이트\n{url}" if url else "사이트 URL 미설정", chat_id=chat_id, parse_mode="")
        return
    if text.startswith("/auto"):
        from agents import safety
        parts = text.split()
        if len(parts) >= 2 and parts[1].lower() in ("off", "stop", "0"):
            safety.set_auto_mode(False, "user /auto off")
            tg.send_text("⏸ AUTO 모드 OFF — 모든 산출물 다시 ✅ 승인 필요", chat_id=chat_id, parse_mode="")
        else:
            safety.set_auto_mode(True, "user /auto on")
            tg.send_text(
                "⚡ AUTO 모드 ON\n\n"
                "지금부터 모든 산출물 자동 승인·적용·캐스케이드.\n"
                "디자인 시안은 V1 자동 채택.\n"
                "일일 한도 50 brief / $5 도달 시 자동 정지.\n\n"
                "정지: /stop — 즉시 멈춤\n"
                "재개: /resume",
                chat_id=chat_id, parse_mode="",
            )
        return
    if text.startswith("/stop"):
        from agents import safety
        safety.force_pause("user /stop")
        tg.send_text("🛑 정지 — AUTO 모드 OFF + brief 처리 일시정지\n/resume으로 재개", chat_id=chat_id, parse_mode="")
        return
    if text.startswith("/resume"):
        from agents import safety
        safety.force_resume("user /resume")
        tg.send_text("▶ 재개 — brief 처리 정상화\n(AUTO 모드는 별도로 켜야 함: /auto)", chat_id=chat_id, parse_mode="")
        return
    if text.startswith("/pending"):
        items = list(PENDING_DIR.glob("*.json"))
        tg.send_text(f"대기 중: {len(items)}건", chat_id=chat_id, parse_mode="")
        return
    if text.startswith("/conv"):
        conv = Conversation.load_active(chat_id) if chat_id else None
        if not conv:
            tg.send_text("진행 중인 대화가 없습니다. 새 아이디어를 한 줄로 보내주세요.", chat_id=chat_id, parse_mode="")
        else:
            turns = sum(1 for h in conv.history if h.get("role") == "user")
            tg.send_text(
                f"진행 중인 대화 — {turns}턴\n상태: {conv.status}\n/cancel로 취소 가능",
                chat_id=chat_id, parse_mode="",
            )
        return
    if text.startswith("/cancel"):
        conv = Conversation.load_active(chat_id) if chat_id else None
        if not conv:
            tg.send_text("취소할 대화가 없습니다.", chat_id=chat_id, parse_mode="")
        else:
            conv.mark_cancelled()
            conv.save()
            tg.send_text("대화 취소됨. 새 아이디어 받을 준비 완료 ✓", chat_id=chat_id, parse_mode="")
        return

    # 3) 일반 텍스트 → idea_intake 라우팅
    if chat_id:
        _handle_idea_message(chat_id, text)


def _pages_url() -> str:
    repo = os.environ.get("GITHUB_REPOSITORY") or "idsexyhomme-code/lecture-auto"
    if "/" not in repo:
        return ""
    owner, name = repo.split("/", 1)
    return f"https://{owner.lower()}.github.io/{name}/"


def _send_status_overview(chat_id: int):
    """/status — 시스템 현재 상태 한눈에 (plain text)."""
    pending = list(PENDING_DIR.glob("*.json"))
    approved = list(APPROVED_DIR.glob("*.json"))
    rejected = list(REJECTED_DIR.glob("*.json"))
    briefs_dir = REPO_ROOT / "briefs"
    queued = list(briefs_dir.glob("*.json")) if briefs_dir.exists() else []
    failed_dir = briefs_dir / "_failed" if briefs_dir.exists() else None
    failed_briefs = list(failed_dir.glob("*.json")) if failed_dir and failed_dir.exists() else []

    lines = ["📊 코어 캠퍼스 현재 상태", ""]
    lines.append(f"📨 대기 중 카드: {len(pending)}건")
    lines.append(f"✓ 완료된 산출물: {len(approved)}건")
    if rejected:
        lines.append(f"❌ 거절: {len(rejected)}건")
    lines.append("")
    lines.append(f"📋 대기 brief: {len(queued)}건")
    if failed_briefs:
        lines.append(f"⚠️ 실패 brief: {len(failed_briefs)}건 (격리됨)")
    lines.append("")
    try:
        from agents import safety
        s = safety.status().replace("*", "").replace("_", "")
        lines.append(s)
    except Exception:
        pass
    lines.append("")
    url = _pages_url()
    if url:
        lines.append(f"🌐 사이트: {url}")
    if pending:
        lines.append("")
        lines.append("최근 대기 카드:")
        recent = sorted(pending, key=lambda p: p.stat().st_mtime, reverse=True)[:3]
        for p in recent:
            try:
                r = AgentResult.load(p)
                title = (r.title or "")[:50].replace("\n", " ")
                lines.append(f"  • [{r.kind}] {title}")
            except Exception:
                continue
    tg.send_text("\n".join(lines), chat_id=chat_id, parse_mode="")


def _resend_pending_cards(chat_id: int):
    """/cards — 대기 카드 다시 발송."""
    pending = sorted(PENDING_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime)
    if not pending:
        tg.send_text("대기 카드 없음 ✓", chat_id=chat_id, parse_mode="")
        return
    pages_base = _pages_url().rstrip("/") if _pages_url() else None
    tg.send_text(f"📋 대기 카드 {len(pending)}개 ↓", chat_id=chat_id, parse_mode="")

    LABEL = {
        "curriculum": "📚 강의 기획",
        "producer": "🎬 콘텐츠 제작",
        "marketing": "📣 홍보·마케팅",
        "success": "🎓 수강생 관리",
        "site_developer": "🛠 사이트 개발자",
        "ui_designer": "🎨 UI/UX 디자이너",
    }
    n = 0
    for path in pending:
        try:
            r = AgentResult.load(path)
        except Exception:
            continue
        try:
            if r.kind == "design_variants":
                target = (r.meta or {}).get("target", "hero")
                variants = (r.meta or {}).get("variants") or []
                if variants:
                    tg.send_design_variants_card(
                        result_id=r.id, title=r.title,
                        summary=r.summary or "", target=target,
                        variants=variants, preview_base_url=pages_base,
                        chat_id=chat_id,
                    )
                    n += 1
            else:
                tg.send_approval_card(
                    result_id=r.id, title=r.title,
                    summary=r.summary or "(요약 없음)",
                    agent_label=LABEL.get(r.agent, r.agent),
                    kind=r.kind, body_preview=r.body_md,
                    chat_id=chat_id,
                )
                n += 1
        except Exception as e:
            log.exception("resend %s: %s", r.id, e)
    tg.send_text(f"✓ {n}개 재발송 완료", chat_id=chat_id, parse_mode="")


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
    import time

    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s [%(name)s] %(message)s",
    )

    # ★ 데몬 모드 — 환경변수 ONESHOT=1이면 1회만, 기본은 무한 루프
    #   30초마다: 텔레그램 polling
    #   150초마다 (5번째 사이클): brief 처리 (conductor.process_pending_briefs)
    oneshot = os.environ.get("ONESHOT", "0").lower() in ("1", "true", "yes")

    if oneshot:
        n = run()
        print(f"Processed {n} update(s)")
    else:
        # 데몬 모드 — brief 처리 + 텔레그램 polling 통합
        from agents.conductor import process_pending_briefs

        log.info("[poll] 데몬 모드 시작 — polling 30s + brief 처리 150s")
        cycle = 0
        while True:
            try:
                # ① 텔레그램 polling
                n = run()
                if n > 0:
                    log.info("Processed %d telegram update(s)", n)

                # ② 5 사이클(=150초)마다 brief 처리
                cycle += 1
                if cycle >= 5:
                    cycle = 0
                    try:
                        log.info("[poll] brief 처리 사이클 시작")
                        files = process_pending_briefs()
                        if files:
                            log.info("[poll] ✓ %d개 brief 처리 완료", len(files))
                        else:
                            log.debug("[poll] (대기 brief 없음)")
                    except Exception as e:
                        log.exception("[poll] brief 처리 실패: %s", e)

            except KeyboardInterrupt:
                log.info("[poll] 종료 신호 받음")
                break
            except Exception as e:
                log.exception("[poll] cycle 실패: %s", e)
            time.sleep(30)
