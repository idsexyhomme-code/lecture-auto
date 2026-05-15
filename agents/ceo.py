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
        return self._daily_report(brief)

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
