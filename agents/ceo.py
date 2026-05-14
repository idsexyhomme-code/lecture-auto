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
        return self._daily_report(brief)

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
