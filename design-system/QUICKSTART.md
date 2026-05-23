# Core Campus Design System — QUICKSTART

> 새 페이지를 5분 안에 디자인 시스템에 맞춰 만드는 가이드.

## 1. 최소 셋업 — 3줄

```html
<link rel="stylesheet" href="/design-system/base.css">
<link rel="stylesheet" href="/design-system/components.css">
<!-- (선택) 최우선 폰트 preload -->
<link rel="preload" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/packages/pretendard/dist/web/variable/woff2/PretendardVariable.woff2" as="font" type="font/woff2" crossorigin>
```

## 2. Hero 섹션 — 그대로 복붙

```html
<section class="hero">
  <div class="container">
    <div class="hero__badge"><span class="badge">한정 100명</span></div>
    <h1 class="hero__title">
      <span class="section-title-2line__small">작은 카피</span>
      큰 카피 <span class="text-coral">강조</span>
    </h1>
    <p class="hero__sub">설명 문장</p>
    <a class="btn btn--primary btn--lg" href="#pricing">CTA</a>
  </div>
</section>
```

## 3. 카드 그리드

```html
<div class="grid grid--3">
  <div class="card card--feature">
    <div class="card__index">01</div>
    <h3 class="card__title">제목</h3>
    <p class="card__body">설명</p>
  </div>
  <!-- 2~3개 더 -->
</div>
```

## 4. FAQ (회원 톤 — Q. 빨간 prefix)

```html
<details class="faq">
  <summary><span><span class="faq__q-label">Q.</span> 질문?</span></summary>
  <div class="faq__body">답</div>
</details>
```

## 5. 최종 CTA (워밍블루 박스)

```html
<div class="final-cta">
  <h2 class="final-cta__title">지금 시작.</h2>
  <p class="final-cta__sub">한정 100명 · 9,900원</p>
  <a class="btn btn--primary btn--lg" href="#">결제하고 받기</a>
</div>
```

## 6. 사용 가능 컴포넌트 (전체 목록)

- `.btn` + 변형 (`--primary`, `--secondary`, `--ghost`, `--lg`, `--block`)
- `.badge` + `.badge--blue`
- `.card` + `.card--feature`, `.card__index`, `.card__title`, `.card__body`
- `.bullet-card`
- `.step-dot` + `.step-dot__num`, `.step-dot__label`
- `.report` + `.report__section`, `.report__section--locked`
- `.pricing` + `.pricing__ribbon`, `.pricing__price`, `.pricing__features`
- `.faq` + `.faq__q-label`, `.faq__body`
- `.hero` + `.hero__badge`, `.hero__title`, `.hero__sub`, `.hero__trust`
- `.final-cta` + `.final-cta__title`, `.final-cta__sub`, `.final-cta__fineprint`
- `.site-header`, `.site-footer`
- `.toast` + `--success/--warning/--danger/--info`
- `.modal-backdrop` + `.modal` + `.modal__title`, `.modal__body`, `.modal__actions`
- `.tooltip` (`data-tooltip="..."`)

## 7. CSS 변수 (10초 안에 외울 만한 것만)

```css
/* Color */
var(--color-coral)        /* #D85A30 — 1차 CTA */
var(--color-deep-blue)    /* #2C4E6B — 최종 CTA */
var(--color-bg)           /* #F5EFE0 — 베이지 본 배경 */
var(--color-ink)          /* #1F1F1F — 본문 */
var(--color-text-muted)   /* #6B6B6B — 보조 */
var(--color-border)       /* #E5DFD3 — 카드 보더 */

/* Spacing — 8-step */
var(--sp-2) /* 8px */
var(--sp-4) /* 16px */
var(--sp-6) /* 24px */
var(--sp-8) /* 32px */
var(--sp-12) /* 48px */
var(--sp-16) /* 64px */

/* Radius */
var(--r-md) /* 10px — 버튼 */
var(--r-lg) /* 16px — 카드 */
var(--r-xl) /* 24px — pricing */
var(--r-full) /* 알약 */

/* Font */
var(--font-sans-kr)    /* Pretendard Variable */
var(--font-impact-kr)  /* GmarketSans — H1 임팩트만 */
var(--font-sans-en)    /* Gotham — 숫자·라벨 */
```

## 8. 절대 하지 말 것

- ❌ 하드코딩 컬러 `#FF6600` (반드시 CSS 변수)
- ❌ `font-family: Roboto` (한글 자형 어색)
- ❌ `letter-spacing: 0` (한글은 음수)
- ❌ `line-height: 1.4` (한글 본문은 1.55+)
- ❌ 그라데이션 헤드라인 (회원 톤 아님)
- ❌ "월 1000만원 보장 / 운명대로 / 100% 맞는" (자동 차단됨)

## 9. 색감·톤 인터뷰

> "**잠깐 — 이게 회원님 색깔인가?**" 자문하세요.
>
> 베이지 + 코랄 + 딥블루는 회원님 감귤박람회·몽생이 어린이집 작업과 같은 톤이에요.
> 추가 컬러를 쓰고 싶다면, `design-system/tokens.json` 확장 제안 → 회원 ✅.

## 10. 검증 (페이지 만들고 마지막 단계)

```bash
# 카피 ban 검사
python3 -c "
import re
html = open('your-page.html').read()
text = re.sub(r'<style.*?</style>', '', html, flags=re.S)
text = re.sub(r'<script.*?</script>', '', text, flags=re.S)
text = re.sub(r'<[^>]+>', ' ', text)
HARD = ['무조건', '100% 보장', '운명대로', '잠자면서', '월 1,000만']
for p in HARD:
    if p in text: print('✗ HARD:', p)
"
```

또는 `agents/sub_agents.py` 의 `DesignQaAgent` 가 자동 검증.
