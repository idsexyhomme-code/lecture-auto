# Core Compass 출시 직전 체크리스트

## 1. 결제 인프라 (필수 — 회원 직접)

- [ ] 페이앱 가입 + 사업자 등록증 인증
- [ ] 페이앱 SHOP_ID·LINK_KEY·LINK_VAL 발급
- [ ] `.env`에 페이앱 키 입력
- [ ] 페이앱 webhook URL 설정: `https://corecampus.kr/webhook/payapp`
- [ ] 페이앱 테스트 결제 1건 (회원 본인 카드)
- [ ] 환불 처리 테스트 (페이앱 콘솔에서)

## 2. 이메일 발송 (필수 — 회원 직접)

- [ ] Resend (또는 Mailgun) 가입
- [ ] 도메인 인증 (DNS DKIM·SPF 추가)
- [ ] `.env`에 RESEND_API_KEY 입력
- [ ] 테스트 메일 1건 발송 (본인 메일)
- [ ] 한글·이미지 정상 표시 확인

## 3. 도메인·호스팅 (필수 — 회원 직접)

- [ ] `corecampus.kr` 도메인 결제·갱신 상태 확인
- [ ] DNS A 레코드 (또는 CNAME) — Cloudflare·Vercel·Render 등 호스팅 가리킴
- [ ] HTTPS 인증서 자동 갱신 (Let's Encrypt or Cloudflare)
- [ ] `webhook/payapp` 엔드포인트 설정 (실제 결제 받는 endpoint)

## 4. 콘텐츠 (CEO 자율 완료 — 점검만)

- [x] Core Compass 랜딩 v3 [/site/landing/core-compass/v3/index.html]
- [x] 결제 페이지 [/site/landing/core-compass/v3/checkout-payapp.html]
- [x] 결제 성공 페이지 [/site/landing/core-compass/v3/success.html]
- [x] 결과 페이지 템플릿 [/site/landing/core-compass/v3/result.html]
- [x] 만료 페이지 [/site/landing/core-compass/v3/expired.html]
- [x] 404 페이지 [/site/landing/core-compass/v3/404.html]
- [x] 이메일 템플릿 [/site/landing/core-compass/v3/email-template.html]
- [x] OG 이미지 SVG (PNG 변환 필요 — 별도 작업)

## 5. 백엔드 (회원 결정 필요)

- [ ] 결제 webhook 받을 서버 (옵션):
  - 옵션 A: Vercel Serverless Functions (무료, 쉬움)
  - 옵션 B: AWS Lambda (확장성)
  - 옵션 C: 자체 서버 (Mac mini · 라즈베리파이 등)
- [ ] `scripts/payment_webhooks.py` 의 함수를 Flask·FastAPI 라우터에 마운트
- [ ] webhook URL을 페이앱 콘솔에 등록

## 6. 진단 자동 생성 (CEO 자율)

- [x] `production_planning_agent` 가 Core Compass 티켓 처리 가능 (스켈레톤)
- [ ] `handle_core_compass_ticket()` 실제 구현 (5개 섹션 생성 프롬프트)
- [ ] 개인 URL 토큰 발급 시스템 (`/r/{token}/`)
- [ ] 24시간 만료 자동 처리 (cron 또는 lazy check)

## 7. 정책·약관 (필수)

- [x] 환불 정책 [REFUND_POLICY.md]
- [ ] 이용약관 페이지 (site/terms.html — 다음 단계)
- [ ] 개인정보처리방침 (site/privacy.html — 다음 단계)
- [x] FAQ에 환불·24시간·Core Campus 관계 명시

## 8. 마케팅 (회원 결정)

- [ ] 출시일 결정 (예: 2026-05-25)
- [ ] 첫 100명 모집 채널:
  - [ ] 회원 SNS (인스타·페이스북·트위터)
  - [ ] Core Campus 블로그 글 (출시 안내)
  - [ ] 카카오톡 친구 알림
  - [ ] 이메일 (기존 구독자 있다면)
- [ ] 홍보 카피 — Core Compass 톤 친근하게

## 9. 모니터링 (CEO 자동)

- [x] 결제 KPI 추적 (`payment_by_channel` 추가됨)
- [x] 텔레그램 알림 인프라 (기존 운영 중)
- [ ] 출시 후 일일 보고에 Core Compass 섹션 추가
- [ ] 100명 한정 카운터 (별도 구현)

## 10. 출시 D-day 시나리오

1. 회원이 .env 모든 키 입력 확인
2. 페이앱 본인 결제 1건 → 환불 (전체 흐름 검증)
3. Resend 본인 메일 발송 1건 (도메인 인증 확인)
4. corecampus.kr 메인 페이지 → Core Compass 배너 노출
5. SNS·블로그 출시 안내 동시 발행
6. 첫 24시간 모니터링 — 텔레그램 실시간 알림
7. 100명 도달 시 결제 페이지에 "마감 임박" 표시
8. 출시 1주일 후 KPI 리뷰

## 회원 진행 순서 추천

| Day | 작업 | 소요 |
|---|---|---|
| D-7 | 페이앱·Resend 가입 신청 | 30분 |
| D-5 | 사업자 등록증 인증 + 키 발급 대기 | 자동 |
| D-3 | 키 .env 입력 + 테스트 결제·메일 | 1시간 |
| D-2 | 백엔드 webhook 셋업 (Vercel 등) | 2시간 |
| D-1 | 도메인 DNS·HTTPS 최종 점검 | 30분 |
| **D-0** | **출시** | 종일 |
