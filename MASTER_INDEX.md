# 누적 120단계 마스터 인덱스 — 2026-05-17

> 4차에 걸친 회원 부재 자율 진행 결과. 모든 산출물·문서·코드 한 페이지 인덱스.

## 1차 30단계 — Design System v1 + Core Compass 출시 페이지 5개

- [REPORT_30_STEPS.md](computer:///Users/seohyeongmin/Desktop/강의 홈페이지 제작/REPORT_30_STEPS.md)
- design-system/ (tokens·base·fonts·components·SKILL·CHANGELOG·QUICKSTART)
- site/landing/core-compass/v3/ (index·result·success·expired·email·404·og.svg)

## 2차 30단계 — 19개 코스 v2 + 메인 시안 + 결제 3 PG 인프라

- [REPORT_30_STEPS_v2.md](computer:///Users/seohyeongmin/Desktop/강의 홈페이지 제작/REPORT_30_STEPS_v2.md)
- 20개 코스 v2 생성 (스크립트 자동화)
- 메인 페이지 v2 시안 + 결제 admin
- 페이앱·토스·스마트스토어 3 PG 통합 인프라
- scripts/ — payment_router·payment_webhooks·design_qa·generate_course

## 3차 30단계 — site_builder 보호 + 출시 준비 + 정책

- [REPORT_30_STEPS_v3.md](computer:///Users/seohyeongmin/Desktop/강의 홈페이지 제작/REPORT_30_STEPS_v3.md)
- v2 별도 경로 운영 (site/v2/·site/courses-v2/)
- 토스 Widget 결제 + sitemap 자동 생성
- 이용약관·개인정보처리방침 페이지
- 출시 체크리스트 + Core Compass 자동화 가이드

## 4차 30단계 — Core Compass v4 (yongyong 흡수 + 차별화)

- [REPORT_30_STEPS_v4.md](computer:///Users/seohyeongmin/Desktop/강의 홈페이지 제작/REPORT_30_STEPS_v4.md)
- yongyong.ai 분석 + 운명 vs 실행 차별화
- 새 컴포넌트 (countdown·social-proof·progress-preview)
- Core Compass v4 (index·wait·share-card)
- 출시 마케팅 카피 (SNS·블로그·이메일·광고)

---

## 📂 분야별 인덱스

### 디자인 시스템
- [design-system/SKILL.md](computer:///Users/seohyeongmin/Desktop/강의 홈페이지 제작/design-system/SKILL.md) — 모든 페이지 생성 규칙서 (자동 주입)
- [design-system/tokens.json](computer:///Users/seohyeongmin/Desktop/강의 홈페이지 제작/design-system/tokens.json) — 색·타이포·간격 토큰
- [design-system/base.css](computer:///Users/seohyeongmin/Desktop/강의 홈페이지 제작/design-system/base.css) — CSS 변수 + 리셋 + 한글 최적화
- [design-system/components.css](computer:///Users/seohyeongmin/Desktop/강의 홈페이지 제작/design-system/components.css) — Button·Card·Pricing·FAQ·Toast·Modal·Tooltip·Countdown·SocialProof·ProgressPreview
- [design-system/QUICKSTART.md](computer:///Users/seohyeongmin/Desktop/강의 홈페이지 제작/design-system/QUICKSTART.md)
- [design-system/preview/index.html](computer:///Users/seohyeongmin/Desktop/강의 홈페이지 제작/design-system/preview/index.html) — 살아있는 컴포넌트 갤러리

### Core Compass 페이지
- [v3 (안정판)](computer:///Users/seohyeongmin/Desktop/강의 홈페이지 제작/site/landing/core-compass/v3/index.html)
- [v4 (yongyong 흡수)](computer:///Users/seohyeongmin/Desktop/강의 홈페이지 제작/site/landing/core-compass/v4/index.html) — 추천
- result·success·expired·email·404 (v3에 있음)
- wait·share-card (v4에 있음)
- [checkout-payapp.html](computer:///Users/seohyeongmin/Desktop/강의 홈페이지 제작/site/landing/core-compass/v3/checkout-payapp.html)

### 사이트 v2 (별도 경로 — 출시 후 통합 결정)
- [site/v2/index.html](computer:///Users/seohyeongmin/Desktop/강의 홈페이지 제작/site/v2/index.html) — 메인 v2
- [site/courses-v2/](computer:///Users/seohyeongmin/Desktop/강의 홈페이지 제작/site/courses-v2/index.html) — 20개 코스 v2
- [site/admin/payments.html](computer:///Users/seohyeongmin/Desktop/강의 홈페이지 제작/site/admin/payments.html) — 결제 관리

### 정책·약관
- [site/terms.html](computer:///Users/seohyeongmin/Desktop/강의 홈페이지 제작/site/terms.html) — 이용약관
- [site/privacy.html](computer:///Users/seohyeongmin/Desktop/강의 홈페이지 제작/site/privacy.html) — 개인정보처리방침
- [REFUND_POLICY.md](computer:///Users/seohyeongmin/Desktop/강의 홈페이지 제작/REFUND_POLICY.md)

### 결제 시스템
- [PAYMENT_PG_COMPARISON.md](computer:///Users/seohyeongmin/Desktop/강의 홈페이지 제작/PAYMENT_PG_COMPARISON.md) — PG 3사 비교
- [PAYMENT_INTEGRATION_GUIDE.md](computer:///Users/seohyeongmin/Desktop/강의 홈페이지 제작/PAYMENT_INTEGRATION_GUIDE.md) — 연동 가이드
- [PAYMENT_TEST_SCENARIOS.md](computer:///Users/seohyeongmin/Desktop/강의 홈페이지 제작/PAYMENT_TEST_SCENARIOS.md) — 7가지 테스트
- [.env.payment.example](computer:///Users/seohyeongmin/Desktop/강의 홈페이지 제작/.env.payment.example) — 환경변수 템플릿
- [scripts/payment_router.py](computer:///Users/seohyeongmin/Desktop/강의 홈페이지 제작/scripts/payment_router.py) — 통합 라우터
- [scripts/payment_webhooks.py](computer:///Users/seohyeongmin/Desktop/강의 홈페이지 제작/scripts/payment_webhooks.py) — 결제 완료 콜백

### 출시 준비
- [LAUNCH_CHECKLIST_CORE_COMPASS.md](computer:///Users/seohyeongmin/Desktop/강의 홈페이지 제작/LAUNCH_CHECKLIST_CORE_COMPASS.md) — 출시 직전 체크
- [CORE_COMPASS_AUTOMATION.md](computer:///Users/seohyeongmin/Desktop/강의 홈페이지 제작/CORE_COMPASS_AUTOMATION.md) — 결제→진단 자동 흐름
- [CORE_COMPASS_LAUNCH_COPY.md](computer:///Users/seohyeongmin/Desktop/강의 홈페이지 제작/CORE_COMPASS_LAUNCH_COPY.md) — 마케팅 카피

### 시장 분석
- [design-system/references/external-analysis.md](computer:///Users/seohyeongmin/Desktop/강의 홈페이지 제작/design-system/references/external-analysis.md) — 인프런·클래스101·패스트캠퍼스·토스·노션
- [design-system/references/YONGYONG_ANALYSIS.md](computer:///Users/seohyeongmin/Desktop/강의 홈페이지 제작/design-system/references/YONGYONG_ANALYSIS.md) — 사주 경쟁 분석
- [design-system/references/combined-analysis.md](computer:///Users/seohyeongmin/Desktop/강의 홈페이지 제작/design-system/references/combined-analysis.md) — Track A+B 결합
- [COMPETITIVE_ANALYSIS.md](computer:///Users/seohyeongmin/Desktop/강의 홈페이지 제작/COMPETITIVE_ANALYSIS.md) — 시장 4분면

### 사이트 audit
- [AUDIT_SITE_STRUCTURE.md](computer:///Users/seohyeongmin/Desktop/강의 홈페이지 제작/AUDIT_SITE_STRUCTURE.md) — 폴더 구조
- [COURSE_PAGES_DESIGN_GAP.md](computer:///Users/seohyeongmin/Desktop/강의 홈페이지 제작/COURSE_PAGES_DESIGN_GAP.md) — 코스 매핑
- [COURSE_V2_MIGRATION.md](computer:///Users/seohyeongmin/Desktop/강의 홈페이지 제작/COURSE_V2_MIGRATION.md) — 마이그레이션
- [SEO_AUDIT.md](computer:///Users/seohyeongmin/Desktop/강의 홈페이지 제작/SEO_AUDIT.md) — SEO 메타
- [MOBILE_A11Y_AUDIT.md](computer:///Users/seohyeongmin/Desktop/강의 홈페이지 제작/MOBILE_A11Y_AUDIT.md) — 모바일·접근성
- [BLOG_TEMPLATE_AUDIT.md](computer:///Users/seohyeongmin/Desktop/강의 홈페이지 제작/BLOG_TEMPLATE_AUDIT.md) — 블로그
- [MAIN_V1_ANALYSIS.md](computer:///Users/seohyeongmin/Desktop/강의 홈페이지 제작/MAIN_V1_ANALYSIS.md) — 메인 분석
- [SYSTEM_HEALTH_CHECK.md](computer:///Users/seohyeongmin/Desktop/강의 홈페이지 제작/SYSTEM_HEALTH_CHECK.md) — 시스템 헬스
- [SWAP_REPORT.md](computer:///Users/seohyeongmin/Desktop/강의 홈페이지 제작/SWAP_REPORT.md) — v2 swap

### 헌법·자동화
- [data/ceo_charter.md](computer:///Users/seohyeongmin/Desktop/강의 홈페이지 제작/data/ceo_charter.md) — §12 디자인 시스템 정책 추가됨
- [data/CEO_AGENT_DISPATCH_PROTOCOL.md](computer:///Users/seohyeongmin/Desktop/강의 홈페이지 제작/data/CEO_AGENT_DISPATCH_PROTOCOL.md) — §11 디스패치
- [agents/ui_designer.py](computer:///Users/seohyeongmin/Desktop/강의 홈페이지 제작/agents/ui_designer.py) — SKILL.md 자동 주입
- [agents/site_developer.py](computer:///Users/seohyeongmin/Desktop/강의 홈페이지 제작/agents/site_developer.py) — SKILL.md 자동 주입
- [agents/sub_agents.py](computer:///Users/seohyeongmin/Desktop/강의 홈페이지 제작/agents/sub_agents.py) — 11명 sub-agent (design_qa 추가)
- [agents/base.py](computer:///Users/seohyeongmin/Desktop/강의 홈페이지 제작/agents/base.py) — HARD/SOFT ban 확장

### 회원 미리보기 .command (더블클릭)
- [preview-core-compass.command](computer:///Users/seohyeongmin/Desktop/강의 홈페이지 제작/preview-core-compass.command) — v2 (port 7920)
- [preview-core-compass-v3.command](computer:///Users/seohyeongmin/Desktop/강의 홈페이지 제작/preview-core-compass-v3.command) — v3 (port 7921)
- [preview-courses-v2.command](computer:///Users/seohyeongmin/Desktop/강의 홈페이지 제작/preview-courses-v2.command) — 코스 v2 (port 7922)
- [preview-core-compass-v4.command](computer:///Users/seohyeongmin/Desktop/강의 홈페이지 제작/preview-core-compass-v4.command) — v4 (port 7923) ⭐

---

## 📊 누적 통계

| 카테고리 | 1차 | 2차 | 3차 | 4차 | 합계 |
|---|---|---|---|---|---|
| HTML 페이지 | 6 | 24 | 7 | 4 | **41** |
| Python 스크립트 | 0 | 4 | 4 | 0 | **8** |
| 디자인 시스템 파일 | 7 | 1 | 0 | 0 | **8** |
| 분석·가이드 문서 | 6 | 6 | 4 | 5 | **21** |
| 에이전트 강화 | 2 | 1 | 1 | 0 | **4** |
| 정책 문서 | 0 | 1 | 2 | 1 | **4** |
| **TOTAL** | | | | | **86 파일** |

**자가 검수 결과**: 모든 새 페이지 self_review pass + design_qa score 평균 90+
