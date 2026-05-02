"""Conductor — 마스터 오케스트레이터.

briefs/*.json 안의 작업 요청을 읽어서 적절한 도메인 에이전트를 호출하고,
결과물을 content/pending/ 으로 떨어뜨린다.

진행 상황은 텔레그램으로 실시간 알림:
  🔨 [에이전트] 작업 시작 → ✓ 산출물 N개 생성 (또는 ⚠️ 실패)
"""
from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

from .base import PENDING_DIR, REPO_ROOT
from .curriculum import CurriculumArchitect
from .producer import ContentProducer
from .marketing import MarketingSpecialist
from .success import StudentSuccessManager
from .site_developer import SiteDeveloper
from .ui_designer import UIDesigner

log = logging.getLogger("conductor")

BRIEFS_DIR = REPO_ROOT / "briefs"
BRIEFS_DIR.mkdir(exist_ok=True)
PROCESSED_DIR = BRIEFS_DIR / "_processed"
PROCESSED_DIR.mkdir(exist_ok=True)
FAILED_DIR = BRIEFS_DIR / "_failed"
FAILED_DIR.mkdir(exist_ok=True)


AGENTS = {
    "curriculum": CurriculumArchitect,
    "producer": ContentProducer,
    "marketing": MarketingSpecialist,
    "success": StudentSuccessManager,
    "site_developer": SiteDeveloper,
    "ui_designer": UIDesigner,
}

AGENT_LABEL = {
    "curriculum": "📚 강의 기획",
    "producer": "🎬 콘텐츠 제작",
    "marketing": "📣 홍보·마케팅",
    "success": "🎓 수강생 관리",
    "site_developer": "🛠 사이트 개발자",
    "ui_designer": "🎨 UI/UX 디자이너",
}


def _notify(text: str):
    """텔레그램으로 진행 상황 알림. 실패해도 워크플로우 막지 않음."""
    try:
        # 파이썬 path에 telegram_bot이 보이도록 (conductor가 -m으로 실행될 때)
        sys.path.insert(0, str(REPO_ROOT))
        from telegram_bot import client as tg
        tg.send_text(text, parse_mode="Markdown")
    except Exception as e:
        log.warning("notify failed: %s", e)


def run_brief(brief_path: Path) -> list[Path]:
    """단일 brief 파일 실행 → pending에 떨어뜨린 파일 경로 리스트 반환."""
    data = json.loads(brief_path.read_text(encoding="utf-8"))
    agent_key = data.get("agent")
    label = AGENT_LABEL.get(agent_key, agent_key or "(?)")

    if agent_key not in AGENTS:
        log.error("unknown agent: %s", agent_key)
        _notify(f"⚠️ 알 수 없는 에이전트 — `{agent_key}`\n_brief: `{brief_path.name}`_")
        return []

    log.info("running brief=%s agent=%s", brief_path.name, agent_key)
    _notify(f"🔨 *{label}* 작업 시작...\n_brief: `{brief_path.name}`_")

    agent = AGENTS[agent_key]()
    try:
        results = agent.run(data.get("brief", {}))
    except Exception as e:
        log.exception("agent run failed: %s", e)
        err_short = f"{type(e).__name__}: {str(e)[:300]}"
        _notify(f"⚠️ *{label}* 실패\n```\n{err_short}\n```")
        raise

    saved = []
    for r in results:
        p = r.save(PENDING_DIR)
        log.info("  → pending/%s", p.name)
        saved.append(p)

    if saved:
        _notify(
            f"✓ *{label}* 산출물 {len(saved)}개 생성 — 카드 발송 중..."
        )
    else:
        _notify(f"✓ *{label}* 완료 — (산출물 없음)")
    return saved


def process_pending_briefs() -> list[Path]:
    """briefs/*.json 모두 처리하고 _processed/ 또는 _failed/ 로 이동.

    실패한 brief은 _failed/로 옮겨 *재시도 루프*에서 빠져나오게 한다.
    필요 시 _failed/에서 꺼내 briefs/로 다시 옮기면 재시도 가능.
    """
    saved: list[Path] = []
    for bp in sorted(BRIEFS_DIR.glob("*.json")):
        try:
            saved.extend(run_brief(bp))
            bp.rename(PROCESSED_DIR / bp.name)
        except Exception as e:
            log.exception("brief failed: %s — %s", bp.name, e)
            # 실패한 brief은 _failed/로 격리 — 재시도 폭주 방지
            try:
                bp.rename(FAILED_DIR / bp.name)
                log.info("moved failed brief to _failed/: %s", bp.name)
            except Exception as move_err:
                log.error("failed to quarantine %s: %s", bp.name, move_err)
    return saved


if __name__ == "__main__":
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s [%(name)s] %(message)s",
    )
    files = process_pending_briefs()
    print(f"Generated {len(files)} pending result(s)")
    for f in files:
        print(f"  - {f}")
    sys.exit(0)
