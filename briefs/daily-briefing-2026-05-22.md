# 📋 2026-05-22 (금) 아침 브리핑

> Core Compass **출시 D-2** (예정일 2026-05-24).
> 회원이 직접 처리해야 하는 결제·이메일·도메인 인프라가 아직 미완.

## 어제의 업데이트 (2026-05-21)

### 🎯 코어 캠퍼스 (Core Campus)
- CEO 일일 보고 정상 실행됨 (`briefs/_processed/ceo-daily-2026-05-21-*.json`).
- approved 누적 467건, pending 7건 (오늘 21:27 기준 475 / 5 로 8건 승인·2건 처리됨).
- courses 23개·posts 248개로 5/20부터 변동 없음 — 콘텐츠 신규 증분은 멈춤.

### 🎬 블로그 자동발행 인프라 (가장 큰 어제 작업)
- **새벽 3시 자동 발행 데몬 구축 완료**: `install-daily-publish-daemon.command` + `com.corecampus.daily-tistory-publish.plist` + `scripts/daily-tistory-publish.sh`.
- `blog-status.command` — 데몬 / 큐 / 검수대기 / 최근 승인 한 화면.
- `bulk-publish-approved-blogs.command` — 승인된 미발행 blog_post 일괄 처리.
- `run-blog-publish-now.command` — 즉시 발행(데몬 우회).
- 블로그 발주 3건 처리됨: `claude-bizflow`, `claude-content-engine`, `claude-launchpad` (briefs/_processed로 이동, site/blog-drafts/*/post.html 생성).
- ⚠️ 다만 KPI상 `blog_published_today: 0`·`last_blog_publish: 2026-05-05` — 데몬은 설치됐으나 **실제 티스토리 발행은 아직 0건**. 데몬 첫 가동(3시) 또는 수동 트리거 확인 필요.

### 🖼 이미지·LLM
- `agents/image_gen.py` 수정 + `test-blog-image-hq.command` 추가 (블로그 이미지 HQ 테스트).
- `list-gemini-models.command` 갱신.

### 📄 기타 문서 (5/20 작성, 5/21에는 .md 신규 없음)
- `PAYMENT_LAUNCH_TOSS.md` — 토스페이먼츠 가입 가이드 (D-day까지 1주 가이드).
- `PHASE_1_REAL_PAGE_PIPELINE.md` — 산출물 승인 → site/ 자동 갱신 파이프라인.
- `FASTCAMPUS_PATTERN.md` — Fast Campus 메인 패턴 분석 (캐러셀·TOP5·카피).
- `CLAUDE.md` — 프로젝트 메타 갱신.

## 오늘 해야 할 일

1. **[D-2 🔥]** 토스페이먼츠 가입 시작 — 사업자등록증·통장사본·신분증 준비, `https://www.tosspayments.com/` (회원 직접) — `PAYMENT_LAUNCH_TOSS.md` 참고.
2. **[D-2 🔥]** Resend(또는 Mailgun) 가입 + 도메인 DKIM·SPF DNS 등록, `.env`에 `RESEND_API_KEY` 입력.
3. **[D-2 🔥]** `corecampus.kr` 도메인 DNS·HTTPS 인증서 상태 점검 + `webhook/payapp` 엔드포인트 호스팅 결정 (Vercel Serverless 권장).
4. **[검증]** 블로그 발행 데몬 실제 동작 확인 — `blog-status.command` 더블클릭 → 가동중·큐·최근발행 확인. `last_blog_publish`가 5/5 그대로면 `run-blog-publish-now.command`로 1건 수동 발행 테스트.
5. **[검수]** `content/pending/` 5건 처리:
   - `ceo_dispatch` (pilot_01 5개 티켓) — 승인/반려 결정.
   - `ceo_daily_report` × 2 (5/18) — 중복 정리.
   - `site_config_change` × 2 (Tier 2) — 메인 페이지 카피 변경 동반 가능성 → 헌법 §6 회원 ✅ 필수.
6. **[결정]** REPORT_30_STEPS_v8 회원 안건 검토:
   - 출시일 5/24 확정 여부
   - Supabase 회원 시스템 도입 시점 (출시 2주 후 권장)
   - 후속 상품(코칭 49,000원·Deep·그룹) 출시 일정
   - 다음 30단계 진행 또는 정지.
7. **[정책]** `site/terms.html` / `site/privacy.html` 작성 — 출시 전 필수 (LAUNCH_CHECKLIST §7).
8. **[마케팅]** 100명 한정 카운터·첫 100명 모집 채널(SNS·블로그·카톡·이메일) 명단 확정.

## ⚠️ 주의 / 마감
- **D-2 5/24 출시** — 결제·이메일·도메인 3종은 회원이 직접 처리해야 하며 토스 심사가 1~3 영업일이라 오늘 시작하지 않으면 출시일이 밀립니다.
- **`blog_published_today: 0` & `last_blog_publish: 2026-05-05`** — 어제 만든 데몬·일괄발행 스크립트가 실제로 티스토리에 송출됐는지 검증 안 됨. 오늘 1건이라도 발행돼야 데몬 정상 판정.
- **courses 23 / posts 248 — 5/20부터 정체** — 콘텐츠 파이프라인이 멈춰 있는 상태. roadmap_pump·conductor 동작 확인 필요.
- **`content/state/checkpoint.json`**: 21:48 heartbeat (오늘 자정 전) — long_poll은 살아 있음.

## 📊 어제→오늘 KPI

| 항목 | 5/21 | 5/22 | 변화 |
|---|---|---|---|
| approved | 467 | 475 | +8 |
| pending | 7 | 5 | -2 |
| courses | 23 | 23 | — |
| posts | 248 | 248 | — |
| blog_published_today | 0 | 0 | — |
| payment_today | 0 | 0 | — |
