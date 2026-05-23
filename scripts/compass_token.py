"""Core Compass 개인 URL 토큰 발급·검증.

토큰: 32자 hex (secrets 기반)
저장: content/state/compass_tokens.jsonl

각 토큰:
- order_id: 결제 주문 ID
- email: 사용자 이메일
- created_at: ISO timestamp
- expires_at: ISO timestamp (created_at + 24h)
- used_count: 열람 횟수
"""
from __future__ import annotations

import json
import secrets
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent
STATE = ROOT / "content/state"
TOKENS_FILE = STATE / "compass_tokens.jsonl"

KST = timezone(timedelta(hours=9))


def generate_token(*, order_id: str, email: str, expire_hours: int = 24) -> dict:
    """새 토큰 발급."""
    STATE.mkdir(parents=True, exist_ok=True)
    token = secrets.token_hex(16)  # 32자 hex
    now = datetime.now(KST)
    expires = now + timedelta(hours=expire_hours)
    record = {
        "token": token,
        "order_id": order_id,
        "email": email,
        "created_at": now.isoformat(),
        "expires_at": expires.isoformat(),
        "used_count": 0,
    }
    with open(TOKENS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def verify_token(token: str) -> dict | None:
    """토큰 검증. 만료 시 None."""
    if not TOKENS_FILE.exists():
        return None
    now = datetime.now(KST)
    with open(TOKENS_FILE, encoding="utf-8") as f:
        for line in f:
            try:
                rec = json.loads(line)
            except Exception:
                continue
            if rec.get("token") != token:
                continue
            # 만료 체크
            try:
                expires = datetime.fromisoformat(rec["expires_at"])
                if now > expires:
                    return None  # 만료
            except Exception:
                continue
            # 열람 횟수 증가 (실제로는 별도 update 필요 — 이 함수는 read-only)
            return rec
    return None


def cleanup_expired() -> int:
    """만료된 토큰 정리. expired_count 반환."""
    if not TOKENS_FILE.exists():
        return 0
    now = datetime.now(KST)
    keep = []
    expired = 0
    with open(TOKENS_FILE, encoding="utf-8") as f:
        for line in f:
            try:
                rec = json.loads(line)
            except Exception:
                continue
            try:
                exp = datetime.fromisoformat(rec["expires_at"])
                if now > exp:
                    expired += 1
                    continue
            except Exception:
                pass
            keep.append(rec)
    # 다시 쓰기
    with open(TOKENS_FILE, "w", encoding="utf-8") as f:
        for rec in keep:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return expired


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "cleanup":
        n = cleanup_expired()
        print(f"Cleaned up {n} expired tokens.")
    else:
        # 테스트 발급
        rec = generate_token(order_id="test_order", email="test@example.com")
        print(json.dumps(rec, indent=2, ensure_ascii=False))
