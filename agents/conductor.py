"""Conductor — 마스터 오케스트레이터.

briefs/*.json 안의 작업 요청을 읽어서 적절한 도메인 에이전트를 호출하고,
결과물을 content/pending/ 으로 떨어뜨린다.
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


AGENTS = {
    "curriculum": CurriculumArchitect,
    "producer": ContentProducer,
    "marketing": MarketingSpecialist,
    "success": StudentSuccessManager,
    "site_developer": SiteDeveloper,
    "ui_designer": UIDesigner,
}


def run_brief(brief_path: Path) -> list[Path]:
    """단일 brief 파일 실행 → pending에 떨어뜨린 파일 경로 리스트 반환."""
    data = json.loads(brief_path.read_text(encoding="utf-8"))
    agent_key = data.get("agent")
    if agent_key not in AGENTS:
        log.error("unknown agent: %s", agent_key)
        return []
    log.info("running brief=%s agent=%s", brief_path.name, agent_key)
    agent = AGENTS[agent_key]()
    results = agent.run(data.get("brief", {}))
    saved = []
    for r in results:
        p = r.save(PENDING_DIR)
        log.info("  → pending/%s", p.name)
        saved.append(p)
    return saved


def process_pending_briefs() -> list[Path]:
    """briefs/*.json 모두 처리하고 _processed/ 로 이동."""
    saved: list[Path] = []
    for bp in sorted(BRIEFS_DIR.glob("*.json")):
        try:
            saved.extend(run_brief(bp))
            bp.rename(PROCESSED_DIR / bp.name)
        except Exception as e:
            log.exception("brief failed: %s — %s", bp.name, e)
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
