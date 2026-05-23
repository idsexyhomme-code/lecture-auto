# 결제 시스템 연동 가이드 — 2026-05-16

> 회원님이 PG 키 입력 후 동작할 코드·페이지가 준비됨. 이 문서가 그 연결 가이드.

## 1. 페이앱 (Core Compass 9,900원 전용)

### 결제 페이지
[site/landing/core-compass/v3/checkout-payapp.html](computer:///Users/seohyeongmin/Desktop/강의 홈페이지 제작/site/landing/core-compass/v3/checkout-payapp.html)

### 연동 방식 — 리다이렉트 결제
1. 사용자가 폼 입력 → 서버에 POST
2. 서버가 페이앱 API에 결제 요청 (SHOP_ID·LINK_KEY 사용)
3. 페이앱이 결제 페이지 URL 반환
4. 사용자를 페이앱 결제 페이지로 리디렉트
5. 결제 완료 후 페이앱이 우리 webhook URL로 콜백

### .env 입력
```bash
# 페이앱 가입 후 발급받은 키
PAYAPP_SHOP_ID=test_shop_id
PAYAPP_LINK_KEY=test_link_key
PAYAPP_LINK_VAL=test_link_val
PAYAPP_WEBHOOK_URL=https://corecampus.kr/webhook/payapp
```

### 서버 코드 (scripts/payment_router.py 참조)
```python
def request_payapp_payment(email, amount, product_name):
    """페이앱 결제 요청 → 결제 URL 반환"""
    import requests, os
    url = "https://api.payapp.kr/oapi/apiLoad.html"
    data = {
        "cmd": "payrequest",
        "userid": os.environ["PAYAPP_SHOP_ID"],
        "linkkey": os.environ["PAYAPP_LINK_KEY"],
        "linkval": os.environ["PAYAPP_LINK_VAL"],
        "goodname": product_name,
        "price": amount,
        "feedbackurl": os.environ["PAYAPP_WEBHOOK_URL"],
        "smsuse": "n",
        "buyer": email,
    }
    r = requests.post(url, data=data, timeout=10)
    # 응답 파싱 → payapp_url 추출
    return r.text  # 실제로는 결제 URL JSON
```

## 2. 토스페이먼츠 (코스 49,000~79,000원 전용)

### 결제 페이지 (시안)
`site/design-previews/checkout-toss/index.html` — 다음 단계에서 작성

### 연동 방식 — Widget 결제 (가장 쉬움)
1. 페이지에 Toss Widget 스크립트 로드
2. 클라이언트키로 widget 초기화
3. 사용자 카드 정보 입력 (Widget 내부)
4. Widget이 결제 토큰 발급 → 서버에 전송
5. 서버가 시크릿키로 결제 승인 API 호출

### .env 입력
```bash
# 토스페이먼츠 가입 후 발급
TOSS_CLIENT_KEY=test_ck_xxx  # 프론트엔드 노출 OK
TOSS_SECRET_KEY=test_sk_xxx  # 서버 사이드만
TOSS_WEBHOOK_URL=https://corecampus.kr/webhook/toss
```

### 클라이언트 코드 (Widget)
```html
<div id="payment-widget"></div>
<script src="https://js.tosspayments.com/v1/payment-widget"></script>
<script>
  const widget = PaymentWidget(
    window.TOSS_CLIENT_KEY,  // 환경변수에서 주입
    PaymentWidget.ANONYMOUS  // 비로그인 결제 가능
  );

  widget.renderPaymentMethods('#payment-widget', { value: 49000 });

  document.getElementById('pay-btn').addEventListener('click', () => {
    widget.requestPayment({
      orderId: 'order_' + Date.now(),
      orderName: '부캐 서비스 7일 런칭',
      successUrl: window.location.origin + '/payment/success',
      failUrl: window.location.origin + '/payment/fail',
      customerEmail: email,
    });
  });
</script>
```

## 3. 스마트스토어 (네이버 SEO 채널)

### 연동 방식 — 외부 리다이렉트 (가장 간단)
- 회원이 네이버 스마트스토어에 상품 등록
- 우리 사이트의 "스토어에서 구매" 버튼이 스토어 상품 URL로 이동
- 결제·정산은 스토어 시스템 사용 (우리 코드 X)

### 회원 직접 해야 할 일
1. https://smartstore.naver.com → 판매자 가입
2. 상품 등록 (Core Compass·코스별)
3. 스토어 URL 메모: `https://smartstore.naver.com/{stove-id}/products/{product-id}`
4. .env에 URL 저장:
   ```bash
   NAVER_STORE_CORE_COMPASS_URL=https://smartstore.naver.com/.../12345
   NAVER_STORE_COURSE_LAUNCHPAD_URL=https://smartstore.naver.com/.../67890
   ```

### 우리 사이트 코드
```html
<a href="{{NAVER_STORE_CORE_COMPASS_URL}}" class="btn btn--secondary">
  스마트스토어에서 구매 (네이버페이)
</a>
```

## 통합 결제 라우터

`scripts/payment_router.py`가 상품 → PG 자동 라우팅:
- 9,900원 이하 → 페이앱
- 49,000~99,000원 → 토스페이먼츠
- SEO 트래픽 → 스마트스토어 (별도 페이지)

## 검증 순서 (회원 직접)

1. 페이앱 가입·키 발급 (3~5일)
2. 페이앱 테스트 결제 1건 (회원 본인 카드 100원)
3. webhook 콜백 확인 (`content/state/payments_log.jsonl` 기록)
4. 환불 처리 테스트 (페이앱 관리자 패널)
5. 토스페이먼츠 같은 흐름 반복
6. 스마트스토어 상품 등록

## 관련 파일

- [site/landing/core-compass/v3/checkout-payapp.html](computer:///Users/seohyeongmin/Desktop/강의 홈페이지 제작/site/landing/core-compass/v3/checkout-payapp.html) — Core Compass 결제 페이지
- [PAYMENT_PG_COMPARISON.md](computer:///Users/seohyeongmin/Desktop/강의 홈페이지 제작/PAYMENT_PG_COMPARISON.md) — PG 3사 비교
- (다음) scripts/payment_router.py
- (다음) scripts/payment_webhooks.py
- (다음) .env.payment.example
