# 블로그 글 템플릿 점검 — 2026-05-16

## 현재 (`site/blog-drafts/v2_human_tone/*.html`)

- 인라인 `<style>` 사용 (Tistory가 외부 CSS 못 부르므로 OK)
- 컬러: `#222` 텍스트 / `#fff8e7` 안내 박스 / `#5b3924` 링크 — **갈색 톤** (design-system과 다름)
- max-width 680px
- system-ui + Apple SD Gothic Neo + sans-serif
- 글 구조: H1 → Hero img → H2 시작 → 단락 → 코스 링크

## 디자인 시스템과의 차이

| 항목 | 현재 블로그 | design-system v1.1 |
|---|---|---|
| 본문 텍스트 | `#222` | `#1F1F1F` (`--color-ink`) |
| 강조 컬러 | `#5b3924` (브라운) | `#D85A30` (코랄) |
| 배경 | 화이트 | `#F5EFE0` (베이지) |
| 폰트 | system-ui | Pretendard Variable |
| 안내 박스 | `#fff8e7` | `--color-coral-soft` (#FBE6DE) |

## 결정

**현 시점에서 변경 보류** (낮은 우선순위). 이유:
1. **Tistory가 외부 폰트·CSS 대부분 막음** → Pretendard 적용 어려움
2. **system-ui가 안전**한 선택 (모든 OS에서 잘 보임)
3. **컬러만 조정**하면 디자인 시스템과 시각적 일관성 확보 가능

## 권장 조치 (CEO 자율 — 다음 발행분부터)

`agents/blog_publisher.py` 또는 템플릿 생성 부분에 다음 컬러만 교체:
- `#222` → `#1F1F1F`
- `#5b3924` → `#D85A30`
- `#fff8e7` → `#FBE6DE`

→ 기존 발행분 일괄 교체는 ❌ (Tistory 재발행 비용 큼)
→ 신규 발행분만 색 변경 → 그라데이션 같은 자연 정렬
