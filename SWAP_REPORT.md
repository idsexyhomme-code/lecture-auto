# Swap 결과 보고서 — 2026-05-17

## 발견 — site_builder 자동 재생성 보호

CEO 데몬 24/7 가동 중이고, `site_builder/build.py`가 빌드마다 자동으로:
- `site/index.html` 재생성
- `site/courses/*.html` 재생성

→ swap 즉시 덮어쓰기 됨. **데몬 안전 우선 — 별도 경로 운영 채택**.

## 운영 URL 구조

| 경로 | 상태 | 내용 |
|---|---|---|
| `site/index.html` | 라이브 v1 | site_builder 자동 빌드, 변경 안 됨 |
| `site/courses/*.html` | 라이브 v1 | 동일 |
| **`site/v2/index.html`** | **v2 시안 라이브** | 메인 v2 (수동) |
| **`site/courses-v2/*.html`** | **v2 시안 라이브** | 20개 코스 v2 (수동) |
| `site/landing/core-compass/v3/` | 신규 라이브 | Core Compass v3 (site_builder 영향 X) |
| `site/_backups/v1-20260517/` | 백업 | swap 전 v1 보존 |

## 회원 결정 안건 — 다음 단계 (3가지 선택)

### 옵션 1 — 그대로 운영 (단기 — 출시 검증)
- `corecampus.kr/` → v1 그대로 (변화 없음)
- `corecampus.kr/v2/` → v2 시안 접근 가능 (개발용)
- KPI 비교 후 v2 채택 결정
- **위험 0, 검증 가능**

### 옵션 2 — site_builder 변경 (중기 — 1주 작업)
- `site_builder/build.py`를 design-system v1.1 사용하도록 수정
- index.html 빌드 시 v2 시안 그대로 출력
- 코스 빌드 시 v2 템플릿 사용
- 빌드 후 자동으로 v2가 라이브 됨
- **데몬 영향 큼. 신중 진행 필요**

### 옵션 3 — 강제 swap + 데몬 비활성화 (단기 — 위험)
- 데몬 launchctl unload
- 메인·코스 v1 → v2 강제 swap
- 데몬 영구 비활성화 또는 v2 친화로 수정 후 재기동
- **자가 학습·자동 발행 모두 중단 위험**

## 권장 — 옵션 1

**이유:**
- v2 검증 시간 확보 (1주~2주)
- 출시 효과 KPI 비교 가능 (v1 vs v2)
- 데몬 자동 운영 유지 (블로그 발행·코스 자동화)
- 위험 0

**진행 방식:**
1. 회원이 미리보기 .command로 v2 점검
2. 1주 후 옵션 2로 site_builder 변경 진행 결정
3. 그 사이 Core Compass 출시 진행 (영향 받지 않음)

## v2 미리보기 — 더블클릭

[preview-courses-v2.command](computer:///Users/seohyeongmin/Desktop/강의 홈페이지 제작/preview-courses-v2.command) → `http://localhost:7922/site/v2/`

직접 접근:
- 메인 v2: file:///Users/seohyeongmin/Desktop/강의 홈페이지 제작/site/v2/index.html
- 코스 v2: file:///Users/seohyeongmin/Desktop/강의 홈페이지 제작/site/courses-v2/claude-launchpad.html
