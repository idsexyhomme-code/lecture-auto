# Core Campus Design System v1.0

> 이 파일은 **모든 페이지·컴포넌트 생성 전에 반드시 읽는다.** Claude Design 기본값·CDN 폰트 함정을 피하기 위함.

## 1. 폰트 (단 4종만 사용)

| 용도 | 폰트 | 출처 |
|---|---|---|
| 본문·UI | `Pretendard Variable` | 자가호스팅 + jsdelivr CDN |
| 헤드라인 임팩트 | `GmarketSans` Bold | 자가호스팅 (HDD) |
| 영문 강조 (숫자·라벨) | `Gotham` | 자가호스팅 (HDD, 회원 라이선스) |
| 다국어 폴백 | `Noto Sans KR` | Google Fonts CDN |

**금지**: Roboto·Open Sans·Lato 같은 외국 산세리프 — 한글 자형이 어색함.

## 2. 컬러 시스템

| 변수 | 값 | 용도 |
|---|---|---|
| `--color-coral` | `#D85A30` | 1차 CTA·강조·악센트 |
| `--color-deep-blue` | `#2C4E6B` | 최종 CTA·신뢰감·잠금 안내 |
| `--color-bg` | `#F5EFE0` | 베이지 본 배경 (제주 톤) |
| `--color-ink` | `#1F1F1F` | 본문 텍스트 |
| `--color-text-muted` | `#6B6B6B` | 보조 텍스트 |
| `--color-border` | `#E5DFD3` | 카드·구분선 |

**임의 컬러 추가 금지.** 시맨틱 확장 필요 시 tokens.json에 먼저 등재.

## 3. 한글 타이포 7가지 규칙

1. **letter-spacing은 음수** (-0.015em ~ -0.028em). 영문 표준 0은 한글에서 헐거워 보임.
2. **line-height는 1.55~1.75** (영문보다 0.1 넓게). 한글은 자모 합쳐진 형태라 행간 좁으면 답답.
3. **word-break: keep-all**. 단어 단위로 줄바꿈 (음절 가운데 끊기지 않게).
4. **클램프(clamp)로 반응형 폰트**. `clamp(28px, 5.5vw, 52px)` 형태.
5. **`font-feature-settings: 'ss10', 'cv11'`** — Pretendard 한글 자형 최적화.
6. **숫자·영문 라벨은 Gotham + tabular-nums**. 가격·통계·날짜에 사용.
7. **헤드라인 H1만 GmarketSans**. 본문에 쓰면 가독성 망함.

## 4. 컴포넌트 — 그대로 가져다 쓰는 클래스

| 컴포넌트 | 클래스 |
|---|---|
| Button (1차 CTA) | `.btn.btn--primary.btn--lg` |
| Button (보조) | `.btn.btn--secondary` |
| Badge (한정·할인) | `.badge` 또는 `.badge.badge--blue` |
| Card | `.card.card--feature` |
| Bullet card | `.bullet-card` |
| 6단계 단계점 | `.step-dot` |
| PDF 리포트 미리보기 | `.report` + `.report__section--locked` |
| Pricing card | `.pricing` + `.pricing__ribbon` |
| FAQ 아코디언 | `.faq` (details/summary) |
| Hero | `.hero` |
| Final CTA (워밍블루 박스) | `.final-cta` |
| Sticky header | `.site-header` |
| Footer | `.site-footer` |

**새 컴포넌트 만들기 전에 위 목록 다시 확인.** 9할은 조합으로 해결됨.

## 5. 카피 가이드 (헌법 §4 가드)

**금지 표현 (자동 차단됨)**
- "월 1,000만원 보장 / 무조건 성공 / 100% 맞는 진단 / 운명대로 돈 번다"
- "하루 10분 자동수익 / 자동으로 부자 / 잠자면서 버는"
- 의약품·치료·정신질환 단정 표현

**선호 표현**
- "정리합니다 / 제안합니다 / 참고합니다 / 시도해볼 수 있습니다"
- "1인 사업 진단 / 자기이해 기반 / 90일 실행 순서"
- "비교한 결과 / 일반적으로 / 평균적으로"

## 6. 레이아웃 — 절제 원칙

| 항목 | 표준 |
|---|---|
| 본문 max-width | `720px` (`.container`) |
| 좁은 글 max-width | `560px` (`.container--narrow`) |
| 섹션 간 padding | `80px` 상하 (모바일 `64px`) |
| 카드 그림자 | `--shadow-sm` 또는 `--shadow-md` 까지만 |
| 라운드 | 카드 `16px`, 버튼 `10px`, 알약 `9999px` |
| 애니메이션 | `fadeUp 600ms` + `prefers-reduced-motion` 존중 |

**AI 티 안 나게:**
- 그림자 진하게 X
- 그라데이션 헤드라인 X (코랄 단색 강조만)
- 무지개·네온·과한 글래스모피즘 X
- 이모지는 자물쇠(🔒) 정도만 — 형용사로 도배하는 거 X

## 7. 페이지 생성 순서 (체크리스트)

페이지 만들 때 이 순서대로:

1. `<link rel="stylesheet" href="/design-system/base.css">` 먼저 import
2. `<link rel="stylesheet" href="/design-system/components.css">` 그 다음
3. 페이지 고유 CSS는 마지막 (있다면)
4. 모든 색·간격·폰트는 CSS 변수 사용 (`var(--color-coral)` 등) — 하드코딩 금지
5. 모바일 우선 작성 → 데스크탑은 `@media (min-width: 720px)` 로 추가
6. self_review 룰 (HARD/SOFT ban) 통과 확인
7. CEO 게이트 (가드 대상 산출물) 통과 확인

## 8. 갱신 정책

- tokens.json·base.css·components.css 변경 시 → **반드시 회원 ✅** (헌법 §6 메인 페이지 카피 변경과 동급으로 취급)
- SKILL.md 본문 수정 시 → CEO 자율 (자가 학습 F3 결과 반영 등)
- 새 컴포넌트 추가 → 회원 ✅ (오용 방지)

---

## 9. 회원님 시그니처 패턴 (Track A 학습)

### 9-1. 컬러 일치 확인
회원님이 직접 작업한 **감귤박람회 풋귤축제 썸네일**의 컬러 팔레트가 Core Compass와 동일:
- 옅은 베이지/크림 배경 ≈ `#F5EFDC` (≈ `--color-bg`)
- 그린 액센트 ≈ `#7A9C3E` (≈ `--color-olive`)
- 코랄 외곽선/보더 ≈ `#D85A30` (= `--color-coral`)

→ 이 톤은 회원 감각에 이미 있던 것. **변경할 이유 없음**. 모든 페이지에 동일 톤 유지.

### 9-2. "작은 카피 + 큰 카피" 2단 헤더 패턴
회원님 **몽생이 어린이집 자막** 패턴:
```
밝은 햇살 아래
아이들을 반기는 첫 공간   ← 더 크게·굵게
```
→ 모든 섹션 헤더에 적용: `.section-title-2line__small` + `.section-title-2line`

### 9-3. Q. 색 강조 prefix
회원님 **한국환경공단 자막** 패턴:
> "**Q.** 다른 환경 보호 활동에 참여해본 적이 있나요?"

→ FAQ 컴포넌트 `.faq__q-label` 클래스로 표준화. Q. 글자만 코랄.

### 9-4. 친근한 제주 톤
회원님 **JTP 영상 썸네일** 카피:
> "딱! 요약해드려마씸"

→ 부 헤드라인·Footer fineprint에 친근한 한 줄 추가 권장:
- "딱, 한 장으로 정리해드릴게요"
- "이번 주 안에 시작하실 수 있어요"
- 단, **방언 직접 사용은 신중히** (전국 대상 카피라)

### 9-5. 사진 + 일러스트 + 타이포 3-layer
회원님 영상 썸네일 구도. 정적 페이지에서는:
- Hero에 **시각 요소** (현재: 6개 에이전트 동그라미)
- 카드에 **하이라이트 원** 등 (`.receive-card::before`)

---

## 10. v3 학습 — 컴포넌트 표준화 결과

| 컴포넌트 | 위치 | 회원 톤 |
|---|---|---|
| `.promo-bar` | 페이지 최상단 풀폭 코랄 | 패스트캠퍼스 식 |
| `.agent-orbit` | Hero 6개 동그라미 | 노션 KR 일러스트 + 회원 3색 |
| `.section-title-2line` | 모든 섹션 헤더 | **몽생이 자막 2단 패턴** |
| `.receive-card` (with ::before) | 받게 되는 것 카드 | 회원 3-layer 구도 흔적 |
| `.pricing--accent` | 가격 카드 | 코랄 그라데이션 보더 (절제) |
| `.faq__q-label` | FAQ Q. prefix | **한국환경공단 자막** |
| `.hero__friendly` | 친근한 톤 한 줄 | **JTP 썸네일** |

---

**최종 업데이트**: 2026-05-16 v1.1 (Track A+B 학습 반영)
**자산 출처**: 회원님 외장 HDD 폰트 2,809개 중 4종 + 회원 작업물 41개 PNG 분석 + 외부 5개 사이트 (인프런·클래스101·패스트캠퍼스·토스 테크·노션 KR)
**변경 이력**: design-system/CHANGELOG.md
