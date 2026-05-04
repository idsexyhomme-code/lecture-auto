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


def _auto_approve(r: AgentResult, path: Path) -> bool:
    """AUTO 모드 — Telegram 카드 안 보내고 *즉시 적용 + approved로 이동*.

    return: True면 처리됨, False면 자동 처리 불가능 (HITL fallback 권장).
    """
    import json as _json
    SITE_CONFIG_PATH = REPO_ROOT / "site_config.json"

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
