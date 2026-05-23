# 🌳 Notion 산출물 자동 동기화 — 회원 셋업 가이드

> Core Campus 산출물 → Notion 데이터베이스 자동 sync
> 모바일 Notion 앱에서 어디서나 검색·필터·확인

---

## 📋 셋업 5단계 (5~10분)

### 1단계 — Notion Integration 만들기

1. https://www.notion.so/my-integrations 접속 (Notion 계정 로그인)
2. 우측 상단 **`+ New integration`** 클릭
3. 이름: `Core Campus`
4. Associated workspace: 본인 워크스페이스 선택
5. Type: `Internal` (기본값 유지)
6. **`Submit`** 클릭
7. 다음 화면에서 **`Internal Integration Token`** 복사 (`secret_xxx...` 형태)
   - ⚠️ 한 번만 표시됨. 바로 복사해서 어딘가에 임시 저장

---

### 2단계 — Notion에 부모 페이지 만들기

1. Notion에서 새 페이지 생성 (이름 자유 — 예: `Core Campus`)
2. 페이지 우측 상단 **`⋯`** 메뉴 클릭
3. **`Add connections`** → 방금 만든 `Core Campus` Integration 선택
4. 확인 다이얼로그 `Confirm` 클릭

---

### 3단계 — Parent Page ID 추출

페이지 URL 구조:
```
https://www.notion.so/Core-Campus-abc123def456789...
                                ^^^^^^^^^^^^^^^^^^^^^^^
                                마지막 32자 (하이픈 제거)
```

URL 끝의 32자를 복사. 하이픈 있으면 제거.

예시:
- URL: `https://www.notion.so/Core-Campus-a1b2c3d4e5f6789012345678901234ab`
- ID: `a1b2c3d4e5f6789012345678901234ab` (32자)

---

### 4단계 — .env 파일에 추가

[.env 파일 열기](computer:///Users/seohyeongmin/Desktop/강의%20홈페이지%20제작/.env)

아래 2줄 추가:
```bash
NOTION_TOKEN=secret_여기에_1단계_토큰
NOTION_PARENT_PAGE_ID=여기에_3단계_32자ID
```

저장.

---

### 5단계 — 더블클릭 실행

[notion-sync.command 더블클릭](computer:///Users/seohyeongmin/Desktop/강의%20홈페이지%20제작/notion-sync.command)

→ 첫 실행:
1. 부모 페이지 안에 **🌳 Core Campus — 산출물 인박스** 데이터베이스 자동 생성
2. content/approved + content/pending 모든 산출물을 Notion 페이지로 sync
3. 완료 후 안내

→ 두 번째 실행부터:
- 새 산출물만 추가 (idempotent)
- 기존 페이지는 status 변경 시 update

---

## 📱 모바일에서 사용하기

1. Notion 모바일 앱 열기
2. 부모 페이지(`Core Campus`) 탭
3. 안에 있는 **🌳 Core Campus — 산출물 인박스** 데이터베이스 탭
4. 어디서나 검색·필터·정렬 가능

---

## 🎨 데이터베이스 자동 생성되는 Properties

| Property | 타입 | 용도 |
|---|---|---|
| **Title** | 제목 | 산출물 제목 |
| **Agent** | Select | 🎩 CEO · 📚 curriculum · 🎬 producer · 📣 marketing · 🎓 success · 🛠 site_developer · 🎨 ui_designer · 📝 blog_publisher |
| **Kind** | Select | curriculum_outline · lecture_script · landing_copy · faq · cx_resolution · blog_post · design_variants · site_config_change · daily_report |
| **Status** | Select | pending · approved · rejected |
| **Self Review** | Select | pass · warn · fail |
| **Course ID** | Text | 코스 식별자 |
| **Summary** | Text | 한 줄 요약 (120자) |
| **DRI** | Text | 책임자 (새 SYSTEM에서 명시) |
| **HARD** | Number | HARD ban 위반 횟수 |
| **SOFT** | Number | SOFT ban 위반 횟수 |
| **Created at** | Date | 생성 시각 |
| **Result ID** | Text | 외부 ID (중복 방지) |

---

## 🔍 Notion에서 활용할 수 있는 View 예시

### 1. 칸반 보드 (Status 그룹화)
- 컬럼: pending · approved · rejected
- 한눈에 검토 대기 현황 파악

### 2. 에이전트별 (Agent 그룹화)
- 각 에이전트가 만든 산출물 분리
- 누가 가장 활발한지 시각화

### 3. 이번 주 (Created at 필터 — 지난 7일)
- 한 주간 산출물 흐름

### 4. 검수 필요 (Self Review = warn or fail)
- HARD·SOFT 위반 있는 산출물만

### 5. DRI별 (DRI 그룹화)
- 책임자 명확화

---

## 🔄 자동화 옵션 (선택)

### 옵션 A — 수동 (기본, 권장 시작)
- `notion-sync.command` 더블클릭할 때만 sync
- 회원님이 원할 때만 실행
- 가장 안전, 통제 쉬움

### 옵션 B — 주기적 자동 (cron, 매 30분)
```bash
# crontab -e 에 추가
*/30 * * * * cd "/Users/seohyeongmin/Desktop/강의 홈페이지 제작" && python3 scripts/notion_sync.py >> ~/Library/Logs/notion-sync.log 2>&1
```

### 옵션 C — 실시간 자동 (산출물 생성 직후 hook)
- `agents/conductor.py` 또는 `telegram_bot/poll.py` 에 hook 추가
- 산출물 1건 생성 → 즉시 Notion sync
- 가장 정밀, but 코드 수정 필요

→ 옵션 A로 시작 → 사용 습관 잡히면 B → 안정화되면 C 권고

---

## 🚨 트러블슈팅

### ❌ "NOTION_TOKEN 미설정"
- `.env` 파일에 `NOTION_TOKEN=secret_...` 추가했는지 확인
- secret_ 접두사 빠뜨리지 않았는지 확인

### ❌ "401 Unauthorized"
- Notion Integration이 페이지에 연결됐는지 확인
- 페이지 우측 상단 ⋯ → Connections → Core Campus 있는지

### ❌ "404 page not found"
- `NOTION_PARENT_PAGE_ID` 32자가 맞는지 확인
- 하이픈 제거했는지 확인

### ❌ DB가 만들어졌는데 산출물이 안 보임
- `content/state/notion_database_id.txt` 파일 삭제
- 다시 더블클릭 → 새 DB 생성

---

## 💡 추가 팁

### 알림 받기
Notion 모바일 앱 설정 → Notifications → 부모 페이지 알림 켜기
→ 새 산출물 추가될 때마다 Notion 푸시 알림

### Notion 위젯 (모바일 홈 화면)
iOS/Android Notion 앱 → 위젯 추가 → 'Core Campus 산출물' 페이지 선택
→ 홈 화면에서 직접 한눈에 확인

### 백업
Notion 페이지 우측 상단 ⋯ → Export → Markdown & CSV
→ 매월 1회 백업 권장 (혹시 원본 데이터 손실 대비)

---

> 🌳 작업하시면서 막히는 부분 있으면 알려주세요. 셋업·동기화 둘 다 도와드립니다.
