# 6 LLM API key 발급 — 회원 액션 가이드

> Core Compass 백엔드 "6 AI 다중 검증" 완성을 위한 API key 발급 순서.
> 비용·난이도·우선순위 순으로 정렬. **Gemini는 100% 무료**부터 시작 추천.

---

## 💰 비용 요약 (1건 진단당)

| LLM | 1건 비용 | 월 100건 시 |
|---|---|---|
| Gemini 2.0 Flash | $0.0003 | $0.03 (40원) |
| Claude Sonnet 4 | $0.015 | $1.50 (2,000원) |
| ChatGPT GPT-4o | $0.012 | $1.20 (1,600원) |
| Perplexity Sonar Pro | $0.018 | $1.80 (2,400원) |
| Grok-2 | $0.012 | $1.20 (1,600원) |
| Mistral Large | $0.016 | $1.60 (2,200원) |
| **6개 합계** | **~$0.07** | **~$7.30 (9,800원)** |

→ 월 100건 진단(9,900원 × 100 = 99만원 매출) 기준 API 비용 약 **1만원 (마진 99%)**

---

## 📌 우선순위 1 — Gemini (Google) ← **무료, 즉시 가능**

**비용**: 완전 무료 (월 1,500 RPD까지)
**신용카드**: 불필요
**소요 시간**: 3분

### 발급 절차

1. https://aistudio.google.com/apikey 접속 (Google 계정 로그인 — Gmail 그대로)
2. 우측 상단 `Create API key` 클릭
3. `Create API key in new project` 선택
4. 발급된 키 복사 (AIzaSy... 형태)
5. 도우미 스크립트로 `.env`에 자동 추가 → 다음 섹션 참고

---

## 📌 우선순위 2 — OpenAI 충전 ← 이미 키 있음, 잔액만 부족

**현재 상태**: API key 보유 ✅, 잔액 0원 (RateLimitError 429)
**충전 금액**: 최소 $5 (=한화 약 7,000원)
**소요 시간**: 5분

### 충전 절차

1. https://platform.openai.com/settings/organization/billing 접속
2. `Add payment method` → 신용카드 등록 (해외 결제 가능 카드)
3. `Add to credit balance` → **$5 또는 $10** 충전
4. (선택) Auto recharge 설정 → 잔액 부족 시 자동 충전

**중요**: OpenAI는 prepaid 방식이라 충전 후 즉시 사용 가능. 환불 불가.

---

## 📌 우선순위 3 — Perplexity ← $5 무료 크레딧 (가입 보너스)

**비용**: 가입 시 $5 무료, 이후 종량제
**신용카드**: 필요 (확인용, 무료 크레딧만 쓸 거면 청구 X)
**소요 시간**: 5분

### 발급 절차

1. https://www.perplexity.ai/settings/api 접속 (Google 계정 가능)
2. `Add Credits` → 카드 등록
3. `API Keys` → `+ Create Key` → 키 복사 (pplx-... 형태)

**특징**: 검색 기반 LLM이라 1인 사업 시장 트렌드·경쟁사 조사에 강함. 진단의 "현 시장 상황" 영역 담당.

---

## 📌 우선순위 4 — xAI Grok ← $25 무료 크레딧 (가입 보너스)

**비용**: 가입 시 $25 무료 (월간 갱신)
**신용카드**: 필요 (무료 크레딧 한도 내에서는 청구 X)
**소요 시간**: 5분

### 발급 절차

1. https://console.x.ai/ 접속
2. X(Twitter) 계정 또는 이메일로 가입
3. `Sign up` → 카드 등록 ($25 free credit 자동 부여)
4. `API Keys` → `Create API Key` → 키 복사 (xai-... 형태)

**특징**: 다른 LLM 합의에 견제 역할. 도발적·직설적 응답.

---

## 📌 우선순위 5 — Mistral ← $5 무료 크레딧

**비용**: 가입 시 $5 무료
**신용카드**: 필요
**소요 시간**: 5분

### 발급 절차

1. https://console.mistral.ai/api-keys/ 접속
2. 이메일 가입 → 카드 등록
3. `Create new key` → 키 복사

**특징**: 유럽 LLM. 미국 LLM 4개의 편향 견제.

---

## ⏱️ 발급 후 — .env 자동 추가 도우미

`add-llm-keys.command` 더블클릭 → 인터랙티브 메뉴로 키 추가.

또는 수동: `.env` 파일 열어서 아래 형식으로 추가
```bash
GOOGLE_GENERATIVEAI_API_KEY=AIzaSy...
PERPLEXITY_API_KEY=pplx-...
XAI_API_KEY=xai-...
MISTRAL_API_KEY=...
```

저장 후 `test-multi-llm.command` 다시 실행 → 활성화 LLM 수 확인.

---

## 🎯 최소 권장 — 3개 LLM 작동 시나리오

시간/비용 부담 있으시면 **Claude + ChatGPT 충전 + Gemini 무료** 3개만 활성화해도 "다중 검증" 카피는 정직하게 유지 가능. 추후 매출 데이터 보고 나머지 3개 추가.

랜딩 카피는 정확하게 표기:
- "**3개 AI 다중 검증** (Claude·ChatGPT·Gemini)" — 3개 단계
- "**6개 AI 다중 검증** (Claude·ChatGPT·Gemini·Perplexity·Grok·Mistral)" — 6개 다 활성화 단계
