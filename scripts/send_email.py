"""Resend 이메일 발송 모듈.

회원이 .env에 RESEND_API_KEY 입력 후 동작.

사용:
    from scripts.send_email import send_compass_email
    result = send_compass_email(
        to_email="user@example.com",
        user_name="홍길동",
        result_url="https://corecampus.kr/site/landing/core-compass/r/abc123/",
        one_line_insight="실행형 솔로 — 작게 만들고 빠르게.",
    )
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

log = logging.getLogger(__name__)

ROOT = Path(__file__).parent.parent
TEMPLATE = ROOT / "site/landing/core-compass/v4/email-template.html"

KST = timezone(timedelta(hours=9))


def send_compass_email(
    *,
    to_email: str,
    user_name: str,
    result_url: str,
    one_line_insight: str,
    expire_hours: int = 24,
) -> dict:
    """Core Compass 결제 후 발송 이메일.

    Returns:
        {"ok": bool, "id": str|None, "error": str|None}
    """
    api_key = os.environ.get("RESEND_API_KEY")
    if not api_key:
        return {"ok": False, "error": "RESEND_API_KEY missing in .env"}

    try:
        import requests
    except ImportError:
        return {"ok": False, "error": "requests not installed"}

    # 템플릿 로드
    if not TEMPLATE.exists():
        return {"ok": False, "error": f"Template not found: {TEMPLATE}"}
    tpl = TEMPLATE.read_text(encoding="utf-8")

    # 만료 시간 (KST)
    expire_at = (datetime.now(KST) + timedelta(hours=expire_hours)).strftime("%Y-%m-%d %H:%M KST")

    # 변수 치환
    body = (
        tpl.replace("{{USER_NAME}}", user_name)
        .replace("{{RESULT_URL}}", result_url)
        .replace("{{ONE_LINE_INSIGHT}}", one_line_insight)
        .replace("{{EXPIRE_AT}}", expire_at)
    )

    # Resend API 호출
    try:
        r = requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "from": os.environ.get("EMAIL_FROM", "Core Compass <hello@corecampus.kr>"),
                "to": [to_email],
                "subject": f"{user_name}님, 진단이 도착했어요. — Core Compass",
                "html": body,
            },
            timeout=10,
        )
        if r.status_code == 200:
            data = r.json()
            log.info("Resend email sent: %s → %s", data.get("id"), to_email)
            return {"ok": True, "id": data.get("id")}
        return {"ok": False, "error": f"Resend API {r.status_code}: {r.text[:200]}"}
    except Exception as e:
        log.error("Resend send error: %s", e)
        return {"ok": False, "error": str(e)}


if __name__ == "__main__":
    # 테스트 — 회원이 RESEND_API_KEY 입력 후 본인 메일로 발송
    import sys
    to = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("TEST_EMAIL", "")
    if not to:
        print("Usage: python send_email.py <your_email>")
        sys.exit(1)
    result = send_compass_email(
        to_email=to,
        user_name="테스트",
        result_url="https://corecampus.kr/site/landing/core-compass/r/test/",
        one_line_insight="실행형 솔로 — 작게 만들고 빠르게 검증.",
    )
    print(result)
