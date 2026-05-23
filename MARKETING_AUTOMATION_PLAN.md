# 마케팅·광고·이메일 자동화 통합 계획

## 1. 구글 광고 (검색·디스플레이)

### 캠페인 1 — "1인 사업 진단" 검색
| 검색어 | 클릭당 입찰 | 카피 |
|---|---|---|
| "1인 사업 진단" | 1,500원 | 9,900원 AI 진단 — 1페이지 정리 |
| "AI 사업 분석" | 1,200원 | 6 LLM 협업 — 운명 말고 90일 실행 |
| "창업 진단" | 1,000원 | 사업 시작 막막할 때 — 9,900원 진단 |
| "사업 방향 찾기" | 1,000원 | AI가 정리하는 1페이지 진단 |
| "1인기업 시작" | 800원 | 90일 실행 로드맵 — 9,900원 |

월 광고 예산: 30만원 (200~300 클릭)
타겟 CTR: 5%+ / CPC 1,000원 평균

### 카피 7세트 (검색)
1. 헤드라인 1: "9,900원 1인 사업 AI 진단"
2. 헤드라인 2: "AI 6명이 한 장에 정리"
3. 헤드라인 3: "90일 실행 로드맵 받기"
4. 설명 1: "ChatGPT·Claude·Gemini 6 LLM이 협업한 진단 리포트"
5. 설명 2: "한정 100명 출시 프로모션. 정가 19,900원."
6. CTA: "9,900원으로 진단 받기"
7. URL: corecampus.kr/site/landing/core-compass/v4/

## 2. 메타 광고 (페북·인스타)

### 캠페인 2 — 인스타 피드·스토리
- 타겟: 25~45세 1인 사업 관심자, 한국 거주
- 일 예산: 1만원 (월 30만원)
- 크리에이티브: site/landing/core-compass/v4/cards/instagram-feed.svg

### 카피 (페북 광고)
```
🧭 사주는 받았는데, 사업 시작은 못 했죠?

AI 6명이 한 장에 정리합니다.
- 일하는 성향 1줄
- 맞는 사업 3가지
- 이번 주 할 일 3가지

9,900원 출시 프로모션 (정가 19,900원)
한정 100명까지.

👉 corecampus.kr
```

## 3. 이메일 시퀀스 — 출시 1주차 (5개)

### Email 1 — Welcome (결제 직후 발송)
- 제목: "{NAME}님, 진단이 도착했어요."
- 본문: 개인 URL + 24h 만료 안내
- CTA: 결과 페이지 열기

### Email 2 — Day 1 (24h 후)
- 제목: "어제 진단 결과 도움 되셨어요?"
- 본문: 만료 안내 + 1회 무료 연장 옵션
- CTA: 연장 신청

### Email 3 — Day 3
- 제목: "이번 주 할 일 3가지 — 시작하셨나요?"
- 본문: 진단 결과 §7 다시 보내기 + Core Campus 코스 추천
- CTA: 추천 코스 1개 (49,000원)

### Email 4 — Day 5
- 제목: "남들은 어떻게 시작했을까?"
- 본문: 비슷한 페르소나 사례 1~2개 + 후기
- CTA: 코칭 49,000원

### Email 5 — Day 7
- 제목: "마지막 안내 — 출시 프로모션 마감"
- 본문: 90일 그룹 99,000원 출시 알림 + 코스 할인
- CTA: 그룹 신청

## 4. 이메일 시퀀스 — 1~2개월 차 (지속)

### 주간 발송 (매주 화요일)
- 새 블로그 글 1편 (CONTENT_PIPELINE.md 통해 자동)
- 코스 추천 1개
- 후기 1개

### 월 1회 발송 (1일)
- 월간 KPI 요약
- 다음 달 출시 예정 상품
- 회원 한정 할인 코드

## 5. 자동화 도구 비교

| 도구 | 가격 | 기능 | 추천 |
|---|---|---|---|
| **Resend** | 무료 (3,000/월) | API 발송·도메인 인증 | ✅ 트랜잭셔널 |
| **Stibee** | 무료 (구독자 1,000) | 한국형·블록 에디터 | 뉴스레터 |
| **Mailgun** | 무료 (100/일) | 글로벌 | 백업 |
| **Brevo (이전 Sendinblue)** | 무료 (300/일) | 한국 운영자 친화 | 마케팅 자동화 |

## 6. 광고·이메일 효과 추적 (UTM)

모든 광고·이메일 링크에 UTM:
```
?utm_source=google&utm_medium=cpc&utm_campaign=launch&utm_content=adcopy1
?utm_source=email&utm_medium=newsletter&utm_campaign=day3
```

추적 데이터 → `content/state/payments_completed.jsonl`에 source 필드 자동 기록.

## 7. 후기 모집 시스템

### 결과 페이지 하단 (다음 차수에서 추가)
```html
<div class="review-prompt">
  <p>이 진단 어땠어요?</p>
  <div class="stars">★★★★★</div>
  <textarea placeholder="짧게 적어주세요 (선택)"></textarea>
  <button>제출</button>
</div>
```

### 인센티브
- 후기 작성 시 추천 코스 10% 할인 코드

## 8. 보안 점검 (출시 전)

- [ ] webhook URL HTTPS만 받음
- [ ] payapp·toss 시그너처 검증 ✓
- [ ] CSRF 토큰 (form 제출 시)
- [ ] Rate limit (분당 60 요청)
- [ ] SQL Injection 방지 (parameterized query)
- [ ] XSS 방지 (innerHTML 사용 시 escape)
- [ ] secrets는 .env 만 (코드·git에 X)

## 9. 성능 목표 (Lighthouse)

| 지표 | 목표 |
|---|---|
| Performance | 90+ |
| Accessibility | 95+ |
| Best Practices | 90+ |
| SEO | 90+ |
| First Contentful Paint | < 1.8s |
| Largest Contentful Paint | < 2.5s |
| Cumulative Layout Shift | < 0.1 |

### 최적화 체크리스트
- [x] 폰트 preconnect·preload
- [x] CSS 인라인 critical
- [ ] 이미지 lazy loading
- [ ] HTTP/2·gzip·brotli
- [ ] CDN 캐싱 (Cloudflare)

## 10. 회원 결재 안건

- 광고 예산 — 월 50~100만원 (구글 30 + 메타 30 + 콘텐츠)
- Stibee·Brevo 둘 다 가입 (한국 뉴스레터 + 글로벌 마케팅 자동화)
- Cloudflare 도입 (성능·보안)
