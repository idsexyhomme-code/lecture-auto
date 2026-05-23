# 사이트 구조 Audit — 2026-05-16

## 1차 폴더 (35개)

### 코스 (claude-* 15개 + 기타 4개 = 19개)
- claude-autowork
- claude-bizflow
- claude-content-engine
- claude-customer-script
- claude-customer-support
- claude-daily-recap
- claude-intro-email
- claude-launchpad
- claude-mail-writing
- claude-meeting-notes
- claude-monthly-revenue
- claude-pricing-page
- claude-sop
- claude-sop-onboarding
- claude-youtube-plan
- deepwork-1hr
- deepwork-1hr-test (테스트 — 정리 필요)
- core-campus-general
- core-campus-meta
- tax-basics-solopreneur

### Core Compass (신규)
- landing/core-compass/ (v1)
- landing/core-compass/v3/ (v3 — 신규 v3 위치)

### 기타 디렉토리
- `_design_previews/` — 이전 디자인 시안 (정리 필요?)
- `blog-drafts/` — Tistory 발행 전 드래프트
- `blog-images/` — 블로그 이미지
- `card-news/` — 카드뉴스
- `courses/` — 코스 인덱스
- `images/` — 사이트 이미지
- `me/` — 운영자 페이지
- `posts/` — 일반 포스트

### 루트 파일
- `index.html` — 메인 홈페이지 (§6 큰 결재 영역)
- `styles.css` — 전역 스타일 (기존)
- `admin.css`, `admin.js` — 관리자 영역

---

## 디자인 시스템 적용 우선순위

| 우선 | 페이지 | 헌법 | 영향도 |
|---|---|---|---|
| 1 | site/landing/core-compass/v3/ (신규) | §5 CEO 자율 | 즉시 — 결제 가능한 출시 가능 |
| 2 | site/courses/ 인덱스 | §5 CEO 자율 (인덱스만) | 코스 목록 노출 |
| 3 | 19개 코스 페이지 본문 | §5 부분 자율 (본문) / §6 카피 변경 큰 거 | 사용자 체류 |
| 4 | site/blog-drafts/ 템플릿 | §5 자율 | 블로그 신규 발행 |
| 5 | site/posts/ 기존 | §5 자율 | 기존 콘텐츠 톤 정리 |
| **§6** | **site/index.html (메인)** | **§6 회원 ✅ 필수** | 큰 결재 — 전체 리브랜딩급 |

---

## 발견사항

### 정리 후보
1. **deepwork-1hr-test** — 테스트 폴더 (CEO 자율 결정으로 삭제 가능)
2. **_design_previews/** — 시안 폴더 (현재 design-system/preview/ 로 통합 가능)

### 누락 폴더
- `site/landing/core-compass/v3/og.png` (현재 og.svg만 있음, 소셜 공유는 PNG 필요할 수 있음 — sharp/rsvg-convert 로 추후 변환)

### 디자인 시스템 미적용 페이지 (CSS 변수 사용 안 함)
- index.html — 메인 (§6 큰 결재 필요)
- 15개 claude-* 코스 — 자체 styles.css 사용 (디자인 시스템 미적용)
- posts/ 기존 글 — 자체 스타일

---

## 다음 조치 (CEO 자율)
1. Core Compass v3 출시 페이지 5개 완성 — **이번 30단계 안에 끝남**
2. 코스 페이지 1개 디자인 시스템 적용 샘플 — **[L14/30]에서**
3. 메인 페이지 리디자인은 **회원 ✅ 시안 작성만** (실제 변경 안 함)
