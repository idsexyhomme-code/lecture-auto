"""결제 PG webhook 통합 핸들러.

각 PG가 결제 완료/실패/취소 시 우리 서버로 콜백.
이 모듈이 통합 인터페이스 — 각 PG별 검증·정규화 후 공통 이벤트 발행.

배포: Flask·FastAPI·또는 GitHub Actions runner 등 webhook 받을 수 있는 곳에 마운트.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import time
from pathlib import Path
from typing import Any

from scripts.payment_router import log_payment_event

log = logging.getLogger(__name__)

ROOT = Path(__file__).parent.parent
STATE_DIR = ROOT / "content/state"
COMPLETED = STATE_DIR / "payments_completed.jsonl"


def emit_payment_completed(
    *,
    order_id: str,
    pg: str,
    product_id: str,
    amount: int,
    email: str,
    raw: dict,
) -> None:
    """결제 완료 통합 이벤트.

    이걸 발행하면:
    1. payments_completed.jsonl 에 추가
    2. content/tasks/pending/ 에 "Core Compass 진단 생성" 티켓 자동 발행
    3. KPI 갱신 (payment_by_channel)
    """
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    event = {
        "ts": int(time.time()),
        "type": "payment_completed",
        "order_id": order_id,
        "pg": pg,
        "product_id": product_id,
        "amount": amount,
        "email": email,
        "raw": raw,
    }
    with open(COMPLETED, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")

    log_payment_event(event)

    # Core Compass 자동 처리
    if product_id == "core-compass":
        try:
            from agents.sub_agents import dispatch_ticket
            dispatch_ticket({
                "task_id": f"compass-{order_id}",
                "assigned_to": "production_planning_agent",
                "priority": "high",
                "title": f"Core Compass 진단 생성 — {email}",
                "context": {
                    "order_id": order_id,
                    "email": email,
                    "amount": amount,
                    "deadline_hours": 0.5,  # 30분 안 발송
                },
                "expected_output": (
                    "Core Compass 1페이지 진단 리포트 7개 섹션 — "
                    "result.html 템플릿 채우기 + 개인 URL 토큰 발급 + 이메일 발송"
                ),
            })
            log.info("Dispatched Core Compass ticket for order %s", order_id)
        except Exception as e:
            log.error("Failed to dispatch Compass ticket: %s", e)


# ─────────────────────────────────────────────────────────────────
# 페이앱 webhook (피드백 URL 콜백)
# ─────────────────────────────────────────────────────────────────

def handle_payapp_webhook(form_data: dict[str, Any]) -> dict:
    """페이앱 결제 피드백.

    페이앱이 form-urlencoded POST로 보냄:
    - userid, linkkey, mul_no, pay_state, price, var1 (order_id), buyer 등
    """
    expected_shop = os.environ.get("PAYAPP_SHOP_ID")
    expected_link = os.environ.get("PAYAPP_LINK_KEY")

    if form_data.get("userid") != expected_shop:
        log.warning("Payapp webhook userid mismatch")
        return {"ok": False, "error": "userid mismatch"}

    if form_data.get("linkkey") != expected_link:
        log.warning("Payapp webhook linkkey mismatch")
        return {"ok": False, "error": "linkkey mismatch"}

    pay_state = form_data.get("pay_state")  # 4: 완료, 9: 취소, 70~74: 환불 등
    if pay_state == "4":
        emit_payment_completed(
            order_id=form_data.get("var1", ""),
            pg="payapp",
            product_id="core-compass",  # 페이앱은 현재 Core Compass 전용
            amount=int(form_data.get("price", 0)),
            email=form_data.get("buyer", ""),
            raw=dict(form_data),
        )
        return {"ok": True, "state": "completed"}

    if pay_state in ("70", "71", "72", "73", "74"):
        log_payment_event({
            "type": "payapp_refund",
            "order_id": form_data.get("var1"),
            "pay_state": pay_state,
            "raw": dict(form_data),
        })
        return {"ok": True, "state": "refunded"}

    return {"ok": True, "state": f"pay_state={pay_state}"}


# ─────────────────────────────────────────────────────────────────
# 토스페이먼츠 webhook
# ─────────────────────────────────────────────────────────────────

def handle_toss_webhook(body: dict[str, Any], signature: str | None = None) -> dict:
    """토스페이먼츠 webhook.

    가상계좌 입금·결제 취소·정산 알림 등.
    Webhook secret으로 HMAC 검증.
    """
    secret = os.environ.get("TOSS_WEBHOOK_SECRET", "")
    if secret and signature:
        body_str = json.dumps(body, sort_keys=True)
        expected_sig = hmac.new(secret.encode(), body_str.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected_sig, signature):
            log.warning("Toss webhook signature mismatch")
            return {"ok": False, "error": "signature mismatch"}

    event_type = body.get("eventType")
    if event_type == "PAYMENT_STATUS_CHANGED":
        status = body.get("data", {}).get("status")
        if status == "DONE":
            data = body.get("data", {})
            emit_payment_completed(
                order_id=data.get("orderId", ""),
                pg="toss",
                product_id=_extract_product_from_toss_order(data.get("orderId", "")),
                amount=data.get("totalAmount", 0),
                email=data.get("customerEmail", ""),
                raw=body,
            )
            return {"ok": True, "state": "completed"}

    log_payment_event({"type": "toss_webhook", "event": event_type, "raw": body})
    return {"ok": True, "state": event_type}


def _extract_product_from_toss_order(order_id: str) -> str:
    """order_id 포맷: order_{product_id}_{timestamp}"""
    parts = order_id.split("_", 2)
    return parts[1] if len(parts) >= 2 else "unknown"


# ─────────────────────────────────────────────────────────────────
# 스마트스토어 — 직접 webhook 안 받음 (스토어가 자체 처리)
# 회원이 수동으로 스토어 관리자에서 결제 내역 확인 후 진단 생성 트리거
# ─────────────────────────────────────────────────────────────────


if __name__ == "__main__":
    # 테스트
    print("Webhook 모듈 로드 완료.")
    print("페이앱 webhook 예시:")
    test_form = {
        "userid": os.environ.get("PAYAPP_SHOP_ID", "test"),
        "linkkey": os.environ.get("PAYAPP_LINK_KEY", "test"),
        "pay_state": "4",
        "price": "9900",
        "var1": "order_core-compass_123",
        "buyer": "test@example.com",
    }
    print(handle_payapp_webhook(test_form))
