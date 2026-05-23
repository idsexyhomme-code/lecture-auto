# SEO Audit — 2026-05-16

## 페이지별 SEO 메타 점수

| 페이지 | title | description | og:title | og:description | og:image | twitter | 점수 |
|---|---|---|---|---|---|---|---|
| `site/index.html` | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | 2/6 |
| `site/courses/claude-launchpad.html` | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | 2/6 |
| `site/landing/core-compass/v3/index.html` | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | 5/6 |
| `site/_design_previews/course-launchpad-v2/index.html` (시안) | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | 2/6 |

## 발견 사항

### 1. og: 메타 거의 누락
- 메인·코스 페이지에 Open Graph 태그 없음
- 카카오톡·페이스북·디스코드 공유 시 미리보기 깨짐
- **영향**: 공유 시 클릭률 30~50% 손실 (업계 평균)

### 2. twitter:card 전무
- twitter:card, twitter:title, twitter:description 등 누락

### 3. canonical 일부 누락
- 페이지 redirect용 canonical은 일부 있음
- HTTPS canonical 통일 필요

### 4. sitemap.xml·robots.txt
- 미확인 — 점검 필요

## 권장 조치 (CEO 자율 영역)

### Phase 1 — Core Compass 신규 페이지 (이미 처리)
- v3/index.html — og:* 다 있음 ✓
- v3/result.html — `noindex,nofollow` (개인 URL) ✓
- v3/og.svg — 소셜 공유용 ✓ (PNG 변환은 별도)

### Phase 2 — 기존 코스 페이지 일괄 (CEO 자율 가능)
- 19개 코스 페이지에 og:title, og:description, og:type, og:image 자동 추가
- 자동화 스크립트로 메타 추가 — `agents/site_developer.py` 확장
- **현재 상태**: 자동 적용 가능 (page title·description 이미 있음 → og:로 그대로 복사)

### Phase 3 — 메인 페이지 (§6 큰 결재 — 회원 ✅ 필수)
- index.html 메타 조정·OG 이미지 제작은 회원 결재

### Phase 4 — sitemap.xml 자동 생성
- agents/site_developer.py가 빌드 시 sitemap.xml 자동 생성
- robots.txt 검증
