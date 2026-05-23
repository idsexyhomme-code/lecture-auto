# site_builder v2 통합 전략

> 데몬 안전 우선. 점진적 마이그레이션. 회원 ✅ 후 단계별 진행.

## 현재 site_builder 구조

`site_builder/build.py`가 빌드마다:
1. `site/index.html` 재생성 — site_config + Jinja2 템플릿
2. `site/courses/*.html` 재생성 — 각 코스별 템플릿
3. CSS·JS 캐시 무효화 (`?v={timestamp}`)

→ swap 즉시 덮어쓰기

## 통합 전략 — 3단계 점진

### Phase 1 — site_config 호환 레이어 (즉시, 위험 0)
`site/styles.css` 상단에 design-system 변수 별칭:
```css
:root {
  --accent: var(--color-coral, #D85A30);
  --bg: var(--color-bg, #F5EFE0);
  --fg: var(--color-ink, #1F1F1F);
  --muted: var(--color-text-muted, #6B6B6B);
  --surface: var(--color-bg-card, #FFFFFF);
  --line: var(--color-border, #E5DFD3);
}
```

또한 `_layout.html` 같은 Jinja 템플릿 head에 design-system import 추가:
```html
{% if site_config.design_system_version == "v2" %}
<link rel="stylesheet" href="/design-system/base.css">
<link rel="stylesheet" href="/design-system/components.css">
{% endif %}
<link rel="stylesheet" href="/site/styles.css?v={{ _build_time }}">
```

회원이 `site_config.json`에 `"design_system_version": "v2"` 추가하면 자동 적용.

### Phase 2 — 코스 빌드 v2 템플릿 (1~2일, 데몬 영향 중)
`site_builder/build.py` 의 코스 빌드 로직을:
```python
template_name = "course_v1.html"
if site_config.get("design_system_version") == "v2":
    template_name = "course_v2.html"
template = env.get_template(template_name)
```

`design-system/templates/course_v2.html` 기반 — 이미 작성됨.

### Phase 3 — index.html v2 빌드 (큰 작업, 1주)
메인 페이지 v2 시안을 site_builder가 출력하도록.
- `index_v2.html` 템플릿 추가
- site_config_change 플래그로 전환

### Phase 4 — 일괄 적용 (모든 페이지 v2 — 결재 완료 후)

## 즉시 가능 변경 (CEO 자율 — 위험 0)

`site/styles.css` 상단에 호환 레이어 추가만:

```css
/* DSv2 호환 레이어 — design-system 변수 별칭 */
:root {
  --accent: var(--color-coral, #D85A30);
  --bg: var(--color-bg, #F5EFE0);
  --fg: var(--color-ink, #1F1F1F);
  --muted: var(--color-text-muted, #6B6B6B);
  --surface: var(--color-bg-card, #FFFFFF);
  --line: var(--color-border, #E5DFD3);
  --radius-card: var(--r-lg, 16px);
  --shadow-md: 0 6px 18px rgba(31, 31, 31, 0.08);
  --shadow-lg: 0 14px 36px rgba(31, 31, 31, 0.10);
  --shadow-sm: 0 2px 6px rgba(31, 31, 31, 0.06);
  --font-family-sans: 'Pretendard Variable', Pretendard, -apple-system, 'Apple SD Gothic Neo', sans-serif;
}
```

이렇게 하면 기존 페이지 컬러 톤이 design-system v1.1과 동기화됨. **데몬 영향 0**.

## 회원 결재 안건

| 작업 | 결재 필요? | 영향 |
|---|---|---|
| Phase 1 호환 레이어 | ✗ CEO 자율 | 컬러만 동기화, 기능 변경 X |
| Phase 2 코스 v2 빌드 | ✅ 회원 결재 | 데몬 영향 있음 |
| Phase 3 index v2 빌드 | ✅ 회원 결재 (§6) | 메인 변경 |
| Phase 4 일괄 적용 | ✅ 회원 결재 | 전체 사이트 톤 통일 |

## 데몬 재시작이 필요할 때

대부분의 변경은 데몬 재시작 불필요 (코드 동적 로드). 단:
- `site_builder/build.py` 시그너처 변경 (다음 빌드부터)
- `agents/*.py` import 추가 (다음 cycle부터)

진짜 재시작이 필요한 경우:
```bash
# 데몬 정지
launchctl unload ~/Library/LaunchAgents/com.corecampus.longpoll.plist

# 5초 대기

# 데몬 재기동
launchctl load ~/Library/LaunchAgents/com.corecampus.longpoll.plist
```
