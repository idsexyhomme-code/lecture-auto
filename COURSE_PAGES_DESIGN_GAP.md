# 코스 페이지 디자인 시스템 갭 분석

## 발견 — 사이트가 이미 자체 디자인 시스템 사용 중

기존 `site/styles.css`에 87개 CSS 변수 사용. 자체 토큰 시스템:

| 기존 | → | design-system/ (신규) |
|---|---|---|
| `--accent` | → | `--color-coral` |
| `--bg` | → | `--color-bg` |
| `--brand` | → | `--color-coral` |
| `--fg` | → | `--color-ink` |
| `--muted` | → | `--color-text-muted` |
| `--surface` | → | `--color-bg-card` |
| `--line` | → | `--color-border` |
| `--radius-card` | → | `--r-lg` |
| `--shadow-md/lg/sm` | → | `--shadow-md/lg/sm` (동일 명명) |
| `--font-family-sans` | → | `--font-sans-kr` |
| `--success`, `--danger` | → | `--color-success`, `--color-danger` (호환) |

**결론**: 기존 사이트가 깨지지 않고, design-system/은 신규 페이지 (Core Compass 등)에서 시작. 점진적으로 마이그레이션.

---

## 마이그레이션 전략 — 안전한 점진적 적용

### Phase A — 신규 페이지만 (즉시, CEO 자율)
- Core Compass v3 + result/success/expired/email/404 (이번 30단계에서 완성)
- 새 코스 발주 (예: 회원 ✅ 결재된 신규 코스 C)
- 새 블로그 글 템플릿

### Phase B — 기존 페이지 호환 레이어 (CEO 자율 가능 수준)
- `site/styles.css` 상단에 design-system 변수 별칭 추가:
  ```css
  /* 호환 레이어 — design-system 변수 ↔ 기존 변수 */
  :root {
    --accent: var(--color-coral, #D85A30);
    --bg: var(--color-bg, #F5EFE0);
    --fg: var(--color-ink, #1F1F1F);
    --muted: var(--color-text-muted, #6B6B6B);
    /* ...등등 */
  }
  ```
- 이렇게 하면 기존 페이지 컬러 토큰이 design-system과 동기화됨
- 단, 카피 변경은 §6 영역이므로 카피는 그대로 유지

### Phase C — 1~2개 코스 페이지 리디자인 시안 (회원 ✅ 필수)
- 1개 코스 골라 design-system v1.1로 풀 리디자인 시안 작성
- 회원님 보시고 ✅ → 19개 일괄 적용 진행 (자동화)

### Phase D — 메인 페이지 (큰 §6 결재)
- index.html 리디자인 시안
- Core Campus 전체 브랜딩 검토 후 진행

---

## 19개 코스 상태 (지금)

| 코스 슬러그 | 코스명 | 현재 페이지 위치 | 디자인 시스템 |
|---|---|---|---|
| claude-autowork | 반복 업무 시간 줄이기 실전 | courses/claude-autowork.html | 기존 styles.css |
| claude-bizflow | (미확인) | courses/claude-bizflow.html | 기존 |
| claude-content-engine | (미확인) | ... | 기존 |
| claude-customer-script | ... | ... | 기존 |
| claude-customer-support | ... | ... | 기존 |
| claude-daily-recap | ... | ... | 기존 |
| claude-intro-email | ... | ... | 기존 |
| claude-launchpad | ... | ... | 기존 |
| claude-mail-writing | ... | ... | 기존 |
| claude-meeting-notes | ... | ... | 기존 |
| claude-monthly-revenue | ... | ... | 기존 |
| claude-pricing-page | ... | ... | 기존 |
| claude-sop | ... | ... | 기존 |
| claude-sop-onboarding | ... | ... | 기존 |
| claude-youtube-plan | ... | ... | 기존 |
| deepwork-1hr | (베타) | ... | 기존 |
| deepwork-1hr-test | (테스트) | ... | 정리 후보 |
| core-campus-general | ... | ... | 기존 |
| core-campus-meta | ... | ... | 기존 |
| tax-basics-solopreneur | ... | ... | 기존 |

**총 19개 코스 + 1개 테스트** = 정리 후보 1개 (deepwork-1hr-test)

---

## 결론 — 회원 결정 필요

**Q1**: 기존 styles.css 위에 design-system 호환 레이어 추가 (Phase B) — CEO 자율?
- 권장: ✅ — 컬러만 동기화, 기능 변화 없음, 점진적 톤 일관성

**Q2**: 1개 코스 골라 리디자인 시안 작성 (Phase C)
- 권장: ✅ — 추천 코스는 `claude-launchpad` 또는 `tax-basics-solopreneur` (1인 사업 관련)

**Q3**: 메인 페이지 리디자인 (Phase D)
- 권장: 회원 ✅ 받은 후만 — Core Compass v3 출시 후 KPI 보고 판단
