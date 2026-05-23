# Phase 1 — 실 페이지 반영 파이프라인 (구축 완료)

> 회원 요청: "텍스트 산출물만 쌓이지 말고, 실제 홈페이지 UI/UX가 바뀌고 사용자가 보는 페이지 퀄리티가 좋아져야 한다."
> 회원 결정: 옵션 A 순서 — Phase 1 → 3 → 2 → 4.

---

## 무엇이 바뀌었나

### Before (이전)
```
산출물 승인 → content/approved/ 에 JSON 적재 → 끝
                                                ↑
                                       site/index.html 갱신 없음
                                       사용자가 보는 페이지 변동 없음
```

### After (이번 Phase 1 완료 후)
```
산출물 승인
    ↓
content/approved/ 적재
    ↓
[Phase 1.1] site_config_change·landing_copy·curriculum_outline·lecture_script·design_variants
    이면 즉시 site_builder/build.py 실행 → site/ 폴더 갱신
    ↓
[Phase 1.2] 시각 영향 큰 kind(site_config_change·design_variants)는
    Playwright로 메인 페이지 스크린샷 + 텔레그램 카드 전송
    Lighthouse 점수도 가능 (라이브 URL — npx 있을 때)
    ↓
long_poll 다음 사이클(~3분)에 자동 git add+commit+push
    ↓
GitHub Pages 자동 배포 (~1분 후 라이브 반영)
    ↓
회원이 텔레그램에서 [스냅샷 + 빌드 결과 + Lighthouse 점수] 한 카드로 확인
```

---

## 추가된 파일

### 1. `scripts/auto_build.py` — 빌드 자동 트리거
```python
should_trigger_build(kind)  # 빌드해야 하는 kind인지
run_build(timeout=120)       # site_builder/build.py 실행 + 결과 dict
format_telegram_card(result) # 텔레그램 카드 텍스트
should_trigger_snapshot(kind) # 스냅샷까지 필요한 시각 영향 큰 kind인지
trigger_snapshot_async(kind, title) # 스냅샷 + 텔레그램 전송
```

### 2. `scripts/site_snapshot.py` — 스크린샷·Lighthouse
```python
capture_pages(use_live=False, mobile=False)  # Playwright headless 캡처
lighthouse_score(url)                          # npx lighthouse 점수 측정
send_snapshot_to_telegram(snap, lh, label)    # 텔레그램 발송
capture_and_report(label, use_live, mobile_too)  # 원샷 헬퍼
```

CLI:
```bash
python3 scripts/site_snapshot.py            # 로컬 캡처
python3 scripts/site_snapshot.py --live     # 라이브 캡처 + Lighthouse
python3 scripts/site_snapshot.py --send     # 텔레그램 전송까지
python3 scripts/site_snapshot.py --mobile   # 모바일 뷰포트 추가
```

### 3. `telegram_bot/client.py` — send_photo·send_media_group 추가
- 단일 사진: `send_photo(path, caption=...)`
- 여러 사진(최대 10장): `send_media_group([paths], caption=...)`

### 4. `telegram_bot/poll.py` — approve handler hook 통합
승인 직후 흐름:
1. `site_config_change`면 `site_config.json` 덮어쓰기
2. `scripts.auto_build.should_trigger_build`에 해당하면 `run_build()` 실행
3. 빌드 성공 + 시각 영향 큰 kind면 `trigger_snapshot_async()` 호출
4. 텔레그램 카드에 빌드 + 스냅샷 결과 추가

### 5. `FASTCAMPUS_PATTERN.md` — Apify 분석 reference
- Fast Campus 메인 페이지 패턴 9개 분석
- Core Campus 적용 안 명시
- 헌법 §4 ban 체크리스트

### 6. `agents/site_developer.py` — reference 자동 주입
`_load_reference_docs()` 함수가 시작 시 FASTCAMPUS_PATTERN.md를
site_developer SYSTEM 프롬프트에 자동 컨텍스트로 추가.

### 7. `briefs/phase1-site-dev-fastcampus-ref-...json` — 첫 시안 brief
site_developer가 자동으로 픽업해 Phase 1 첫 시안 생성 시작.

### 8. `build-and-snapshot.command` — 수동 더블클릭 실행
회원이 언제든지 더블클릭으로:
1. site_builder/build.py 실행
2. 스크린샷 (desktop + mobile) 캡처
3. Lighthouse 점수 (npx 설치 시)
4. 텔레그램 일괄 전송

---

## 회원이 다음에 할 일

### 즉시 — 5분 안에 확인 가능
1. **데몬 가동 확인** — `launchctl list | grep corecampus` (이미 24/7 가동 중)
2. **briefs/ 큐 확인** — 다음 데몬 사이클에 site_developer가 Fast Campus 패턴 brief 픽업 시작 (1~3분 안)
3. **첫 텔레그램 카드 받으면** ✅ 누름 → 자동 빌드 + 스냅샷 + push → GitHub Pages 반영

### 옵션 — Playwright 설치 (스냅샷 자동화 핵심)
```bash
cd "/Users/seohyeongmin/Desktop/강의 홈페이지 제작"
.venv/bin/pip install playwright
.venv/bin/playwright install chromium
```

### 옵션 — Lighthouse CLI 설치 (점수 측정)
Node.js·npx 있으면 자동 작동. 없으면 점수 부분만 건너뜀(빌드·스크린샷은 정상 작동).

---

## 안전 장치

### 자동 빌드 실패 시
- 빌드 실패하면 site_config.json은 이미 새 값으로 덮어쓴 상태
- 텔레그램에 *빌드 실패 — 사이트 미반영* 카드 + stderr 마지막 줄
- 데몬은 정상 계속 운영 (다른 산출물 처리 안 막힘)
- 회원이 build.py 에러 보고 → `bash build-and-snapshot.command` 재시도

### Playwright 미설치 시
- 빌드는 정상 실행
- 스냅샷 단계만 건너뜀 (텔레그램에 "Playwright 미설치" 안내)
- 데몬·long_poll 모두 정상 작동

### git push 실패 시
- 이미 long_poll.py에 `_git_sync_changes()` 락 + 재시도 로직 있음
- detached HEAD 자동 복구
- 충돌 시 ours 전략으로 데몬 변경 우선

---

## 다음 단계 — Phase 3 (KPI 대시보드, 1주)

Phase 1 완료 → 회원 결정한 순서대로 Phase 3 진행:
- 결제 통합 (페이앱/토스 중 회원 결정 필요)
- 매출 추적 KPI 대시보드
- 매일 09:00 텔레그램에 진척률 카드 (월 1000만원 대비)
- CAC vs LTV 추적

이후 Phase 2 (블로그 파워블로그화, 3주) → Phase 4 (강사 플랫폼, 6주).

---

## 검증 체크리스트

- [x] `scripts/auto_build.py` 생성 — should_trigger_build·run_build·format_telegram_card·trigger_snapshot_async
- [x] `scripts/site_snapshot.py` 생성 — Playwright·Lighthouse·텔레그램 통합
- [x] `telegram_bot/client.py` 확장 — send_photo·send_media_group
- [x] `telegram_bot/poll.py` hook — 승인 후 자동 빌드 + 스냅샷
- [x] `FASTCAMPUS_PATTERN.md` reference 작성
- [x] `agents/site_developer.py` reference 자동 주입
- [x] `briefs/phase1-site-dev-fastcampus-ref-*.json` 첫 시안 brief 큐잉
- [x] `build-and-snapshot.command` 수동 트리거 패키지
- [ ] Playwright 설치 (회원 액션 필요)
- [ ] 첫 site_developer 산출물 카드 회원 ✅ → 실 배포 검증
