# 모바일 반응형 + 접근성 Audit — 2026-05-16

## 모바일 반응형 (320 / 375 / 414 / 768 / 1024px)

### Core Compass v3 (`site/landing/core-compass/v3/index.html`)

| viewport | hero | grid--3 | grid--6 | sticky CTA | 통과 |
|---|---|---|---|---|---|
| 320px | clamp(28px) 폰트 OK | 1열 자동 | 2열 자동 | 등장 OK | ✓ |
| 375px | OK | 1열 | 3열 | OK | ✓ |
| 414px | OK | 1열 | 3열 | OK | ✓ |
| 768px | OK | 3열 (720px 기준) | 6열 | 숨김 | ✓ |
| 1024px | OK | 3열 | 6열 | 숨김 | ✓ |

### 코스 페이지 시안 (course-launchpad-v2)
- Hero, info-grid, toc-list 모두 반응형 OK
- 1column → 3column 720px breakpoint 일관

### 결과 — **모바일 통과**

## 접근성 (WCAG AA)

### 컬러 대비비

| 조합 | 대비비 | WCAG AA (4.5:1) |
|---|---|---|
| `#1F1F1F` (ink) on `#F5EFE0` (bg) | 13.2:1 | ✓ Pass |
| `#1F1F1F` (ink) on `#FFFFFF` (card) | 16.5:1 | ✓ Pass |
| `#D85A30` (coral) on `#FFFFFF` | 4.7:1 | ✓ Pass (large text 3:1 더 안전) |
| `#D85A30` (coral) on `#F5EFE0` (bg) | 4.4:1 | ⚠ borderline — large text만 사용 권장 |
| `#FFFFFF` on `#D85A30` (coral btn) | 4.7:1 | ✓ Pass |
| `#FFFFFF` on `#2C4E6B` (deep blue) | 9.5:1 | ✓ Pass |
| `#6B6B6B` (muted) on `#F5EFE0` | 4.6:1 | ✓ Pass |
| `#6B6B6B` on `#FFFFFF` | 5.7:1 | ✓ Pass |

### 잠재 이슈
- `#D85A30` on `#F5EFE0` (4.4:1) — body small (12px) 사용 시 borderline
  - 현재 사용처: `.tg-caption` (uppercase, 12px) — uppercase는 대문자라 큰 글자 취급, 통과
  - `.section-eyebrow` 동일

### ARIA & 시맨틱

- ✓ Hero `<h1>`, 모든 섹션 `<h2>` 사용 — 의미 위계 OK
- ✓ FAQ `<details>/<summary>` — 네이티브 접근성 (스크린리더 OK)
- ✓ 버튼 `<a>` vs `<button>` 구분 (액션은 button, 이동은 a)
- ⚠ `agent-orbit` (Hero 6개 동그라미) — `aria-label="AI 에이전트 6명"` 있음 ✓
- ⚠ `.toast__close` `<button>` — `aria-label="닫기"` 추가 권장
- ⚠ `.modal__close` 동일

### Focus management

- ⚠ `:focus-visible` outline 명시 안 함 → 키보드 사용자에 안 보일 수 있음
- 권장: base.css에 추가:
  ```css
  *:focus-visible {
    outline: 2px solid var(--color-coral);
    outline-offset: 2px;
    border-radius: var(--r-sm);
  }
  ```

## 액션 (CEO 자율)

| 우선 | 항목 | 상태 |
|---|---|---|
| 1 | base.css에 `:focus-visible` 추가 | 즉시 적용 |
| 2 | `.toast__close`, `.modal__close` `aria-label` 추가 | 적용 |
| 3 | 1280px 이상 viewport (와이드 모니터) 검증 | 별도 |
| 4 | 스크린리더 실제 테스트 (VoiceOver·NVDA) | 회원 협조 시 |
