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

from agents.base import PENDING_DIR, APPROVED_DIR, REPO_ROOT, AgentResult

# .env 자동 로드
try:
    from dotenv import load_dotenv
    load_dotenv(REPO_ROOT / ".env")
except ImportError:
    pass

from telegram_bot import client as tg
from agents import safety

LABEL = {
    "curriculum": "📚 강의 기획",
    "producer": "🎬 콘텐츠 제작",
    "marketing": "📣 홍보·마케팅",
    "success": "🎓 수강생 관리",
    "site_developer": "🛠 사이트 개발자",
    "ui_designer": "🎨 UI/UX 디자이너",
    "ceo": "🎩 CEO",
}

log = logging.getLogger("notify")

# CEO 리뷰 게이트 대상 — 메인 페이지·코스·디자인·콘텐츠에 영향을 주는 산출물
# F2 확대: lecture_script·blog_post·faq 추가 (자가 학습 루프 핵심 데이터)
CEO_GATED_KINDS = {
    "site_config_change",
    "design_variants",
    "curriculum_outline",
    "landing_copy",
    "lecture_script",      # F2 추가 — 차시 본문 (블로그·강의의 핵심)
    "blog_post",           # F2 추가 — 외부 발행 직전 마지막 검수
    "faq",                 # F2 추가 — 회원 대화 톤
}


def _format_self_review(r: AgentResult) -> str:
    """F1 self_review 결과를 CEO prompt에 주입할 한 줄 요약."""
    sr = (r.meta or {}).get("self_review") if isinstance(r.meta, dict) else None
    if not sr:
        return "(self_review 결과 없음)"
    sev = sr.get("severity", "?")
    hard = sr.get("hard_violations") or []
    soft = sr.get("soft_violations") or []
    parts = [f"severity={sev}"]
    if hard:
        parts.append(f"hard={hard}")
    if soft:
        parts.append(f"soft={soft[:5]}")
    parts.append(f"len={sr.get('len','?')}")
    return " / ".join(parts)


def _get_ceo_comment(r: AgentResult) -> str:
    """가드 대상 산출물에 대한 CEO 한 줄 의견.

    [F2 강화]
    - self_review (F1) 결과를 CEO prompt에 주입 — CEO가 룰 기반 검사 보고 종합 판단
    - severity=fail이면 CEO가 *반려 권고* 한 줄
    - severity=pass면 CEO가 *추가 관찰 포인트* 한 줄

    실패해도 워크플로우 막지 않음.
    """
    try:
        from agents.ceo import CEOAgent
        ceo = CEOAgent()
        body_preview = (r.body_md or "")[:1500]

        # F1 self_review 결과 — CEO 종합 판단 근거
        sr_summary = _format_self_review(r)

        meta_preview = ""
        try:
            import json as _json
            if r.meta:
                # self_review 빼고 나머지만 (중복 방지)
                meta_copy = {k: v for k, v in r.meta.items() if k != "self_review"}
                if meta_copy:
                    meta_preview = _json.dumps(meta_copy, ensure_ascii=False)[:600]
        except Exception:
            pass

        prompt = f"""다음 산출물에 대해 CEO로서 *한 줄 종합 의견*을 작성하라.

[산출물]
agent: {r.agent}
kind: {r.kind}
title: {r.title}
summary: {r.summary or ''}
body 앞부분: {body_preview}
meta 요약: {meta_preview}

[F1 자기 검수 결과]
{sr_summary}

[CEO 판단 규칙]
- self_review severity=fail이면 → "반려 권고" 시작으로 *어떤 부분 다시 써야 하는지* 한 줄
- self_review severity=warn이면 → "주의" 시작으로 *어느 부분 잘 보고 결정할지* 한 줄
- self_review severity=pass이면 → "통과 권고" 시작으로 *회원님이 한 번 더 확인할 포인트* 한 줄
- 정확히 한 문장 (80자 이내).
- 헌법 §4 금기·§8 톤·KPI 기여도 중 *가장 중요한 1개*만 짚는다.
- 자극·과장 톤 없이 사실 기반.
- 줄바꿈·따옴표·마크다운 금지. 일반 텍스트 한 줄."""

        comment = ceo.call(prompt, max_tokens=250).strip().replace("\n", " ")[:160]
        return comment
    except Exception as e:
        log.warning("[ceo-gate] CEO 코멘트 실패 (무시): %s", e)
        return ""


def _should_gate(r: AgentResult) -> bool:
    """F2: CEO 게이트 적용 여부 판단.

    1) kind가 CEO_GATED_KINDS면 → 항상 게이트
    2) kind 무관 — self_review severity=fail이면 *강제 게이트* (안전망)
    """
    if r.kind in CEO_GATED_KINDS:
        return True
    sr = (r.meta or {}).get("self_review") if isinstance(r.meta, dict) else None
    if sr and sr.get("severity") == "fail":
        return True
    return False


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


def _auto_approve(r: AgentResult, path: Path) -> bool:
    """AUTO 모드 — Telegram 카드 안 보내고 *즉시 적용 + approved로 이동*.

    return: True면 처리됨, False면 자동 처리 불가능 (HITL fallback 권장).
    """
    import json as _json
    SITE_CONFIG_PATH = REPO_ROOT / "site_config.json"

    # ★ CEO 산출물은 *절대* 자동 승인 안 함 (헌법 §6 회원 승인 필수)
    if r.kind.startswith("ceo_"):
        log.info("[auto] CEO 산출물 %s — HITL fallback (헌법 §6 보호)", r.id)
        return False

    # ★ 메인 페이지 변경(site_config_change)은 회원 승인 필수 (헌법 §6 + 회원 명시 결정 2026-05-15)
    if r.kind == "site_config_change":
        log.info("[auto] site_config_change %s — HITL fallback (메인 페이지 변경 잠금)", r.id)
        return False

    label = LABEL.get(r.agent, r.agent)

    # site_config 변경 — new_config 그대로 적용
    if r.kind == "site_config_change":
        new_cfg = (r.meta or {}).get("new_config")
        if isinstance(new_cfg, dict):
            SITE_CONFIG_PATH.write_text(
                _json.dumps(new_cfg, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            log.info("[auto] site_config updated from %s", r.id)

    # ★ curriculum_outline 자동 승인 시 course_order 자동 추가 (Site Dev 빈자리 메우기)
    elif r.kind == "curriculum_outline":
        course_id = r.course_id or ""
        if course_id and SITE_CONFIG_PATH.exists():
            try:
                cfg = _json.loads(SITE_CONFIG_PATH.read_text(encoding="utf-8"))
                order = cfg.get("course_order") or []
                if not isinstance(order, list):
                    order = []
                if course_id not in order:
                    order.append(course_id)
                    cfg["course_order"] = order
                    SITE_CONFIG_PATH.write_text(
                        _json.dumps(cfg, ensure_ascii=False, indent=2),
                        encoding="utf-8",
                    )
                    log.info("[auto] course_order에 %s 추가", course_id)
            except Exception as e:
                log.warning("[auto] course_order 갱신 실패: %s", e)

    # 디자인 시안 — V1 자동 채택 (가장 보수적)
    elif r.kind == "design_variants":
        variants = (r.meta or {}).get("variants") or []
        chosen = next((v for v in variants if v.get("id") == "v1"), variants[0] if variants else None)
        if chosen:
            target = (r.meta or {}).get("target", "hero")
            slot_map = {"hero": "hero_html", "home_intro": "home_intro_html", "footer": "footer_html"}
            slot = slot_map.get(target, "hero_html")
            try:
                cfg = _json.loads(SITE_CONFIG_PATH.read_text(encoding="utf-8")) if SITE_CONFIG_PATH.exists() else {}
                cfg[slot] = chosen.get("html") or ""
                existing = cfg.get("design_tokens") or {}
                if not isinstance(existing, dict):
                    existing = {}
                existing.update(chosen.get("design_tokens") or {})
                cfg["design_tokens"] = existing
                SITE_CONFIG_PATH.write_text(_json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
                r.meta["chosen_variant_id"] = chosen.get("id")
                log.info("[auto] design v1 applied to %s for %s", slot, r.id)
            except Exception as e:
                log.exception("[auto] design apply failed: %s", e)
                return False

    # 결과 status=approved + approved/로 이동
    r.status = "approved"
    new_path = APPROVED_DIR / path.name
    APPROVED_DIR.mkdir(parents=True, exist_ok=True)
    new_path.write_text(
        _json.dumps(r.__dict__, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    try:
        path.unlink()
    except Exception:
        pass

    # AUTO 처리 알림 — 짧게
    title_short = (r.title or "")[:60].replace("\n", " ")
    tg.send_text(
        f"⚡ AUTO 승인 — {label}\n[{r.kind}] {title_short}",
        parse_mode="",
    )

    # ★ Cascade — curriculum 자동 승인 후 producer/marketing/success 자동 발주
    try:
        from telegram_bot import poll as _poll
        cascaded = _poll._cascade_after_approve(r)
        if cascaded:
            tg.send_text(
                f"⚡ 자동 캐스케이드 — {len(cascaded)}개 brief 발주\n"
                + "\n".join(f"• {p.name}" for p in cascaded[:5]),
                parse_mode="",
            )
            log.info("[auto] cascaded %d briefs from %s", len(cascaded), r.id)
    except Exception as e:
        log.warning("[auto] cascade failed: %s", e)

    return True


def notify_new_pending() -> int:
    sent = 0
    pages_base = _pages_base_url()
    auto = safety.is_auto_mode()

    for path in sorted(PENDING_DIR.glob("*.json")):
        r = AgentResult.load(path)

        # ★ AUTO 모드는 telegram_message_id 무시하고 *모든 pending* 자동 처리.
        # (HITL 모드일 때만 이미 발송된 카드 skip)
        if auto:
            try:
                if _auto_approve(r, path):
                    sent += 1
                    log.info("[auto] approved %s", r.id)
                    continue
            except Exception as e:
                log.exception("[auto] approve failed for %s: %s — fallback to HITL", r.id, e)

        if r.telegram_message_id:
            continue  # HITL: 이미 발송됨

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
            elif r.kind.startswith("ceo_"):
                # ★ CEO 산출물 — '🎩 CEO 의견 / ✅ 회원 최종 결정' 카드
                # CEO 결정은 회원님이 ✅로 확정해야 사이트/운영에 적용됨 (헌법 §6 보호)
                mode_label = {
                    "ceo_first_setup": "첫 임명 작업",
                    "ceo_daily_report": "일일 보고",
                    "ceo_review": "산출물 검토",
                    "ceo_quarterly": "분기 리뷰",
                }.get(r.kind, "CEO 결정")
                ceo_summary = (r.summary or "") + f"\n\n📌 CEO 헌법 §6에 따라 회원님 최종 ✅ 확정 필요"
                res = tg.send_approval_card(
                    result_id=r.id,
                    title=f"🎩 CEO — {mode_label}",
                    summary=ceo_summary,
                    agent_label="🎩 CEO",
                    kind=r.kind,
                    body_preview=r.body_md,
                )
            else:
                # ★ CEO 리뷰 게이트 — F2 강화: gated kind + self_review fail 강제 게이트
                summary = r.summary or "(요약 없음)"

                # F1 self_review 결과 짧게 표시 (회원 판단 도움)
                sr = (r.meta or {}).get("self_review") if isinstance(r.meta, dict) else None
                if sr:
                    sev = sr.get("severity")
                    if sev == "fail":
                        hard = sr.get("hard_violations") or []
                        summary = f"{summary}\n\n🚫 자가 검수 FAIL: {hard[:3]}"
                    elif sev == "warn":
                        soft_n = len(sr.get("soft_violations") or [])
                        summary = f"{summary}\n\n⚠️ 자가 검수 warn (soft 위반 {soft_n}개)"

                if _should_gate(r):
                    ceo_line = _get_ceo_comment(r)
                    if ceo_line:
                        summary = f"{summary}\n\n🎩 CEO: {ceo_line}"
                        # CEO 코멘트를 meta에도 보관 (감사 추적)
                        if isinstance(r.meta, dict):
                            r.meta["ceo_comment"] = ceo_line
                            r.save(PENDING_DIR)
                res = tg.send_approval_card(
                    result_id=r.id,
                    title=r.title,
                    summary=summary,
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
