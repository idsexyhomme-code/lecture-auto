"""brief 스케줄러 — 의존성 안전한 실행 그룹 계산.

[휴리스틱 의존성 규칙]
1. 같은 course_id의 brief들은 *같은 worker에서 직렬* — 데이터 race 방지
   예: marketing-claude-X와 producer-claude-X-lesson-3 동시 처리하면 같은 파일 충돌
2. ceo·site_developer는 *글로벌 직렬* (project-level 영향) — 모두 한 워커
3. 그 외 다른 course_id의 brief들은 *서로 병렬*

[그룹화 결과]
output = [
    [brief_a_course_X, brief_b_course_X, ...],   # 그룹 1 (course X — 직렬)
    [brief_c_course_Y, ...],                       # 그룹 2 (course Y — 직렬)
    [brief_d_ceo, brief_e_site_developer, ...],    # 그룹 3 (글로벌 — 직렬)
    [brief_f_blog_publisher_a, ...],               # 그룹 4 (blog_publisher — 독립이라 단독)
]
각 그룹은 worker 1개에 dispatch. 그룹 간은 병렬.

[명시적 dependency (선택)]
brief 안에 `brief["depends_on"]: ["brief-id-1"]` 명시 가능.
지금은 *휴리스틱만* 사용. 명시 의존성은 v2에서.

회원 결정 P4: 이 단순한 휴리스틱이 *복잡성 대비 이득* 충분히 보장.
"""
from __future__ import annotations

import json
import logging
from collections import defaultdict
from pathlib import Path

log = logging.getLogger("scheduler")

# *글로벌 직렬* 영역 — 한 워커에서 처리 (project-level 부작용 있음)
GLOBAL_SERIAL_AGENTS = {"ceo", "site_developer"}


def _read_brief_meta(path: Path) -> dict:
    """brief 파일에서 agent / course_id 추출."""
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"agent": None, "course_id": None}
    agent = d.get("agent")
    brief = d.get("brief") or {}
    course_id = brief.get("course_id") or d.get("course_id") or ""
    return {"agent": agent, "course_id": course_id}


def schedule_briefs(brief_paths: list[Path]) -> list[list[Path]]:
    """brief 리스트를 *안전한 실행 그룹*들로 분류.

    Returns:
        list of groups. 각 그룹은 *한 워커에서 직렬* 실행. 그룹 간은 병렬.

    Algorithm:
        1. agent ∈ GLOBAL_SERIAL_AGENTS → "__global__" 그룹
        2. course_id 있으면 → "course:{course_id}" 그룹
        3. 그 외 (blog_publisher 등) → 각 brief을 *단독 그룹* (병렬 OK)
    """
    if not brief_paths:
        return []

    groups: dict[str, list[Path]] = defaultdict(list)

    for path in brief_paths:
        meta = _read_brief_meta(path)
        agent = meta["agent"]
        course_id = meta["course_id"]

        if agent in GLOBAL_SERIAL_AGENTS:
            key = "__global__"
        elif course_id:
            key = f"course:{course_id}"
        else:
            # 독립 brief — 자기만의 그룹
            key = f"solo:{path.name}"

        groups[key].append(path)

    # 그룹 정렬 — __global__ 먼저 (사이트 상태 영향)
    sorted_keys = sorted(
        groups.keys(),
        key=lambda k: (0 if k == "__global__" else 1, k),
    )

    result = [groups[k] for k in sorted_keys]
    log.info(
        "[scheduler] %d brief → %d 그룹 (global=%d, course=%d, solo=%d)",
        len(brief_paths),
        len(result),
        sum(1 for k in sorted_keys if k == "__global__"),
        sum(1 for k in sorted_keys if k.startswith("course:")),
        sum(1 for k in sorted_keys if k.startswith("solo:")),
    )
    return result


def explain_schedule(brief_paths: list[Path]) -> str:
    """디버그용 — 분류 결과를 사람이 읽을 수 있는 형식으로."""
    groups = schedule_briefs(brief_paths)
    lines = []
    for i, grp in enumerate(groups, 1):
        lines.append(f"그룹 {i} ({len(grp)}개 — 직렬):")
        for p in grp:
            meta = _read_brief_meta(p)
            lines.append(f"  - {p.name}  agent={meta['agent']}  course={meta['course_id'] or '-'}")
    lines.append(f"\n총 {len(groups)}개 그룹 — 그룹 간 병렬 처리 가능")
    return "\n".join(lines)
