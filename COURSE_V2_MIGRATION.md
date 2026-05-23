# 코스 페이지 v1 → v2 마이그레이션 가이드

## 현 상태 (2026-05-16)

| 위치 | 페이지 | 상태 |
|---|---|---|
| `site/courses/*.html` | 20개 v1 (기존 styles.css) | 운영 중 — 그대로 |
| `site/design-previews/courses-v2/*.html` | 20개 v2 시안 (design-system v1.1) | 시안 — 회원 ✅ 대기 |

## 회원 ✅ 받은 후 마이그레이션 절차

### 옵션 A — 점진적 (코스별 1개씩)
1회 코스를 v2로 swap → 1주 KPI 관찰 → OK면 다음.

```bash
# 1개 코스 swap (예: claude-launchpad)
cp site/design-previews/courses-v2/claude-launchpad.html site/courses/claude-launchpad.html
```

### 옵션 B — 일괄 (모두 한 번에)
20개 코스 동시 swap.

```bash
# 자동 일괄 적용
cd "강의 홈페이지 제작"
for f in site/design-previews/courses-v2/*.html; do
  basename=$(basename "$f")
  if [ -f "site/courses/$basename" ]; then
    cp "$f" "site/courses/$basename"
    echo "✓ swap: $basename"
  fi
done
```

### 옵션 C — 별도 경로로 신규 운영
`site/courses-v2/` 로 신규 경로 만들고, 메인 페이지의 코스 링크만 변경. 기존 v1 백업.

## 차이점 요약

| 항목 | v1 (기존) | v2 (신규) |
|---|---|---|
| 컬러 시스템 | `styles.css` (--accent, --bg, --fg) | `design-system/base.css` (--color-coral, --color-bg, --color-ink) |
| 폰트 | system-ui | Pretendard Variable + Gotham + GmarketSans |
| Hero | course-hero 단순 | course-hero + meta-chips + 2단 카피 (회원 톤) |
| Pricing | 페이지 하단 cta-bottom | 별도 final-cta 워밍블루 박스 |
| FAQ | (대부분 없음) | Q. 빨간 prefix + 3~5개 기본 셋 |
| 카드 라운드 | 12~16px | 16~20px |
| 한글 자간 | 0 | -0.015 ~ -0.028em |
| 한글 행간 | 1.55 | 1.65~1.75 |
| 모바일 sticky CTA | ✗ | ✓ |

## 회원 결정 안건

회원님이 결정하실 사항:

1. **마이그레이션 방식**: 옵션 A (점진) / 옵션 B (일괄) / 옵션 C (별도 경로)
2. **첫 swap 코스**: 어느 코스를 1번 적용으로 KPI 관찰할지 (옵션 A 선택 시)
3. **타이밍**: 즉시 / 1주 뒤 / Core Compass 출시 후

## 자동 백업

mig 진행 전 자동 백업:
```bash
mkdir -p site/courses-backup-v1-$(date +%Y%m%d)
cp site/courses/*.html site/courses-backup-v1-$(date +%Y%m%d)/
```
