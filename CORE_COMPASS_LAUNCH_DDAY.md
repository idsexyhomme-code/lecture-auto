# Core Compass 출시 D-day 일별 액션 카드

> 5/24 출시 목표. 회원님 D-7 (5/17) 부터 매일 처리할 일.

## D-7 (5/17 토) — 가입 신청 (오늘)

### 회원 직접 (각 30분~1시간)
- [ ] **페이앱** https://payapp.kr → 가맹점 신청 (사업자 등록증)
- [ ] **토스페이먼츠** https://tosspayments.com → 가맹점 신청 (선택)
- [ ] **Resend** https://resend.com → 회원가입·도메인 등록
- [ ] **도메인 DNS** — corecampus.kr DKIM·SPF 레코드 추가 (Resend 안내 따라)

### 자동 진행 (저녁 또는 다음 날)
- [ ] CEO 데몬 정상 동작 확인 → 텔레그램 모니터링 활성

## D-6~5 (5/18~19 일·월) — 심사 대기

### 회원 직접
- [ ] 페이앱 심사 진행률 확인
- [ ] Resend 도메인 인증 완료 (DNS 반영 24~48시간)

### CEO 자율
- [ ] v4 페이지 최종 점검 — 더블클릭 [preview-core-compass-v4.command](computer:///Users/seohyeongmin/Desktop/강의 홈페이지 제작/preview-core-compass-v4.command)

## D-4 (5/20 화) — 키 발급 시작

### 회원 직접
- [ ] 페이앱 SHOP_ID·LINK_KEY 발급 완료 (예상)
- [ ] Resend RESEND_API_KEY 발급
- [ ] `.env`에 키 입력:
  ```
  PAYAPP_SHOP_ID=...
  PAYAPP_LINK_KEY=...
  PAYAPP_LINK_VAL=...
  RESEND_API_KEY=re_...
  ANTHROPIC_API_KEY=sk-ant-...  (이미 있다면)
  ```

### 자동 검증
- [ ] `python3 scripts/payment_router.py` 실행 → 라우터 ✓ 확인
- [ ] `python3 scripts/send_email.py 본인메일` → 이메일 도착 확인

## D-3 (5/21 수) — Webhook 서버 배포

### 회원 직접 (2시간 소요)
- [ ] **Vercel 배포 (간단)**:
  ```bash
  cd "~/Desktop/강의 홈페이지 제작"
  npx vercel --prod
  ```
  → webhook URL 발급받음 (예: corecampus-webhook.vercel.app/webhook/payapp)
- [ ] 페이앱 콘솔 → webhook URL 등록
- [ ] 테스트 결제 1건 (본인 카드, 100원 또는 9,900원) → webhook 동작 확인

### 또는 옵션 B — Mac mini 로컬 + ngrok
```bash
brew install ngrok
ngrok http 5000  # webhook 외부 노출
python3 scripts/webhook_server.py  # 로컬 실행
```

## D-2 (5/22 목) — 출시 전 최종 점검

### 회원 직접
- [ ] `./launch-core-compass.command` 더블클릭 → 6단계 자동 점검
- [ ] 점검 PASS 확인
- [ ] 도메인 DNS HTTPS 동작 확인 (`curl -I https://corecampus.kr`)
- [ ] 모바일 브라우저에서 직접 결제 흐름 1회 (본인 결제 → 환불)

## D-1 (5/23 금) — 마케팅 준비

### 회원 직접
- [ ] SNS 카드 이미지 다운로드 — `site/landing/core-compass/v4/cards/instagram-feed.svg`
- [ ] 인스타·페북·X에 예약 발행 설정 (또는 5/24 오전 9시 직접 발행)
- [ ] 블로그 글 — `site/blog-drafts/core-compass-launch/post.html` 내용 복사 → Tistory·Naver 블로그 작성
- [ ] 이메일 뉴스레터 발송 (구독자 있다면) — 미리 작성

## D-0 (5/24 토) — 출시일

### 오전 (09:00 KST)
- [ ] SNS 카드 이미지 인스타·페북 동시 발행
- [ ] X (트위터) 3 tweet thread 발행
- [ ] 블로그 글 Tistory·Naver 동시 발행
- [ ] 텔레그램 모니터링 시작

### 오전 (10:00 KST)
- [ ] 이메일 뉴스레터 발송 (구독자에게)

### 오후 (14:00 KST)
- [ ] 카카오톡 친구·지인 개인 메시지 (CORE_COMPASS_LAUNCH_COPY.md 참고)
- [ ] 첫 결제 모니터 — 텔레그램 알림 확인

### 저녁 (21:00 KST)
- [ ] D-day KPI 점검 — 결제 건수·문의·후기
- [ ] 100명 한정 진행률 확인

## D+1~7 (출시 후 1주) — 모니터링

### 매일
- [ ] 텔레그램 결제 알림 실시간 모니터
- [ ] 진단 결과 도착 확인 (이메일 발송 정상?)
- [ ] 문의·환불 요청 처리

### 매일 09:00 (CEO 자율)
- [ ] 일일 보고에 Core Compass 섹션 자동 포함
- [ ] KPI 추이 텔레그램 카드 발송

## 출시 후 100명 도달 시

- [ ] 결제 페이지에 "마감 임박" 표시
- [ ] 100명 도달 시 자동 매진 + 정가 19,900원으로 복귀
- [ ] 다음 100명 또는 정가 운영 결정 (회원)
