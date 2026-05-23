# Core Compass 결제 → 진단 자동 워크플로

## 전체 흐름

```
[1] 결제 완료 (페이앱 webhook)
     ↓
[2] payment_webhooks.emit_payment_completed()
     ↓
[3] content/tasks/pending/compass-{order_id}.json 자동 생성
     ↓
[4] long_poll daemon이 5초마다 pending 픽업
     ↓
[5] production_planning_agent가 진단 생성 (5~10분)
     ↓
[6] result.html 템플릿 채우기 + 개인 URL 토큰 발급
     ↓
[7] 이메일 발송 (Mailgun/Resend/Postmark)
     ↓
[8] 회원 텔레그램 알림 (결제·진단·발송)
     ↓
[9] 결과 페이지 24시간 유효
```

## 1. production_planning_agent — 진단 생성 강화

현재 production_planning_agent는 일반 코스 제작용. Core Compass 전용 분기 추가 필요:

```python
# agents/sub_agents.py 또는 별도 production_planning.py 에 추가
def handle_core_compass_ticket(ticket: dict) -> dict:
    """결제 완료 → 7개 섹션 진단 → result.html 채우기"""
    email = ticket["context"]["email"]
    order_id = ticket["context"]["order_id"]

    # 1. AI 6명 시뮬레이션 — 사실 1번 호출 (multi-perspective prompt)
    sections = generate_7_sections(email)

    # 2. result.html 템플릿 로드
    tpl = Path("site/landing/core-compass/v3/result.html").read_text()

    # 3. 변수 치환
    user_name = sections.get("user_name", "회원")
    result = tpl.replace("{{USER_NAME}}", user_name)
    for i, sec in enumerate(sections.get("sections", []), 1):
        result = result.replace(f"{{{{SECTION_{i}_TITLE}}}}", sec["title"])
        result = result.replace(f"{{{{SECTION_{i}_BODY}}}}", sec["body"])

    # 4. 개인 URL 토큰 발급
    token = generate_token(order_id)
    out_path = Path(f"site/landing/core-compass/r/{token}/index.html")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(result)

    return {
        "result_url": f"https://corecampus.kr/site/landing/core-compass/r/{token}/",
        "expires_at": (datetime.now() + timedelta(hours=24)).isoformat(),
    }
```

## 2. PDF 생성 옵션 (옵션 — 회원 요청 시)

### 옵션 A — wkhtmltopdf (간단, 무료)
```bash
brew install wkhtmltopdf
wkhtmltopdf result.html report.pdf
```
- 한글 폰트 임베드 자동 (Pretendard cdn 로딩 시간 필요)
- 페이지 분할 자동
- 단점: 최신 CSS 일부 미지원

### 옵션 B — puppeteer (모던, JS 필요)
```bash
npm install puppeteer
```
```javascript
const browser = await puppeteer.launch();
const page = await browser.newPage();
await page.goto('file:///path/to/result.html');
await page.pdf({ path: 'report.pdf', format: 'A4' });
```
- 모든 CSS 완벽 지원
- 한글 폰트 perfect
- 단점: 약 100MB 의존성

### 권장 — 옵션 A (간단·작은 의존성)

## 3. 이메일 발송 시스템 비교

| 서비스 | 무료 한도 | 한글 폰트 | API 난이도 | 한국 IP |
|---|---|---|---|---|
| **Resend** | 100/일·3000/월 | ✓ | 매우 쉬움 | △ (USA) |
| **Mailgun** | 100/일 | ✓ | 쉬움 | △ |
| **Postmark** | 100/월 | ✓ | 쉬움 | △ |
| **AWS SES** | 62k/월 (저렴) | ✓ | 중 | △ |
| **Stibee** | 별도 (한국) | ✓ | 한국형 API | ✓ |

### 권장 — Resend (3000/월 무료, 가장 모던)

```python
# scripts/send_email.py
import os, requests

def send_compass_email(to_email: str, user_name: str, result_url: str, one_line_insight: str):
    """Core Compass 결제 후 발송 이메일."""
    api_key = os.environ.get("RESEND_API_KEY")
    if not api_key:
        return {"ok": False, "error": "RESEND_API_KEY missing"}

    # 템플릿 로드
    tpl = open("site/landing/core-compass/v3/email-template.html").read()
    expire_at = "...24시간 후..."  # 계산
    body = (tpl
        .replace("{{USER_NAME}}", user_name)
        .replace("{{RESULT_URL}}", result_url)
        .replace("{{ONE_LINE_INSIGHT}}", one_line_insight)
        .replace("{{EXPIRE_AT}}", expire_at)
    )

    r = requests.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "from": "Core Compass <hello@corecampus.kr>",
            "to": [to_email],
            "subject": f"{user_name}님, 진단이 도착했어요. — Core Compass",
            "html": body,
        },
        timeout=10,
    )
    return {"ok": r.status_code == 200, "id": r.json().get("id")}
```

## 4. 회원 .env 추가 항목

```bash
# Resend (이메일 발송)
RESEND_API_KEY=re_xxx
EMAIL_FROM=Core Compass <hello@corecampus.kr>

# 도메인 인증 (Resend·Mailgun 다 필요)
# 1. Resend.com 가입
# 2. 도메인 등록 (corecampus.kr) → DNS DKIM·SPF 레코드 추가
# 3. 인증 완료 후 발송 가능
```

## 5. 회원 직접 작업

1. Resend·Mailgun·SES 중 1개 선택 → 가입
2. 도메인 DNS에 인증 레코드 추가 (가비아·Cloudflare 등)
3. API 키 .env 입력
4. 첫 테스트 메일 1건 발송 (본인 메일로)
5. 한글 깨짐·이미지 로딩 확인
