"""통합 결제 라우터 — 상품 → PG 자동 매핑.

사용 예:
    from scripts.payment_router import route_payment

    url = route_payment(product_id="core-compass", amount=9900, email="...")
    # → 페이앱 결제 URL

    url = route_payment(product_id="claude-launchpad", amount=49000, email="...")
    # → 토스페이먼츠 Widget 페이지
"""
from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

ROOT = Path(__file__).parent.parent
STATE_DIR = ROOT / "content/state"
PAYMENTS_LOG = STATE_DIR / "payments_log.jsonl"


# ─────────────────────────────────────────────────────────────────
# 상품 → PG 매핑
# ─────────────────────────────────────────────────────────────────

PRODUCT_PG_MAP = {
    # Core Compass (9,900원) → 페이앱
    "core-compass": {"pg": "payapp", "default_amount": 9900},

    # 일반 코스 → 토스페이먼츠
    "claude-launchpad": {"pg": "toss", "default_amount": 49000},
    "claude-autowork": {"pg": "toss", "default_amount": 49000},
    "claude-bizflow": {"pg": "toss", "default_amount": 49000},
    "claude-content-engine": {"pg": "toss", "default_amount": 49000},
    "claude-customer-script": {"pg": "toss", "default_amount": 49000},
    "claude-customer-support": {"pg": "toss", "default_amount": 49000},
    "claude-daily-recap": {"pg": "toss", "default_amount": 29000},
    "claude-intro-email": {"pg": "toss", "default_amount": 29000},
    "claude-mail-writing": {"pg": "toss", "default_amount": 49000},
    "claude-meeting-notes": {"pg": "toss", "default_amount": 49000},
    "claude-monthly-revenue": {"pg": "toss", "default_amount": 79000},
    "claude-pricing-page": {"pg": "toss", "default_amount": 49000},
    "claude-sop": {"pg": "toss", "default_amount": 49000},
    "claude-sop-onboarding": {"pg": "toss", "default_amount": 49000},
    "claude-youtube-plan": {"pg": "toss", "default_amount": 79000},
    "core-campus-general": {"pg": "toss", "default_amount": 49000},
    "core-campus-meta": {"pg": "toss", "default_amount": 49000},
    "deepwork-1hr": {"pg": "toss", "default_amount": 29000},
    "tax-basics-solopreneur": {"pg": "toss", "default_amount": 49000},
}


def resolve_pg(product_id: str, override_pg: str | None = None) -> str:
    """상품 → PG 매핑. override 우선."""
    if override_pg:
        return override_pg
    info = PRODUCT_PG_MAP.get(product_id)
    if info:
        return info["pg"]
    log.warning("Unknown product_id=%s, fallback to payapp", product_id)
    return "payapp"


def log_payment_event(event: dict[str, Any]) -> None:
    """모든 결제 이벤트 jsonl 로깅."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    event = {**event, "ts": int(time.time())}
    with open(PAYMENTS_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


# ─────────────────────────────────────────────────────────────────
# 페이앱 어댑터
# ─────────────────────────────────────────────────────────────────

def request_payapp_payment(
    *,
    email: str,
    amount: int,
    product_name: str,
    order_id: str,
) -> dict[str, Any]:
    """페이앱 결제 요청 → 결제 페이지 URL 반환.

    Returns:
        {"ok": bool, "payment_url": str, "raw": str}
    """
    shop_id = os.environ.get("PAYAPP_SHOP_ID")
    link_key = os.environ.get("PAYAPP_LINK_KEY")
    link_val = os.environ.get("PAYAPP_LINK_VAL")

    if not all([shop_id, link_key, link_val]):
        return {
            "ok": False,
            "error": "PAYAPP keys missing in .env",
            "payment_url": None,
        }

    try:
        import requests  # type: ignore
    except ImportError:
        return {"ok": False, "error": "requests not installed", "payment_url": None}

    data = {
        "cmd": "payrequest",
        "userid": shop_id,
        "linkkey": link_key,
        "linkval": link_val,
        "goodname": product_name,
        "price": str(amount),
        "smsuse": "n",
        "buyer": email,
        "var1": order_id,
        "feedbackurl": os.environ.get("PAYAPP_WEBHOOK_URL", ""),
        "returnurl": os.environ.get("PAYAPP_RETURN_URL", "https://corecampus.kr/payment/success"),
    }

    r = requests.post("https://api.payapp.kr/oapi/apiLoad.html", data=data, timeout=10)
    log_payment_event({
        "type": "payapp_request",
        "order_id": order_id,
        "email": email,
        "amount": amount,
        "status_code": r.status_code,
    })

    # 응답 파싱 (페이앱 query string 응답)
    from urllib.parse import parse_qs
    parsed = parse_qs(r.text)
    if parsed.get("state", [""])[0] == "1":
        return {
            "ok": True,
            "payment_url": parsed.get("payurl", [""])[0],
            "mul_no": parsed.get("mul_no", [""])[0],
            "raw": r.text,
        }
    return {
        "ok": False,
        "error": parsed.get("errorMessage", ["unknown"])[0],
        "payment_url": None,
        "raw": r.text,
    }


# ─────────────────────────────────────────────────────────────────
# 토스페이먼츠 어댑터 (Widget — 서버는 승인만 처리)
# ─────────────────────────────────────────────────────────────────

def confirm_toss_payment(
    *,
    payment_key: str,
    order_id: str,
    amount: int,
) -> dict[str, Any]:
    """토스페이먼츠 결제 승인 (Widget이 frontend에서 결제 → 백엔드 confirm).

    Returns:
        {"ok": bool, "payment": dict}
    """
    secret_key = os.environ.get("TOSS_SECRET_KEY")
    if not secret_key:
        return {"ok": False, "error": "TOSS_SECRET_KEY missing"}

    try:
        import requests  # type: ignore
        import base64
    except ImportError:
        return {"ok": False, "error": "requests not installed"}

    auth = base64.b64encode(f"{secret_key}:".encode()).decode()
    r = requests.post(
        "https://api.tosspayments.com/v1/payments/confirm",
        headers={
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/json",
        },
        json={
            "paymentKey": payment_key,
            "orderId": order_id,
            "amount": amount,
        },
        timeout=10,
    )
    data = r.json() if r.headers.get("Content-Type", "").startswith("application/json") else {}
    log_payment_event({
        "type": "toss_confirm",
        "order_id": order_id,
        "payment_key": payment_key,
        "amount": amount,
        "status_code": r.status_code,
        "raw": data,
    })
    return {"ok": r.status_code == 200, "payment": data}


# ─────────────────────────────────────────────────────────────────
# 스마트스토어 — 외부 리다이렉트 (코드 결제 처리 X)
# ─────────────────────────────────────────────────────────────────

def get_naver_store_url(product_id: str) -> str | None:
    """스마트스토어 상품 URL 조회 (.env에서)."""
    env_key = f"NAVER_STORE_{product_id.upper().replace('-', '_')}_URL"
    return os.environ.get(env_key)


# ─────────────────────────────────────────────────────────────────
# 메인 라우터
# ─────────────────────────────────────────────────────────────────

def route_payment(
    *,
    product_id: str,
    amount: int | None = None,
    email: str,
    channel: str | None = None,  # "default" / "naver_store"
) -> dict[str, Any]:
    """상품 → 결제 URL/method 반환.

    Args:
        product_id: 상품 슬러그
        amount: 결제 금액 (None이면 default 사용)
        email: 구매자 이메일
        channel: "naver_store"면 스마트스토어 URL 반환

    Returns:
        {"ok": bool, "method": "redirect"|"widget"|"external", "url": str, "extra": dict}
    """
    info = PRODUCT_PG_MAP.get(product_id, {"pg": "payapp", "default_amount": 9900})
    amount = amount or info["default_amount"]
    order_id = f"order_{product_id}_{int(time.time())}"

    # 채널 override — 스마트스토어 강제
    if channel == "naver_store":
        url = get_naver_store_url(product_id)
        if not url:
            return {"ok": False, "error": f"Naver store URL not set for {product_id}"}
        return {"ok": True, "method": "external", "url": url, "extra": {"channel": "naver_store"}}

    pg = info["pg"]
    if pg == "payapp":
        result = request_payapp_payment(
            email=email,
            amount=amount,
            product_name=product_id,
            order_id=order_id,
        )
        if result["ok"]:
            return {
                "ok": True,
                "method": "redirect",
                "url": result["payment_url"],
                "extra": {"pg": "payapp", "order_id": order_id, "mul_no": result.get("mul_no")},
            }
        return {"ok": False, "error": result.get("error", "payapp failed")}

    if pg == "toss":
        # Widget 결제 — Frontend가 처리하므로 백엔드는 widget 페이지 URL 반환
        widget_url = f"/site/landing/checkout-toss?product={product_id}&amount={amount}&email={email}&order={order_id}"
        return {
            "ok": True,
            "method": "widget",
            "url": widget_url,
            "extra": {"pg": "toss", "order_id": order_id, "amount": amount},
        }

    return {"ok": False, "error": f"Unknown PG: {pg}"}


if __name__ == "__main__":
    # 테스트 — 페이앱 키 없으면 error 메시지 반환
    print("Test 1 — Core Compass (페이앱):")
    print(route_payment(product_id="core-compass", email="test@example.com"))
    print("\nTest 2 — claude-launchpad (토스):")
    print(route_payment(product_id="claude-launchpad", email="test@example.com"))
    print("\nTest 3 — 스마트스토어 채널:")
    print(route_payment(product_id="core-compass", email="test@example.com", channel="naver_store"))
