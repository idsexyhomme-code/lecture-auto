# Design System CHANGELOG

## v1.1 — 2026-05-16

### Added
- `tokens.json` motion·z-index 토큰 추가 (animation duration, easing, layer stack)
- `base.css` 동일 CSS 변수로 노출
- `components.css` Toast / Modal / Tooltip 컴포넌트 추가
- `preview/index.html` 살아있는 컴포넌트 갤러리
- `SKILL.md` §9 회원 시그니처 패턴 명시 (Track A 학습 반영)
- `SKILL.md` §10 v3 컴포넌트 표준화 결과 표

### Inspired by
- Track A — 회원 작업물 41개 PNG 직접 분석 결과 반영
- Track B — 외부 5개 사이트 (인프런·클래스101·패스트캠퍼스·토스 테크·노션 KR) 결합

### Discovered
- 회원님 감귤박람회 컬러 팔레트가 Core Compass v1과 일치 → **회원 감각에 이미 있던 톤**
- "작은 + 큰 카피" 2단 패턴은 회원 몽생이 자막 표준
- "Q. 빨간 prefix" 패턴은 회원 한국환경공단 자막 표준
- "딱! ~해드려마씸" 친근한 제주 톤은 회원 JTP 썸네일에서 확인

## v1.0 — 2026-05-16

### Initial Setup
- `tokens.json` 컬러·타이포·간격·라운드·그림자·트랜지션·컨테이너 토큰
- `base.css` CSS 변수 + 리셋 + 한글 타이포 최적화 (자간 음수, 행간 1.65, word-break keep-all)
- `fonts.css` Pretendard Variable + GmarketSans + Gotham + Noto Sans KR (CDN + 자가호스팅)
- `components.css` Button / Badge / Card / BulletCard / StepDot / Report / Pricing / FAQ / Hero / FinalCTA / Header / Footer
- `SKILL.md` 디자인 시스템 규칙서
- `_hdd_scan/` 회원 HDD 자산 매니페스트 (폰트 2,809 / 디자인 1,090 / 이미지 5,000 / PDF 76)
- `references/raw-psd-previews/` 41개 회원 작업물 PNG 변환본
- `references/external-analysis.md` 외부 5개 사이트 직접 캡쳐 분석
- `references/combined-analysis.md` Track A + B 결합 가이드

### Outputs
- `site/landing/core-compass/index.html` v2 (Claude Design 초안 → 자가 디자인시스템 적용)
- `site/landing/core-compass/v3/index.html` v3 (Track A+B 학습 반영)
