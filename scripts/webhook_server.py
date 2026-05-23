"""결제 webhook 서버 — Flask 기반.

배포 옵션:
1. Vercel Serverless (간단·무료)
2. Render.com 또는 Railway (자체 서버)
3. 회원 Mac mini 로컬 + ngrok 터널 (개발용)

설치:
    pip install flask

실행 (개발):
    FLASK_APP=scripts/webhook_server.py flask run --port 5000

배포 (production):
    gunicorn -w 2 -b 0.0.0.0:5000 scripts.webhook_server:app
"""
from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

try:
    from flask import Flask, request, jsonify
except ImportError:
    print("⚠ Flask 미설치: pip install flask")
    raise

from scripts.payment_webhooks import handle_payapp_webhook, handle_toss_webhook

app = Flask(__name__)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"ok": True, "service": "corecampus-webhook"})


@app.route("/webhook/payapp", methods=["POST"])
def payapp_webhook():
    """페이앱 결제 콜백.

    페이앱이 form-urlencoded POST로 보냄.
    """
    try:
        form_data = request.form.to_dict()
        result = handle_payapp_webhook(form_data)
        log.info("Payapp webhook: %s", result)
        # 페이앱은 plain text "0" 응답을 기대 (성공)
        return ("0", 200)
    except Exception as e:
        log.error("Payapp webhook error: %s", e)
        return ("error", 500)


@app.route("/webhook/toss", methods=["POST"])
def toss_webhook():
    """토스페이먼츠 webhook.

    JSON body + Tosspayments-Signature 헤더.
    """
    try:
        body = request.get_json() or {}
        signature = request.headers.get("Tosspayments-Signature", "")
        result = handle_toss_webhook(body, signature)
        log.info("Toss webhook: %s", result)
        return jsonify(result), 200
    except Exception as e:
        log.error("Toss webhook error: %s", e)
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/payment/payapp/create", methods=["POST"])
def create_payapp_payment():
    """프론트엔드에서 결제 요청 → 페이앱 결제 URL 반환."""
    try:
        data = request.get_json() or {}
        from scripts.payment_router import route_payment
        result = route_payment(
            product_id=data.get("product", "core-compass"),
            amount=data.get("amount", 9900),
            email=data.get("email", ""),
        )
        return jsonify(result), 200 if result.get("ok") else 400
    except Exception as e:
        log.error("Create payment error: %s", e)
        return jsonify({"ok": False, "error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
