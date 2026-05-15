# Core Campus — 프로젝트 메타 파일

> Claude·새 에이전트가 이 프로젝트에 들어올 때 *가장 먼저 읽는* 파일.

## 회사 미션

Core Campus는 1인 사업가의 아이디어를 AI 기반 수익 시스템으로 바꾼다.

> 자세한 헌법은 `data/ceo_charter.md` 9개 조항 + §10 외부 전문가 소싱 정책.

## 팀 구성 (8명 + CEO)

| 에이전트 | 파일 | 역할 |
|---|---|---|
| 🎩 CEO | `agents/ceo.py` | 일일 보고·산출물 검토·분기 리뷰. 헌법 9조항 따름. |
| 📚 강의 기획자 | `agents/curriculum.py` | 코스 주제 → 6편 차시 구조. 80/20·Bloom·단일 학습목표. |
| 🎬 콘텐츠 제작자 | `agents/producer.py` | 차시 brief → 영상 스크립트 5단 구조 (Hook/Promise/Core/Exercise/CTA). |
| 📣 홍보·마케팅 | `agents/marketing.py` | 커리큘럼 → 랜딩 카피 (hero·problem·solution·FAQ·pricing). |
| 🎨 시니어 디자이너 | `agents/ui_designer.py` | 디자인 시안 v1·v2·v3 + image_prompts. |
| 🛠 사이트 개발자 | `agents/site_developer.py` | site_config.json 변경 → GitHub Actions 빌드. |
| 🎓 수강생 관리 | `agents/success.py` | FAQ 자동 생성·수강생 Q&A 답변 초안. |
| 📝 블로그 발행 | `agents/blog_publisher.py` | 코스 → 블로그 글 → Tistory 자동 발행. |

## 일일 워크플로우

```
09:00 KST — CEO 일일 보고 자동 트리거 (long_poll.py)
        ↓
roadmap_pump 1시간마다 새 코스 brief 자동 발주
        ↓
brief 큐 → conductor 또는 worker_pool (16 동시)
        ↓
self_review (F1) → CEO 게이트 (F2) → pending
        ↓
회원 ✅ → approved → site_builder/build → GitHub Pages
        ↓
blog_publisher → Tistory 발행
```

## 자율 vs 회원 승인 영역 (헌법 §5·§6)

**CEO 자율 (회원 ✅ 없이 진행)**
- 강의 제목·설명·SEO·태그
- 블로그 글 주제·초안 작성
- 커리큘럼 초안
- 랜딩 카피 초안
- 무료 자료 아이디어
- 콘텐츠 업로드 일정 제안

**회원 ✅ 필수 (헌법 §6)**
- 유료 상품 출시·가격 변경
- 정식 결제 도입
- 환불 정책 변경
- 외부 광고비 집행
- 메인 페이지 카피 변경
- 강의 카테고리 추가
- 외부 전문가 메시지 발송
- 계약 조건 확정

## 출력 파일 명명 규칙

- 산출물: `content/pending/{ts}-{hash6}.json`
- 승인 후: `content/approved/{ts}-{hash6}.json`
- 사이트: `site/courses/{course_id}.html` / `site/posts/{ts}-{hash}.html`
- 블로그 드래프트: `site/blog-drafts/v2_human_tone/{idx}_{course_id}.html`

## 자가 학습 루프 (F1~F5)

1. **F1** 산출물마다 self_review (HARD/SOFT ban) → meta 기록
2. **F2** 가드 대상 산출물엔 CEO 종합 의견
3. **F3** KPI·self_review 통계 누적 → `data/learning/copy_principles_v2.json`
4. **F4** A/B 테스트 (CC_AB_TEST=1) — 두 변형 비교
5. **F5** 임계값 초과 패턴 자동 banned_words 승격

## 환경변수 (.env)

| 키 | 용도 |
|---|---|
| ANTHROPIC_API_KEY | Claude API |
| GH_PAT | GitHub PAT (자동 push) |
| TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID | 알림·승인 |
| TISTORY_BLOG_NAME | 블로그 발행 대상 |
| CC_PARALLEL=1 | 병렬 모드 활성 |
| CC_WORKER_POOL_WORKERS=4 | 워커 수 |
| CC_WORKER_POOL_CONCURRENCY=4 | 동시 처리 수 |
| DAILY_BUDGET_USD | 일일 비용 한도 |
| DRY_RUN | true면 외부 발송 모두 mock |
| INSTAGRAM_ACCESS_TOKEN | Instagram Graph API |
| INSTAGRAM_BUSINESS_ACCOUNT_ID | IG 비즈니스 계정 |

## 모니터링

- 대시보드: `open-dashboard.command` 더블클릭 → http://localhost:7878
- 로그: `tail-daemon.command` 더블클릭 → `~/Library/Logs/corecampus-longpoll.log`
- 텔레그램: 실시간 산출물 카드 + 알림

## 사고 시 빠른 진단

| 증상 | 첫 확인 |
|---|---|
| 블로그 발행 실패 | `tistory_session.json` mtime / 세션 재캡처 |
| 데몬 멈춤 | `launchctl list \| grep corecampus` |
| 비용 폭주 | `content/state/daily_total.json` |
| 자가 학습 안 됨 | `data/learning/copy_principles_v2.json` |
| brief 적체 | 대시보드 큐잉 카운트 |
