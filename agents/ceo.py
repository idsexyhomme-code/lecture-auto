"""CEO Agent — Core Campus의 총책임자.

회원님(서형) 임명. 헌법: data/ceo_charter.md.

3가지 모드:
  - first_setup     : 첫 셋업 — 30일 로드맵·카테고리 5개·무료 콘텐츠 20개·
                      유료 상품 3개·수익 구조·운영 루틴·승인 목록을 한 번에 작성
  - daily_report    : 매일 보고 7항목 (오늘 목표 / 실행 작업 / 예상 효과 /
                      승인 필요 / 자율 가능 / 생성할 산출물 / 리스크)
  - review_pending  : pending/ 의 산출물 검토 → 승인·반려·수정 요청
  - quarterly_review: 90일/6개월/12개월 KPI 대비 진척도 + 다음 분기 우선순위

브리프 예시:
  {"agent": "ceo", "brief": {"mode": "first_setup"}}
  {"agent": "ceo", "brief": {"mode": "daily_report", "today_kst": "2026-05-08"}}
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from .base import BaseAgent, AgentResult, REPO_ROOT
from ._copy_principles import HUMAN_TONE_GUIDE

CHARTER_PATH = REPO_ROOT / "data" / "ceo_charter.md"
CHARTER = CHARTER_PATH.read_text(encoding="utf-8") if CHARTER_PATH.exists() else ""

SYSTEM = f"""당신은 Core Campus의 CEO 에이전트다. 회원님(서형)이 임명했다.

[CEO 헌법 — 절대 무시 금지]

{CHARTER}

[행동 원칙]

- 위 헌법의 모든 조항을 엄격히 따른다.
- 금기 사항(§4)을 위반하는 결정은 *어떤 이유에서도* 하지 않는다.
- 자율 결정 가능 범위(§5) 안에서는 단호하고 빠르게 결정한다.
- 승인 필수 범위(§6)는 *반드시 회원님 확인이 필요한 사항*으로 명시한다.
- 보고는 §9 형식에 따라 7항목 구조를 유지한다.
- §8 톤을 그대로 쓴다 — 숫자로 말하고, 자극적 부업팔이 톤은 사용하지 않는다.
- 모든 산출물은 §9의 형식 또는 회원님이 직접 지시한 형식을 따른다.

[CEO 의사결정 자가 검수 — 결과 출력 전 항상 한 번 더 확인]

1. 이 결정이 헌법 §4 금기 사항에 해당하는가? → 해당하면 *즉시* 결정 철회.
2. 이 작업이 §6 승인 필수 범위인가? → 해당하면 결과물에 "★ 회원 승인 필수" 명시.
3. 숫자·구체 KPI·시한이 들어가 있는가? → 없으면 추가.
4. 자극적 동기부여·과장 표현이 있는가? → 있으면 삭제.
""" + HUMAN_TONE_GUIDE


class CEOAgent(BaseAgent):
    name = "ceo"
    display_name = "CEO"
    system_prompt = SYSTEM

    def run(self, brief: dict) -> list[AgentResult]:
        mode = brief.get("mode", "daily_report")
        if mode == "first_setup":
            return self._first_setup(brief)
        if mode == "daily_report":
            return self._daily_report(brief)
        if mode == "review_pending":
            return self._review_pending(brief)
        if mode == "quarterly_review":
            return self._quarterly_review(brief)
        if mode == "w1_plan":
            return self._w1_plan(brief)
        if mode == "w1_step":
            return self._w1_step(brief)
        if mode == "dispatch_workflow":
            return self._dispatch_workflow(brief)
        return self._daily_report(brief)

    # ── §11 디스패치 — 작업 티켓 일괄 발행 ─────────────────────────
    def _dispatch_workflow(self, brief: dict) -> list[AgentResult]:
        """CEO가 워크플로 ID를 받아 *작업 티켓 5~10개*를 content/tasks/pending/ 에 일괄 발행.

        brief = {
            "mode": "dispatch_workflow",
            "workflow": "pilot_01" | "custom",
            "date_kst": "2026-05-16",  # 옵션. 티켓 ID 접두사.
            "tickets": [...],          # custom일 때만. 명시 티켓 배열.
        }
        """
        import logging
        log = logging.getLogger("ceo._dispatch_workflow")

        from datetime import datetime, timezone, timedelta
        KST = timezone(timedelta(hours=9))

        workflow = brief.get("workflow", "pilot_01")
        date_kst = brief.get("date_kst") or datetime.now(KST).strftime("%Y-%m-%d")
        date_compact = date_kst.replace("-", "")

        # 워크플로별 티켓 템플릿
        tickets = []
        if workflow == "pilot_01":
            # §11 §8의 W1 5개 티켓 그대로
            tickets = self._pilot_01_tickets(date_compact)
        elif workflow == "custom":
            tickets = brief.get("tickets") or []
        else:
            raise ValueError(f"unknown workflow: {workflow}")

        # 큐에 발행
        from .sub_agents import dispatch_ticket
        dispatched_paths = []
        for t in tickets:
            p = dispatch_ticket(t)
            dispatched_paths.append(str(p.relative_to(REPO_ROOT)))

        # 보고서 (회원께)
        report = f"""# CEO 디스패치 — {workflow} ({date_kst})

## 발행된 작업 티켓 {len(tickets)}개

"""
        for t in tickets:
            approval = "★ 회원 ✅" if t.get("approval_required") else "자율"
            report += f"- **{t['task_id']}** → `{t['assigned_agent']}` ({approval})\n"
            report += f"  - {t['objective'].split(chr(10))[0][:100]}\n"

        report += f"""

## 다음 단계

데몬·worker_pool이 content/tasks/pending/ 에서 *순차적으로* 티켓을 픽업해 처리합니다.
완료된 결과는 content/tasks/completed/ 에 저장되고, CEO가 다시 검수해 라벨링합니다.

## 헌법 §11 준수

- 회원 ✅ 필요 티켓: {sum(1 for t in tickets if t.get('approval_required'))}개 (텔레그램 카드로 도착)
- 자율 실행 가능: {sum(1 for t in tickets if not t.get('approval_required'))}개
- 자동 실행 금지 조건(§11 §7) 7개 모두 자가 검수 완료
"""
        return [AgentResult.new(
            agent=self.name,
            kind="ceo_dispatch",
            title=f"🎩 CEO 디스패치 — {workflow} {len(tickets)}개 티켓",
            body_md=report,
            summary=f"{workflow} 워크플로 {len(tickets)}개 티켓 발행",
            course_id="core-campus-meta",
            meta={
                "brief": brief,
                "mode": "dispatch_workflow",
                "workflow": workflow,
                "ticket_count": len(tickets),
                "dispatched_paths": dispatched_paths,
            },
        )]

    def _pilot_01_tickets(self, date_compact: str) -> list[dict]:
        """파일럿 #1 (외주 강의) W1 5개 티켓 — §11 §8 그대로."""
        from datetime import datetime, timezone, timedelta
        deadline_base = datetime.now(timezone(timedelta(hours=9)))

        def _deadline(days_after: int, hour: int = 18) -> str:
            d = deadline_base + timedelta(days=days_after)
            d = d.replace(hour=hour, minute=0, second=0, microsecond=0)
            return d.isoformat()

        return [
            {
                "task_id": f"TASK-{date_compact}-001",
                "assigned_agent": "market_research_agent",
                "objective": "Core Campus 첫 외주 강의 파일럿(주제: 1인 사업가를 위한 AI 업무 자동화)의 시장 수요·경쟁 현황을 수치 기반으로 정리한다. 진입 권고 또는 비권고를 명확한 근거와 함께 결론 내린다.",
                "input_files": ["data/ceo_charter.md", "data/PILOT_01_DESIGN.md"],
                "output_file": f"content/tasks/completed/TASK-{date_compact}-001-market-research.md",
                "scope": {
                    "포함": ["검색 키워드 5개 + 월간 검색량 추정", "경쟁 강의 3~5개 분석", "타깃 페르소나 1명 9항목", "수요 점수 0~10 + 근거"],
                    "제외": ["SEO 도구 무단 사용", "경쟁사 비방"],
                },
                "do_not": ["가격 제안", "§4 금기 단어"],
                "acceptance_criteria": ["키워드 5개·근거 명시", "경쟁 분석 ≥3", "페르소나 9항목", "수요 점수 + 결론"],
                "approval_required": False,
                "deadline": _deadline(1),
                "next_step": f"TASK-{date_compact}-002 expert_sourcing_agent",
            },
            {
                "task_id": f"TASK-{date_compact}-002",
                "assigned_agent": "expert_sourcing_agent",
                "objective": "현재 CRM의 김그린dev(34/40)를 재평가하고, 추가 후보 2명 수집용 검색 키워드 5개 + 평가 기준 체크리스트를 정리한다.",
                "input_files": ["content/state/experts_crm.json", "data/EXTERNAL_EXPERT_SOURCING_POLICY.md"],
                "output_file": f"content/tasks/completed/TASK-{date_compact}-002-sourcing.md",
                "scope": {
                    "포함": ["김그린dev 재평가", "추가 키워드 5개", "빈 평가 시트 3행"],
                    "제외": ["자동 크롤링", "메시지 발송"],
                },
                "do_not": ["자동 메시지 발송", "플랫폼 외부 직거래 유도"],
                "acceptance_criteria": ["김그린dev 재평가 한 단락", "키워드 5개", "평가 시트 표"],
                "approval_required": False,
                "deadline": _deadline(2),
                "next_step": f"TASK-{date_compact}-003 curriculum_agent",
            },
            {
                "task_id": f"TASK-{date_compact}-003",
                "assigned_agent": "curriculum_agent",
                "objective": "외주 파일럿 강의 '1인 사업가를 위한 AI 업무 자동화' 6강 커리큘럼 초안. 각 강 12~15분, 측정 가능한 학습목표, 실습 결과물 1개씩.",
                "input_files": [f"content/tasks/approved/TASK-{date_compact}-001.json"],
                "output_file": f"content/tasks/completed/TASK-{date_compact}-003-curriculum.md",
                "scope": {
                    "포함": ["코스 제목·가치제안·약속 3개", "6강 학습목표·중요 개념 3·실습·도구"],
                    "제외": ["영상 본문", "가격 책정"],
                },
                "do_not": ["산출물·워크플로우·솔루션·효율적 같은 §8 금기", "과장 약속"],
                "acceptance_criteria": ["6강 구조 완성", "각 15분 단일 학습목표", "§4·§8 금기어 0"],
                "approval_required": False,
                "deadline": _deadline(3),
                "next_step": f"TASK-{date_compact}-004 outreach_draft_agent",
            },
            {
                "task_id": f"TASK-{date_compact}-004",
                "assigned_agent": "outreach_draft_agent",
                "objective": "김그린dev(kmong/gig/546955)에게 보낼 섭외 메시지 v1·v2 초안. §10.5 6단 구조 엄격. 가격은 질문만. 발송은 회원 직접.",
                "input_files": ["content/state/experts_crm.json", "data/EXTERNAL_EXPERT_SOURCING_POLICY.md", f"content/tasks/approved/TASK-{date_compact}-003.json"],
                "output_file": f"content/tasks/completed/TASK-{date_compact}-004-outreach.md",
                "scope": {
                    "포함": ["v1 파일럿 협업 350~450자", "v2 자문+촬영 변형 350~450자", "후속 메시지 200자", "발송 전 체크리스트"],
                    "제외": ["실제 발송", "가격 제안", "외부 직거래 유도"],
                },
                "do_not": ["'크몽 밖에서 직거래' 등 약관 위반", "100% 보장·월 N만 원 자동 등 §4 금기"],
                "acceptance_criteria": ["v1·v2 각 350~450자", "§10.5 6단 구조", "자가 검수 통과"],
                "approval_required": True,
                "deadline": _deadline(4),
                "next_step": f"TASK-{date_compact}-005 rights_checklist_agent",
            },
            {
                "task_id": f"TASK-{date_compact}-005",
                "assigned_agent": "rights_checklist_agent",
                "objective": "외주 전문가 계약 표준 조항 10개 체크리스트. 회원이 견적 받은 후 전문가에 발송할 양식.",
                "input_files": ["data/EXTERNAL_EXPERT_SOURCING_POLICY.md"],
                "output_file": f"content/tasks/completed/TASK-{date_compact}-005-rights-checklist.md",
                "scope": {
                    "포함": ["§10.6 10조항", "회원 ✅ 안내 1줄"],
                    "제외": ["법무 자문", "실제 PDF 서명"],
                },
                "do_not": ["사용권을 '양도'로 표현", "3년 기간 누락"],
                "acceptance_criteria": ["10조항 모두 명시", "회원 ✅ 안내"],
                "approval_required": True,
                "deadline": _deadline(5),
                "next_step": f"TASK-{date_compact}-006 production_planning_agent (W2)",
            },
        ]

    # ── W1 단계별 작업 (한 step당 1개 문서) ────────────────────────
    # 회원 원칙: 한 번에 하나만, 승인 후 다음 단계로
    W1_STEPS = {
        1: {
            "filename": "W1_STEP1_PROJECT_BRIEF.md",
            "title": "프로젝트 1페이지 방향 정리",
            "sections": """## 1. 프로젝트 목적
한 단락 (3~5문장).

## 2. 왜 이 강의가 Core Campus에 필요한지
한 단락. KPI·미션·타깃 관점에서 *왜 지금* *왜 이 주제* 인지.

## 3. 핵심 타깃
회원 확정 타깃 그대로. 단 *한 줄 페르소나*로 압축 (40자 이내).

## 4. 첫 강의 주제 방향
- 주제 한 줄 (회원 확정안 그대로)
- 사용 도구 (ChatGPT·Claude·Notion·Make/Zapier 중 *우선순위 매겨*)
- 강의 톤 (실전·실습 중심 / 이론 X)

## 5. 4주 안에 만들 *최소* 결과물
구체 3~4개. 욕심 X. 예: 영상 6편 / 상세페이지 1장 / 결제 페이지 연결(승인 후) / 첫 결제 3건.

## 6. 이번 프로젝트에서 하지 않을 것
헌법 §10 금지 + 회원 명시 금지 모두 포함. 6~8개.

## 7. 다음 Step 2에서 결정해야 할 것
짧게 3~5개. 예: 커리큘럼 6강 확정 / 도구 우선순위 / 강의 결과물 정의 등.""",
            "next_step_msg": "Step 1 완료. Step 2 진행 승인이 필요합니다.",
        },
        2: {
            "filename": "W1_STEP2_COURSE_CURRICULUM_DRAFT.md",
            "title": "커리큘럼 초안 (6강)",
            "sections": """## 코스 개요
- 코스 제목 (한 줄, 25~40자)
- 한 줄 가치제안
- 수강 후 약속 3개
- 선수지식
- 결과물

## 차시별 상세 (1~6강 모두)
각 차시:
### {N}강. {제목}
- 학습목표 (측정 가능한 동사로)
- 중요 개념 3개
- 실습 결과물
- 추천 분량 (분)
- 사용 도구

## 검증 체크
- §4 금기 위반 없음
- 각 차시가 *수강 후 손에 결과물 1개*를 남기는가
- 6편 모두 *15분 안에 끝나는 단일 학습목표*인가""",
            "next_step_msg": "Step 2 완료. Step 3 진행 승인이 필요합니다.",
        },
        3: {
            "filename": "W1_STEP3_EXPERT_SCORECARD.md",
            "title": "전문가 평가 스코어카드",
            "sections": """## 1. 평가 항목 8개
각 항목: 점수 0~5 / 0·3·5점 기준 / 검증 방법.

1. 실무 경험
2. 설명력
3. 포트폴리오 신뢰도
4. 1인 사업가 타깃 적합성
5. 화면녹화·강의 가능성
6. 협업 가능성
7. 예산 적합성
8. Core Campus 브랜드 적합성

## 2. 최종 합격 임계값
총점 / 항목별 최소 / 자동 탈락 조건.

## 3. 평가 시트 템플릿 (마크다운 표 + 빈 행 3개)

## 4. 빨간 깃발 5개 (자동 탈락)

## 5. CEO 검수 한 줄 패턴 (예시 3개)""",
            "next_step_msg": "Step 3 완료. Step 4 진행 승인이 필요합니다.",
        },
        4: {
            "filename": "W1_STEP4_OUTREACH_MESSAGE_DRAFT.md",
            "title": "섭외 메시지 초안 (발송 X — 초안만)",
            "sections": """⚠️ **이 문서는 초안일 뿐. 실제 발송은 회원 ✅ 후 *플랫폼 내부에서 회원이 직접*.**

## 1. 메시지 v1 — 파일럿 협업 제안 (부담 낮은 톤)
헌법 §10.5 6단 구조. 300~450자.

## 2. 메시지 v2 — 자문 1회 + 촬영 협업 변형
v1과 같은 톤. 옵션 제시.

## 3. 절대 포함하지 말 단어
- 헌법 §4 금기
- §8 금기
- 플랫폼 약관 위반 ("크몽 밖에서 직거래" / "직접 입금" 등)

## 4. 답신 후 후속 메시지 초안 (200자)

## 5. 발송 전 회원 체크리스트""",
            "next_step_msg": "Step 4 완료. Step 5 진행 승인이 필요합니다.",
        },
        5: {
            "filename": "W1_STEP5_PRODUCTION_CHECKLIST.md",
            "title": "제작 체크리스트 (30일)",
            "sections": """## W1~W4 마일스톤 체크박스
헌법 §10.8의 30일 25단계를 체크박스로.
각 단계: 담당(회원/CEO) / 완료 조건 / 막혔을 때 다음 액션.

## 회원 ✅ 필요 항목 (별도 표)

## 촬영 방식 결정 가이드
화면녹화 / 줌 인터뷰 / 대면 — 장단점 + B등급 추천.

## 판매 페이지 전 마지막 검토 5가지

## 30일 회고 KPI 5개""",
            "next_step_msg": "Step 5 완료. W1 종합 보고서를 작성하시겠습니까? (옵션)",
        },
    }

    def _w1_step(self, brief: dict) -> list[AgentResult]:
        """W1 단계별 작업 — *한 step당 문서 1개*. 회원 승인 대기 패턴.

        brief에서 filename/title/sections/next_step_msg/tone_guide 우선 받음.
        회원이 step마다 다른 요구해도 동적 대응 가능.
        """
        import logging
        log = logging.getLogger("ceo._w1_step")

        step_no = int(brief.get("step", 1))
        default = self.W1_STEPS.get(step_no, {})

        # brief 우선 → W1_STEPS fallback
        step = {
            "filename": brief.get("filename") or default.get("filename") or f"W1_STEP{step_no}.md",
            "title": brief.get("title") or default.get("title") or f"Step {step_no}",
            "sections": brief.get("sections") or default.get("sections") or "",
            "next_step_msg": brief.get("next_step_msg") or default.get("next_step_msg") or f"Step {step_no} 완료. Step {step_no+1} 진행 승인이 필요합니다.",
        }
        tone_guide = brief.get("tone_guide", "")
        forbidden = brief.get("forbidden_in_this_step", "")

        # 회원 확정 조건 (brief에서 받음 — 모든 step 공통)
        topic = brief.get("topic", "1인 사업가를 위한 AI 업무 자동화 입문")
        audience = brief.get("audience", "1인 사업가·프리랜서·크리에이터")
        tools = brief.get("tools", "ChatGPT·Claude·Notion·Make/Zapier")
        lessons = brief.get("lessons", "6편 × 12~15분")
        budget_tier = brief.get("budget_tier", "B등급")
        deadline = brief.get("deadline", "4주")
        platform = brief.get("platform", "1순위 크몽 / 백업 숨고")

        prompt = f"""W1 외부 전문가 강의 파일럿 — Step {step_no} 작업.

[회원 확정 조건]
- 주제 방향: {topic}
- 활용 도구 후보: {tools}
- 타깃: {audience}
- 차시: {lessons}
- 예산 등급: {budget_tier}
- 납기: {deadline}
- 플랫폼: {platform}

[회원 금지 사항 — 절대 위반 X]
- 실제 전문가에게 메시지 발송 X (이번 작업은 *초안만*)
- 결제·예산 지출 X
- 가격 제안 X (스코어카드의 가격 적합성은 *평가 기준*일 뿐, 실제 제안 X)
- 계약 조건 확정 X
- 사이트 공개 반영 X
- *한 번에 모든 문서 생성 금지* — 이번엔 Step {step_no} 1개 문서만

[Step {step_no} 산출물]
파일명: {step['filename']}
제목: {step['title']}

[필수 섹션]
{step['sections']}

[톤·규칙]
- §8 톤 (잡스+베이조스+한국 실전 코치). 자극·과장 X. 숫자·구체 O.
- §10 외주 정책 준수.
- 마크다운으로 작성. 코드펜스(```) 사용 금지.
- 다른 step 산출물 절대 작성 X — 오직 이 문서만.
- 문서 끝 라인은 절대 추가 X (마무리 멘트도 X — 깔끔하게 끝낸다).
{tone_guide and f'''
[이번 단계 추가 톤 가이드 (회원 명시)]
{tone_guide}
'''}
{forbidden and f'''
[이번 단계에서 절대 작성하지 말 것 (회원 명시)]
{forbidden}
'''}

이 문서 본문 *마크다운만* 출력하라."""

        try:
            md = self.call(prompt, max_tokens=4500).strip()
            # 코드펜스 제거 (안전망)
            if md.startswith("```"):
                md = md.split("```", 2)[1]
                if md.startswith(("markdown", "md")):
                    md = md.split("\n", 1)[1]
                md = md.rsplit("```", 1)[0].strip()
        except Exception as e:
            log.exception(f"[w1_step{step_no}] 생성 실패: {e}")
            raise

        # 파일 저장 — brief의 target_dir 우선 (없으면 data/w1/)
        target_dir = brief.get("target_dir", "data/w1")
        docs_dir = REPO_ROOT / target_dir
        docs_dir.mkdir(parents=True, exist_ok=True)
        doc_path = docs_dir / step['filename']
        doc_path.write_text(md, encoding="utf-8")
        log.info(f"[w1_step{step_no}] ✓ {doc_path} ({len(md):,}자)")

        # 보고서 형식 — brief에서 override 가능 (회원이 step별 다른 형식 원할 때)
        report_override = brief.get("_report_format_override", "")
        if report_override:
            report_prompt = f"""W1 Step {step_no} 작업 완료. 회원이 *명시한* 보고 형식 그대로 작성하라.

[작성한 문서]
- data/w1/{step['filename']}
- 제목: {step['title']}
- 분량: {len(md):,}자

{report_override}

§8 톤. 자극 X. 숫자 O. 마크다운 본문만 출력 (코드펜스 X)."""
        else:
            report_prompt = f"""W1 Step {step_no} 작업 완료. 회원께 7항목 보고서를 작성하라.

[작성한 문서]
- data/w1/{step['filename']}
- 제목: {step['title']}
- 분량: {len(md):,}자

[보고 형식 — 정확히 따를 것]

## 1. 이번 단계 목표
한 줄. Step {step_no} 무엇을 했는지.

## 2. 생성한 문서
파일 경로 1개 — data/w1/{step['filename']}
무엇을 담고 있는지 한 문단 요약.

## 3. 핵심 결정 사항 3~5개
이 문서에서 *명시한* 핵심 결정 사항 짧게.

## 4. 헌법 준수 체크
§4 금기 / §10 외주 정책 / 회원 금지 6개 위반 없음 확인.

## 5. 회원께 보여드리고 싶은 *한 단락 발췌*
이 문서에서 회원이 *가장 먼저 확인하면 좋은* 부분 한 단락 그대로 인용.

## 6. 승인 필요한 사항
이번 step에서 회원 ✅ 받아야 할 항목 — 없으면 "Step {step_no} 자체 승인 필요" 한 줄.

## 7. 다음 액션
Step {step_no+1 if step_no < 5 else 5} 미리보기 — *무엇을 할지* 짧게.

마지막 라인은 *반드시* 다음 정확한 문장:

> {step['next_step_msg']}

§8 톤. 자극 X. 숫자 O. 마크다운 본문만 출력 (코드펜스 X)."""

        report = self.call(report_prompt, max_tokens=2500).strip()
        if report.startswith("```"):
            report = report.split("```", 2)[1]
            if report.startswith(("markdown", "md")):
                report = report.split("\n", 1)[1]
            report = report.rsplit("```", 1)[0].strip()

        return [AgentResult.new(
            agent=self.name,
            kind="ceo_w1_step",
            title=f"🎩 CEO W1 Step {step_no} — {step['title']}",
            body_md=report,
            summary=f"Step {step_no}/{len(self.W1_STEPS)} 완료. 회원 ✅ 후 Step {min(step_no+1, 5)} 진행.",
            course_id="core-campus-meta",
            meta={
                "brief": brief,
                "mode": "w1_step",
                "step": step_no,
                "filename": step['filename'],
                "doc_path": f"data/w1/{step['filename']}",
                "doc_len": len(md),
            },
        )]

    # ── W1 외주 소싱 플랜 (5개 문서 + 보고서) ───────────────────
    def _w1_plan(self, brief: dict) -> list[AgentResult]:
        """W1 외주 소싱 플랜 — 회원 확정 사항(주제·타깃·차시·예산·납기) 기반.

        data/w1/ 에 5개 .md 문서 작성 + 7항목 보고서 1개를 pending에 떨어뜨림.
        """
        import logging
        log = logging.getLogger("ceo._w1_plan")

        params = brief or {}
        topic = params.get("topic", "AI로 내 사업 운영 시스템 만들기: 1인 사업가 자동화 입문")
        audience = params.get("audience", "1인 사업가·프리랜서·크리에이터·강사·디지털 상품 만들고 싶은 사람·ChatGPT/Claude 쓰지만 수익으로 연결 못 한 사람")
        lessons = params.get("lessons", "6편 × 12~15분")
        budget_tier = params.get("budget_tier", "B등급 (총예산 50~150만 원, 출연료 30~80만 원)")
        deadline = params.get("deadline", "4주")
        platform = params.get("platform", "1순위 크몽 / 백업 숨고")
        curriculum_seed = params.get("curriculum_seed", "")

        docs_dir = REPO_ROOT / "data" / "w1"
        docs_dir.mkdir(parents=True, exist_ok=True)

        # 5개 문서 — 각각 분리 호출 (max_tokens 안전 + 품질↑)
        DOCS = [
            (
                "W1_EXPERT_SOURCING_PLAN.md",
                f"""W1 외부 전문가 소싱 플랜 마크다운 문서를 작성하라.

[확정 사항]
- 주제: {topic}
- 타깃: {audience}
- 차시: {lessons}
- 예산: {budget_tier}
- 납기: {deadline}
- 플랫폼: {platform}

[필수 섹션]
## 1. 적합한 전문가 유형 5~6개
각 유형에 대해 — *역할 설명 / 필수 경험 / 우선순위 (높음·중간·낮음) / 검색 키워드 3개씩*.
예: Notion 자동화 전문가 / Make·Zapier 자동화 전문가 / ChatGPT·Claude 업무 자동화 강사 / 1인 사업가 생산성 컨설턴트 / AI 업무 시스템 구축 경험자.

## 2. 크몽 검색 전략
- 카테고리 추천 2~3개
- 검색 키워드 표 (한국어 5개 + 영어 2개)
- 1차 필터 조건 (별점·후기 수·응답률·가격대)

## 3. 숨고 검색 전략 (백업)
같은 형식으로 짧게.

## 4. 1주 안 후보 5명 확보 액션 플랜
- 일자별 (D1~D7) 액션
- 각 일자: 회원 직접 작업 / CEO 자동 작업 구분

## 5. 헌법 §10 준수 체크리스트
- 자동 크롤링·자동 메시지 금지 명시
- 플랫폼 내부 검색·수동 발송 원칙
- 첫 후보 입력은 회원 직접

마크다운 표 활용. 헌법 §8 톤 (잡스+베이조스+한국 실전 코치). 절대 자극·과장 톤 X.""",
            ),
            (
                "W1_COURSE_CURRICULUM_DRAFT.md",
                f"""W1 강의 커리큘럼 초안 마크다운 문서를 작성하라.

[확정 사항]
- 주제: {topic}
- 차시: {lessons} (총 6편, 각 12~15분)
- 타깃: {audience}

[회원 제안 커리큘럼 시드]
1강. 1인 사업가에게 AI 자동화가 필요한 이유
2강. ChatGPT와 Claude 역할 분리하기
3강. Notion으로 사업 운영 대시보드 만들기
4강. 반복 업무를 AI 프롬프트로 시스템화하기
5강. 콘텐츠/강의/상품 기획 자동화하기
6강. 나만의 AI 업무 루틴 만들기

[필수 섹션]
## 코스 개요
- 코스 제목 (한 줄, 25~40자)
- 한 줄 가치제안
- 수강 후 약속 3개 (구체 행동 단위)
- 선수지식
- 결과물(코스 완강 시 손에 남는 것)

## 차시별 상세 (각 차시당 다음 구조)
### {{N}}강. {{제목}}
- 학습목표 (측정 가능한 동사로)
- 중요 개념 3개
- 실습 결과물 (수강생이 직접 만드는 것)
- 추천 분량 (분)
- 사용 도구 (구체적 — ChatGPT / Claude / Notion / Make 등)

6강 모두 위 구조로. 시드를 그대로 쓰지 말고 §8 톤으로 다듬을 것.

## 검증 체크
- §4 금기 위반 없음 (과장 약속·AI 만능론 X)
- 각 차시가 *수강 후 손에 결과물 1개*를 남기는가
- 6편 모두 *15분 안에 끝나는 단일 학습목표*인가""",
            ),
            (
                "W1_OUTREACH_MESSAGE_DRAFT.md",
                f"""W1 크몽 전문가 섭외 메시지 초안 마크다운 문서를 작성하라.

[확정 사항]
- 코스 주제: {topic}
- 차시: {lessons}
- 예산: {budget_tier}
- 납기: {deadline}
- 권리: 헌법 §10.6 표준 10조항 (전용 사용권 / 3년 / 일시불 매절 기본)

[필수 섹션]
## 1. 메시지 v1 — 파일럿 협업 제안 (부담 낮은 톤)
헌법 §10.5의 6단 구조 따름:
1. 인사 + Core Campus 짧은 소개
2. 발견 경위 + 그 전문가 콘텐츠 1개 구체 칭찬 (`[전문가가 만든 콘텐츠]` placeholder)
3. 요청 사항 5줄 이하 (주제·차시·예산 범위·납기)
4. 권리 조항 한 줄 (자세한 건 별도 PDF/문서)
5. 답신 체크리스트 4개 (가능 여부 / 견적 / 일정 / 샘플)
6. 마무리 + 답신 기한

300~450자. 자연스러운 한국어. 영업·과장 톤 X.

## 2. 메시지 v2 — 자문 1회 + 촬영 협업 변형
v1 톤 유지하되 *6편 전체 위탁 부담스러우면 1회 자문+촬영부터*라는 옵션 제시.
v1과 같은 6단 구조.

## 3. 절대 포함하지 말 단어 (자가 검수 체크리스트)
- 헌법 §4 금기 단어 전체 (월 1,000만 원 같은 수익 보장 등)
- §8 금기 (워크플로우·솔루션·효율적·여러분 등)
- 플랫폼 약관 위반 단어 ("크몽 밖에서 직거래" / "직접 입금" / "외부 결제" — *이런 단어 절대 X*)

## 4. 답신 받은 후 다음 단계 안내문 (회원이 답신받았다고 가정 — 회원이 보낼 후속 메시지 초안)
짧게 200자. 다음 단계 — 견적 확정 → 표준 계약 조항 전달 → 에스크로 결제 → 브리핑.

## 5. 회원에게 — 발송 전 체크리스트
- 메시지 발송은 *플랫폼 내부에서 회원이 직접*
- v1 또는 v2 중 선택
- 전문가별 발견 경위 placeholder 채우기
- 첨부 파일 (있다면) 준비

§8 톤. 헌법 §10.3 절대 금지 사항 모두 자가 검수.""",
            ),
            (
                "W1_EXPERT_SCORECARD.md",
                f"""W1 전문가 후보 평가 스코어카드 마크다운 문서를 작성하라.

[확정 사항]
- 예산 등급: {budget_tier}
- 헌법 §10.4 필수 5개 + 가산 3개 기준

[필수 섹션]
## 1. 평가 항목 8개 — 회원 요청 사항 반영
1. 실무 경험
2. 설명력
3. 포트폴리오 신뢰도
4. 1인 사업가 타깃 적합성
5. 화면녹화/강의 가능성
6. 협업 가능성
7. 예산 적합성
8. Core Campus 브랜드 적합성

각 항목에 대해:
- 0~5점 척도
- 점수별 구체적 기준 (0점 / 3점 / 5점은 각각 어떤 상태인지)
- 검증 방법 (어디서 어떻게 확인하는지)

## 2. 최종 합격 임계값
- 총점 / 항목별 최소 점수 / 자동 탈락 조건

## 3. 평가 시트 템플릿 (마크다운 표)
| 전문가 ID | 이름 | 채널 | 1.실무 | 2.설명력 | 3.포트폴리오 | 4.타깃 | 5.촬영 | 6.협업 | 7.예산 | 8.브랜드 | 총점 | 등급 | CEO 코멘트 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| (빈 행 3개) |

## 4. 빨간 깃발 (자동 탈락 조건 5개)
- 평점 4.5 미만
- 후기 10개 미만
- 응답률 80% 미만
- 영상 샘플 0편
- 분쟁 이력 또는 블랙리스트

## 5. CEO 검수 한 줄 의견 패턴 (예시 3개)
헌법 §8 톤 — 짧고 단호하게.""",
            ),
            (
                "W1_PRODUCTION_CHECKLIST.md",
                f"""W1 강의 제작 체크리스트 마크다운 문서를 작성하라.

[확정 사항]
- 주제: {topic}
- 차시: {lessons}
- 예산: {budget_tier}
- 납기: {deadline}

[회원 요청 항목 — 모두 포함]
1. 전문가 섭외
2. 주제 확정
3. 커리큘럼 확정
4. 촬영 방식 결정 (화면녹화 / 줌 인터뷰 / 간단 대면)
5. 권리 동의 항목 (헌법 §10.6 10조항)
6. 강의 제목 (메인 + 보조)
7. 상세페이지 카피
8. 썸네일 문구
9. Core Campus 업로드 구조 (코스 ID·카테고리·차시 메타)
10. 판매 전 검토 항목

[필수 섹션]
## W1~W4 마일스톤별 체크박스
헌법 §10.8의 30일 25단계를 *체크박스 형식*으로.
각 항목: 담당(회원/CEO) / 완료 조건 / 막혔을 때 다음 액션.

## 회원 ✅ 필요 항목 (별도 표)
헌법 §10.2의 회원 직접·승인 항목 모두 한 표로.

## 촬영 방식 결정 가이드
- 화면녹화 / 줌 인터뷰 / 대면 — 각각 장단점 + B등급 예산에 맞는 추천

## 판매 페이지 전 마지막 검토 5가지
- 헌법 §4 금기 검수
- §8 톤 검수
- 권리 동의서 서명본 보관 확인
- 결제 페이지·환불 정책 회원 ✅
- CEO 코멘트 1줄

## 30일 회고용 KPI 5개
- 후보 발굴 N명
- 응답률
- 견적 받은 N건
- 계약 체결 1건
- 영상 등록 1건 + 첫 결제

§8 톤. 마크다운 체크박스 - [ ] 형식 활용.""",
            ),
        ]

        written = []
        for fname, prompt in DOCS:
            try:
                md = self.call(prompt, max_tokens=4500)
                # 코드펜스 제거
                md = md.strip()
                if md.startswith("```"):
                    md = md.split("```", 2)[1]
                    if md.startswith("markdown") or md.startswith("md"):
                        md = md.split("\n", 1)[1]
                    md = md.rsplit("```", 1)[0].strip()
                (docs_dir / fname).write_text(md, encoding="utf-8")
                written.append(fname)
                log.info(f"[w1_plan] ✓ {fname} ({len(md):,}자)")
            except Exception as e:
                log.exception(f"[w1_plan] ✗ {fname}: {e}")

        # 7항목 보고서
        report_prompt = f"""W1 외주 소싱 플랜 작업이 완료됐다. 회원님께 7항목 보고서를 작성하라.

[작성한 문서]
{chr(10).join(f'- data/w1/{name}' for name in written)}

[보고 형식 — 정확히 따를 것]

## 1. 이번 주 목표
한 줄. 회원 확정 사항({topic}) 기반.

## 2. 생성한 문서
{len(written)}개 문서 리스트 — 각 문서가 *무엇을 담고 있는지* 한 줄씩.

## 3. 추천 전문가 유형
W1_EXPERT_SOURCING_PLAN.md 의 1번 섹션을 요약. 5~6개 유형 + 우선순위.

## 4. 추천 커리큘럼
W1_COURSE_CURRICULUM_DRAFT.md 의 6강 제목 + 각 1줄 학습목표.

## 5. 섭외 메시지 초안
W1_OUTREACH_MESSAGE_DRAFT.md 의 v1 *전체 문구* (300~450자) 그대로 포함. 회원이 바로 복사해서 쓸 수 있게.

## 6. 승인 필요한 사항
헌법 §10.2 + §6에 따라 회원 ✅ 받아야 할 항목 6개 — 회원 요청 그대로:
- 실제 전문가에게 메시지 발송
- 예산 지출
- 출연료 또는 수익배분 조건 제안
- 계약 조건 확정
- 강의 판매 페이지 공개
- 유료 결제 연결

## 7. 다음 액션 (회원 / CEO 분리)
- 회원: 3개 — 가장 시급한 순서로
- CEO 자율: 3개 — 회원 결정 기다리지 않고 바로 시작 가능한

§8 톤. 자극 X. 숫자 O."""

        report = self.call(report_prompt, max_tokens=3500)

        return [AgentResult.new(
            agent=self.name,
            kind="ceo_w1_plan",
            title=f"🎩 CEO W1 외주 소싱 플랜 — {topic[:30]}",
            body_md=report,
            summary=f"W1 5개 문서 + 7항목 보고서. data/w1/ 에 저장됨.",
            course_id="core-campus-meta",
            meta={
                "brief": brief,
                "mode": "w1_plan",
                "documents_written": written,
                "docs_dir": "data/w1/",
            },
        )]

    # ── 첫 셋업 ───────────────────────────────────────────────
    def _first_setup(self, brief: dict) -> list[AgentResult]:
        prompt = """첫 임명 작업이다. Core Campus의 현재 상태(이미 19개 코스·블로그 발행 시작·티스토리 연동·1인 운영)를 기준으로 다음 7가지를 *한 묶음*으로 작성하라.

# 1. 30일 성장 로드맵
주 단위(W1~W4)로 *한 줄씩* 핵심 작업과 KPI 목표를 명시한다. 추상적 표현 금지, 숫자로 말한다.

# 2. 초기 강의 카테고리 5개
각 카테고리는 이름·한 줄 설명·해당 카테고리의 *초기 강의 후보 3개 제목*을 함께 제시한다.
한국 1인 사업가가 검색창에 칠 만한 단어로 짓는다.

# 3. 무료 유입 콘텐츠 아이디어 20개
티스토리·SEO 유입용. 각각 *제목 + 검색 의도 + 어떤 강의로 연결되는지* 한 줄.

# 4. 첫 유료 상품 후보 3개
각 후보는: *상품명·가격대(추정)·핵심 약속·왜 이 가격인지 근거*. 가격 변경은 회원 승인 필수임을 명시.

# 5. 월 순수익 1,000만 원까지 가는 수익 구조 초안
무료·저가·중가·고가 3~4단계 funnel. 각 단계: *상품 형태·가격·예상 전환율·월 목표 매출*.

# 6. CEO가 매일 반복할 운영 루틴
시간대별로 *내가(=CEO 에이전트가) 매일 무엇을 할지* 정의. 회원님 개입 시점 명시.

# 7. 회원에게 반드시 승인받아야 할 결정 목록
헌법 §6 외에 *오늘부터 30일 안에 발생할 결정 중 회원 승인이 필요한 것* 8~12개. 각 항목: *결정명·예상 시점·왜 회원 승인이 필요한지*.

출력 형식: 각 섹션을 `## N. 제목` 헤더로 시작. 한국어 마크다운. 숫자·구체 KPI·시한 포함. §8 톤(잡스+베이조스+한국 실전 코치) 유지."""

        body_md = self.call(prompt, max_tokens=12000)

        return [AgentResult.new(
            agent=self.name,
            kind="ceo_first_setup",
            title="CEO 첫 임명 작업 — 30일 로드맵·카테고리·콘텐츠·상품·수익 구조·운영 루틴·승인 목록",
            body_md=body_md,
            summary="CEO 첫 임명 — 7항목 셋업 완료",
            course_id="core-campus-meta",
            meta={
                "brief": brief,
                "mode": "first_setup",
                "charter_path": str(CHARTER_PATH.relative_to(REPO_ROOT)),
            },
        )]

    # ── 일일 보고 ─────────────────────────────────────────────
    def _daily_report(self, brief: dict) -> list[AgentResult]:
        today = brief.get("today_kst") or time.strftime("%Y-%m-%d")
        site_state = brief.get("site_state") or {}
        recent_kpi = brief.get("recent_kpi") or {}

        prompt = f"""오늘은 {today} (KST). Core Campus의 일일 보고를 헌법 §9 형식에 따라 작성하라.

[참고 컨텍스트]
- 사이트 상태: {json.dumps(site_state, ensure_ascii=False)}
- 최근 KPI: {json.dumps(recent_kpi, ensure_ascii=False)}

7항목 형식:

## 1. 오늘의 성장 목표
구체적 KPI 1~2개 (예: 블로그 글 3편 발행, 메인 페이지 코스 1개 추가).

## 2. 오늘 실행할 작업 3개
각 작업: *제목 + 30분 안에 완료 가능한 작업 단위 + 누가 할 일인지(CEO 자율 / 회원 승인 필요 / 다른 에이전트)*.

## 3. 예상 효과
1·2번을 다 했을 때 어떤 KPI가 얼마나 움직이는지. 숫자로.

## 4. 필요한 승인 사항
회원님 ✅ 받아야 할 결정. 없으면 "오늘은 없음" 명시.

## 5. 승인 없이 진행 가능한 작업
CEO 자율 범위 안의 작업 리스트.

## 6. 오늘 생성할 산출물
구체적 파일·페이지·블로그 글 제목.

## 7. 리스크와 방지책
오늘 1~2개 리스크 + 각각의 방지책.

§8 톤 — 숫자로, 자극 톤 없이, 단호하게."""

        body_md = self.call(prompt, max_tokens=4000)

        return [AgentResult.new(
            agent=self.name,
            kind="ceo_daily_report",
            title=f"CEO 일일 보고 — {today}",
            body_md=body_md,
            summary=f"{today} CEO 일일 보고",
            course_id="core-campus-meta",
            meta={"brief": brief, "mode": "daily_report", "today_kst": today},
        )]

    # ── 산출물 검토 ────────────────────────────────────────────
    def _review_pending(self, brief: dict) -> list[AgentResult]:
        items = brief.get("items") or []
        prompt = f"""다음 산출물들이 회원 승인 대기 중이다. CEO로서 각 산출물을 헌법 §4 금기·§5 자율 범위·§8 톤 기준으로 검토하라.

[산출물 목록]
{json.dumps(items, ensure_ascii=False, indent=2)}

각 산출물에 대해 다음 형식으로 응답:

## [산출물 ID] — [제목]

**CEO 판단**: ✅ 통과 / ⚠️ 수정 권고 / ❌ 반려

**근거**: 헌법 §X에 따라 ...

**수정 권고**(⚠️·❌ 경우만): 구체적으로 어떻게 고칠지

**회원님께 드리는 한 줄**: 회원님이 최종 결정 시 참고할 짧은 코멘트

마지막에 ## 총평 — 오늘 검토 N건 중 통과 N건 / 수정 N건 / 반려 N건. 우선순위 추천 1~2개."""

        body_md = self.call(prompt, max_tokens=6000)

        return [AgentResult.new(
            agent=self.name,
            kind="ceo_review",
            title=f"CEO 산출물 검토 — {len(items)}건",
            body_md=body_md,
            summary=f"{len(items)}건 검토",
            course_id="core-campus-meta",
            meta={"brief": brief, "mode": "review_pending", "item_count": len(items)},
        )]

    # ── 분기 리뷰 ────────────────────────────────────────────
    def _quarterly_review(self, brief: dict) -> list[AgentResult]:
        period = brief.get("period", "Q1")
        kpi = brief.get("kpi_snapshot") or {}
        prompt = f"""분기 리뷰 — {period}. 헌법 §7 단계별 목표 대비 진척도를 평가하라.

[KPI 스냅샷]
{json.dumps(kpi, ensure_ascii=False, indent=2)}

다음 형식:

## 1. 목표 대비 진척
각 KPI: 목표 / 현재 / 달성률 / 평가(잡스 톤 — 짧고 단호하게).

## 2. 이번 분기 잘된 것 3개

## 3. 이번 분기 안 된 것 3개 + 원인

## 4. 다음 분기 우선순위 3개
각 우선순위: *작업명 / KPI 목표 / 회원 승인 필요 여부*.

## 5. 회원님 결정 필요 사항
다음 분기에 회원 승인을 받아야 할 결정 목록.

§8 톤."""

        body_md = self.call(prompt, max_tokens=6000)

        return [AgentResult.new(
            agent=self.name,
            kind="ceo_quarterly",
            title=f"CEO 분기 리뷰 — {period}",
            body_md=body_md,
            summary=f"{period} 분기 리뷰",
            course_id="core-campus-meta",
            meta={"brief": brief, "mode": "quarterly_review", "period": period},
        )]
