"""§11 디스패치 시스템 — 10 하위 에이전트 + 작업 큐 엔진.

[기존 conductor·worker_pool 위에 얹는 디스패치 레이어]
- conductor·worker_pool: brief → AgentResult → pending (산출물 기반)
- sub_agents: 작업 티켓 → completed/{md} → CEO 판정 → approved (작업 흐름 기반)

[큐 흐름]
content/tasks/pending/  → in_progress/ → completed/ → CEO 판정
                                                        ↓
                              approved/ | review_required/ | rejected/

[작업 티켓 JSON 형식] — §11 §3 명세
{
  "task_id": "TASK-20260516-001",
  "assigned_agent": "market_research_agent",
  "objective": "...",
  "input_files": [...],
  "output_file": "content/tasks/completed/TASK-20260516-001-market-research.md",
  "scope": {...},
  "do_not": [...],
  "acceptance_criteria": [...],
  "approval_required": false,
  "deadline": "2026-05-17T18:00:00+09:00",
  "next_step": "TASK-20260516-002 expert_sourcing_agent"
}
"""
from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

from .base import BaseAgent, AgentResult, REPO_ROOT
from ._copy_principles import HUMAN_TONE_GUIDE

log = logging.getLogger("sub_agents")
KST = timezone(timedelta(hours=9))

TASKS_DIR = REPO_ROOT / "content" / "tasks"
PENDING = TASKS_DIR / "pending"
IN_PROGRESS = TASKS_DIR / "in_progress"
COMPLETED = TASKS_DIR / "completed"
REVIEW_REQUIRED = TASKS_DIR / "review_required"
APPROVED = TASKS_DIR / "approved"
REJECTED = TASKS_DIR / "rejected"

for d in (PENDING, IN_PROGRESS, COMPLETED, REVIEW_REQUIRED, APPROVED, REJECTED):
    d.mkdir(parents=True, exist_ok=True)


# ──────────────────────────────────────────────────────────────
# 10 하위 에이전트 — §11 §2 정의
# 각 에이전트는 BaseAgent를 상속해 self.call() 사용 가능
# ──────────────────────────────────────────────────────────────

CHARTER_PATH = REPO_ROOT / "data" / "ceo_charter.md"
DISPATCH_PATH = REPO_ROOT / "data" / "CEO_AGENT_DISPATCH_PROTOCOL.md"


def _load_text(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except Exception:
        return ""


CHARTER_TEXT = _load_text(CHARTER_PATH)
DISPATCH_TEXT = _load_text(DISPATCH_PATH)


class SubAgentBase(BaseAgent):
    """모든 하위 에이전트의 공용 부모. system_prompt에 헌법·§11·역할 정의 자동 inject."""

    # 서브클래스에서 override
    sub_role: str = ""                   # 한 단락 — 이 에이전트의 역할
    can_do: list[str] = []                # 할 수 있는 일
    do_not: list[str] = []                # 하면 안 되는 일
    acceptance_pattern: str = ""          # 완료 기준 패턴

    def __init_subclass__(cls, **kw):
        super().__init_subclass__(**kw)
        # system_prompt 자동 합성 — 각 서브클래스의 sub_role·can_do·do_not·헌법
        base = f"""당신은 Core Campus의 *{cls.display_name}* 에이전트다.

[역할]
{cls.sub_role}

[할 수 있는 일]
{chr(10).join(f'- {x}' for x in cls.can_do)}

[하면 안 되는 일]
{chr(10).join(f'- {x}' for x in cls.do_not)}

[완료 기준]
{cls.acceptance_pattern}

[CEO 헌법 — 모든 조항 엄격 준수]
{CHARTER_TEXT[:8000]}

[§11 디스패치 프로토콜]
{DISPATCH_TEXT[:4000]}

[작업 흐름]
1. 작업 티켓 JSON을 받는다 (Task ID·Objective·Scope·Acceptance·Do Not).
2. *Do Not*과 헌법 §4 금기를 *반드시* 위반하지 않는다.
3. Acceptance Criteria를 모두 충족하는 결과물을 마크다운으로 작성한다.
4. 출력은 마크다운 본문만. 코드펜스 금지.
"""
        cls.system_prompt = base + HUMAN_TONE_GUIDE

    def run_ticket(self, ticket: dict) -> str:
        """작업 티켓을 받아 마크다운 결과 본문 반환.

        하위 에이전트는 보통 이 메서드를 *그대로 사용*. 특화 로직 필요 시 override.
        """
        objective = ticket.get("objective", "")
        scope = ticket.get("scope", {})
        do_not = ticket.get("do_not", [])
        acceptance = ticket.get("acceptance_criteria", [])

        prompt = f"""작업 티켓 ID: {ticket.get('task_id')}

[Objective]
{objective}

[Scope]
{json.dumps(scope, ensure_ascii=False, indent=2)}

[Do Not]
{chr(10).join(f'- {x}' for x in do_not)}

[Acceptance Criteria]
{chr(10).join(f'- {x}' for x in acceptance)}

위 티켓을 마크다운으로 처리하라.
- 첫 줄: # {ticket.get('task_id')} — {ticket.get('assigned_agent')}
- 각 Acceptance Criteria를 만족하는 섹션으로 구성
- 헌법 §4·§8 자가 검수 후 출력
- 코드펜스(```) 사용 금지
"""
        body = self.call(prompt, max_tokens=4500).strip()
        if body.startswith("```"):
            body = body.split("```", 2)[1]
            if body.startswith(("markdown", "md")):
                body = body.split("\n", 1)[1]
            body = body.rsplit("```", 1)[0].strip()
        return body


# ───── 10 에이전트 ─────

class MarketResearchAgent(SubAgentBase):
    name = "market_research_agent"
    display_name = "📊 시장 조사"
    sub_role = "코스 주제·타깃·경쟁 현황을 수치 기반으로 정리한다."
    can_do = ["검색 키워드 추정", "경쟁 분석 3~5건", "타깃 페르소나 1명 구체화", "수요 점수 0~10 + 근거"]
    do_not = ["외부 페이지 무단 크롤링", "실제 사용자 데이터 수집", "가격 책정"]
    acceptance_pattern = "수요 점수·근거 3개·페르소나 1명·진입 권고/비권고 한 줄"


class ExpertSourcingAgent(SubAgentBase):
    name = "expert_sourcing_agent"
    display_name = "🔍 전문가 소싱"
    sub_role = "외주 전문가 풀을 발굴·평가한다 (헌법 §10 정책 엄격 준수)."
    can_do = ["§10.4 평가 8항목 점수화", "빨간 깃발 검출", "추천 1명 + 근거", "검색 키워드 추천"]
    do_not = ["자동 크롤링", "자동 메시지 발송", "플랫폼 외부 직거래 유도"]
    acceptance_pattern = "후보 ≥3명 평가 / 추천 1명 + 점수 + 근거"


class CurriculumAgentSub(SubAgentBase):
    name = "curriculum_agent"
    display_name = "📚 커리큘럼"
    sub_role = "코스 6강 커리큘럼 초안을 작성한다."
    can_do = ["80/20 원칙", "Bloom 분류", "각 차시 측정 가능한 학습목표"]
    do_not = ["영상 본문 작성", "가격 책정", "콘텐츠 직접 제작"]
    acceptance_pattern = "6강 모두 학습목표·실습 결과물·15분 분량"


class OutreachDraftAgent(SubAgentBase):
    name = "outreach_draft_agent"
    display_name = "✉️ 섭외 메시지"
    sub_role = "외주 전문가 섭외 메시지 v1·v2 초안을 작성한다."
    can_do = ["§10.5 6단 구조 메시지", "v1 파일럿 협업", "v2 자문+촬영 변형"]
    do_not = ["실제 메시지 발송", "가격 제안 (질문만 OK)", "계약 조건 확정", "플랫폼 외부 유도 표현"]
    acceptance_pattern = "v1·v2 각 350~450자 / 자가 검수 통과"


class RightsChecklistAgent(SubAgentBase):
    name = "rights_checklist_agent"
    display_name = "📜 권리 체크리스트"
    sub_role = "전문가 계약 표준 조항 10개 체크리스트를 작성한다."
    can_do = ["§10.6 10조항 체크리스트", "회원이 전문가에 발송할 양식"]
    do_not = ["계약 조건 확정", "실제 PDF 서명", "법무 자문"]
    acceptance_pattern = "10조항 모두 명시 / 회원 ✅ 안내 1줄"


class ProductionPlanningAgent(SubAgentBase):
    name = "production_planning_agent"
    display_name = "🎬 제작 계획"
    sub_role = "4주 제작 일정·촬영 방식·산출물 체크리스트를 작성한다."
    can_do = ["W1~W4 마일스톤", "촬영 방식 추천", "검수 5단계"]
    do_not = ["실제 촬영 일정 확정", "예산 집행", "전문가 명의 결정"]
    acceptance_pattern = "30일 25 단계 체크박스 / 회원 ✅ 게이트 시점 명시"


class LandingCopyAgent(SubAgentBase):
    name = "landing_copy_agent"
    display_name = "🪧 랜딩 카피"
    sub_role = "사이트 랜딩 페이지 카피 초안을 작성한다."
    can_do = ["헤드라인·문제·해결·결과·FAQ 5~7개·CTA"]
    do_not = ["가격 책정", "사이트 실제 수정", "메인 페이지 시그니처 카피 변경"]
    acceptance_pattern = "모든 섹션 §8 톤 / 구체 숫자·사례"


class SiteDeveloperAgentSub(SubAgentBase):
    name = "site_developer_agent"
    display_name = "🛠 사이트 변경 제안"
    sub_role = "사이트 코드·구조 변경 *제안*만 한다 (회원 ✅ 후만 적용)."
    can_do = ["course_overrides·course_order 변경 제안"]
    do_not = ["LOCKED_KEYS 변경 (hero·footer·시그니처)", "직접 commit·push"]
    acceptance_pattern = "변경 diff·근거·예상 영향"


class KpiReportAgent(SubAgentBase):
    name = "kpi_report_agent"
    display_name = "📈 KPI 리포트"
    sub_role = "일일·주간 KPI 리포트를 작성한다."
    can_do = ["§7 단계별 목표 대비 진척률", "비용 분석", "전환 분석"]
    do_not = ["KPI 임의 조작", "외부 데이터 무단 가져오기"]
    acceptance_pattern = "초기·중간·수익 KPI / 한 줄 운영 평가"


class CeoReviewAgent(SubAgentBase):
    name = "ceo_review_agent"
    display_name = "🎩 CEO 최종 판정"
    sub_role = "다른 9 에이전트 산출물에 대한 CEO 최종 판정 (메타 에이전트)."
    can_do = ["APPROVED / REVISION_REQUIRED / REJECTED 라벨", "구체적 수정 사항"]
    do_not = ["산출물 직접 수정", "다른 에이전트 작업 대신 수행"]
    acceptance_pattern = "라벨 + 사유 한 단락 + 회원 ✅ 필요 여부"


SUB_AGENTS: dict[str, type[SubAgentBase]] = {
    "market_research_agent": MarketResearchAgent,
    "expert_sourcing_agent": ExpertSourcingAgent,
    "curriculum_agent": CurriculumAgentSub,
    "outreach_draft_agent": OutreachDraftAgent,
    "rights_checklist_agent": RightsChecklistAgent,
    "production_planning_agent": ProductionPlanningAgent,
    "landing_copy_agent": LandingCopyAgent,
    "site_developer_agent": SiteDeveloperAgentSub,
    "kpi_report_agent": KpiReportAgent,
    "ceo_review_agent": CeoReviewAgent,
}


# ──────────────────────────────────────────────────────────────
# 작업 큐 엔진 — dispatch / pickup / complete / label
# ──────────────────────────────────────────────────────────────

def dispatch_ticket(ticket: dict) -> Path:
    """CEO가 호출. pending/에 작업 티켓 JSON 저장."""
    task_id = ticket.get("task_id") or f"TASK-{int(time.time())}"
    ticket["task_id"] = task_id
    ticket.setdefault("created_at", datetime.now(KST).isoformat())
    ticket.setdefault("status", "pending")
    p = PENDING / f"{task_id}.json"
    p.write_text(json.dumps(ticket, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("[dispatch] %s → %s", task_id, ticket.get("assigned_agent"))
    return p


def pickup_pending_ticket() -> Path | None:
    """가장 오래된 pending 티켓 1개 → in_progress로 이동."""
    candidates = sorted(PENDING.glob("TASK-*.json"))
    if not candidates:
        return None
    src = candidates[0]
    dst = IN_PROGRESS / src.name
    src.rename(dst)
    log.info("[pickup] %s → in_progress", dst.name)
    return dst


def complete_ticket(ticket_path: Path, output_text: str) -> tuple[Path, Path]:
    """in_progress 티켓 처리 후 → completed/. (티켓 JSON + 결과 .md 둘 다 이동)"""
    ticket = json.loads(ticket_path.read_text(encoding="utf-8"))
    task_id = ticket["task_id"]
    agent_short = ticket["assigned_agent"].replace("_agent", "")
    md_name = f"{task_id}-{agent_short}.md"

    out_md = COMPLETED / md_name
    out_md.write_text(output_text, encoding="utf-8")

    ticket["status"] = "completed"
    ticket["completed_at"] = datetime.now(KST).isoformat()
    ticket["output_path"] = str(out_md.relative_to(REPO_ROOT))
    out_json = COMPLETED / ticket_path.name
    out_json.write_text(json.dumps(ticket, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        ticket_path.unlink()
    except Exception:
        pass
    log.info("[complete] %s → completed/", task_id)
    return out_json, out_md


def label_ticket(task_id: str, label: str, reason: str = "", revision: str = "") -> Path | None:
    """CEO가 호출. completed/ 의 티켓을 approved/review_required/rejected 중 하나로 이동."""
    assert label in ("approved", "review_required", "rejected"), f"잘못된 라벨: {label}"
    src = COMPLETED / f"{task_id}.json"
    if not src.exists():
        log.warning("[label] %s 없음 in completed/", task_id)
        return None
    ticket = json.loads(src.read_text(encoding="utf-8"))
    ticket["label"] = label
    ticket["label_reason"] = reason
    if revision:
        ticket["revision_instructions"] = revision
    ticket["labeled_at"] = datetime.now(KST).isoformat()

    dst_dir = {"approved": APPROVED, "review_required": REVIEW_REQUIRED, "rejected": REJECTED}[label]
    dst = dst_dir / f"{task_id}.json"
    dst.write_text(json.dumps(ticket, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        src.unlink()
    except Exception:
        pass
    log.info("[label] %s → %s", task_id, label)
    return dst


def process_one_pending() -> dict | None:
    """1개 pending 티켓 처리 — 픽업 → 에이전트 실행 → completed.

    Returns:
        결과 dict (task_id, agent, output_path) 또는 None (큐 비어있음)
    """
    ticket_path = pickup_pending_ticket()
    if ticket_path is None:
        return None
    try:
        ticket = json.loads(ticket_path.read_text(encoding="utf-8"))
        agent_key = ticket.get("assigned_agent")
        if agent_key not in SUB_AGENTS:
            log.error("[process] unknown agent: %s", agent_key)
            # rejected로 이동
            ticket["label"] = "rejected"
            ticket["label_reason"] = f"unknown agent: {agent_key}"
            (REJECTED / ticket_path.name).write_text(
                json.dumps(ticket, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            ticket_path.unlink()
            return {"task_id": ticket["task_id"], "agent": agent_key, "ok": False}

        agent = SUB_AGENTS[agent_key]()
        body = agent.run_ticket(ticket)
        out_json, out_md = complete_ticket(ticket_path, body)
        return {
            "task_id": ticket["task_id"],
            "agent": agent_key,
            "ok": True,
            "output_path": str(out_md.relative_to(REPO_ROOT)),
            "body_len": len(body),
        }
    except Exception as e:
        log.exception("[process] 처리 실패: %s", e)
        return {"ok": False, "error": str(e)}


def get_queue_status() -> dict:
    """대시보드용 — 각 큐 상태."""
    return {
        "pending": len(list(PENDING.glob("TASK-*.json"))),
        "in_progress": len(list(IN_PROGRESS.glob("TASK-*.json"))),
        "completed": len(list(COMPLETED.glob("TASK-*.json"))),
        "review_required": len(list(REVIEW_REQUIRED.glob("TASK-*.json"))),
        "approved": len(list(APPROVED.glob("TASK-*.json"))),
        "rejected": len(list(REJECTED.glob("TASK-*.json"))),
    }
