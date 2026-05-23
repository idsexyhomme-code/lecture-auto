"""Supabase 기반 회원 관리.

회원 가입·로그인·세션·진단 기록 연결.

회원이 SUPABASE_URL·SUPABASE_SERVICE_KEY 입력 후 동작.
"""
from __future__ import annotations

import json
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

log = logging.getLogger(__name__)
KST = timezone(timedelta(hours=9))

ROOT = Path(__file__).parent.parent

# Fallback — Supabase 미설치 시 로컬 JSON 사용 (개발용)
LOCAL_USERS = ROOT / "content/state/users_local.jsonl"


def _get_supabase():
    """Supabase 클라이언트 반환. 미설치 시 None."""
    try:
        from supabase import create_client
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_KEY")
        if not (url and key):
            return None
        return create_client(url, key)
    except ImportError:
        return None


def get_or_create_user(
    *,
    email: str,
    name: str = "",
    oauth_provider: str = "email",
    oauth_id: str | None = None,
) -> dict:
    """사용자 가입 또는 조회.

    Returns:
        user dict with id, email, name, created_at
    """
    sb = _get_supabase()
    if sb:
        try:
            result = sb.table('users').upsert({
                'email': email,
                'name': name,
                'oauth_provider': oauth_provider,
                'oauth_id': oauth_id,
            }, on_conflict='email').execute()
            return result.data[0] if result.data else {}
        except Exception as e:
            log.error("Supabase upsert error: %s", e)

    # Fallback — 로컬 JSON
    LOCAL_USERS.parent.mkdir(parents=True, exist_ok=True)
    user_id = secrets.token_hex(16)
    now = datetime.now(KST).isoformat()
    user = {
        "id": user_id,
        "email": email,
        "name": name,
        "oauth_provider": oauth_provider,
        "oauth_id": oauth_id,
        "created_at": now,
    }
    with open(LOCAL_USERS, "a", encoding="utf-8") as f:
        f.write(json.dumps(user, ensure_ascii=False) + "\n")
    return user


def get_user_by_email(email: str) -> dict | None:
    """이메일로 사용자 조회."""
    sb = _get_supabase()
    if sb:
        try:
            result = sb.table('users').select('*').eq('email', email).limit(1).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            log.error("Supabase query error: %s", e)

    # Fallback
    if not LOCAL_USERS.exists():
        return None
    with open(LOCAL_USERS, encoding="utf-8") as f:
        for line in f:
            try:
                u = json.loads(line)
                if u.get("email") == email:
                    return u
            except Exception:
                continue
    return None


def link_compass_to_user(*, user_id: str, order_id: str, result_url: str, one_line_insight: str, user_persona: str = "") -> bool:
    """진단 기록을 회원에 연결."""
    sb = _get_supabase()
    if sb:
        try:
            sb.table('compass_reports').insert({
                'user_id': user_id,
                'order_id': order_id,
                'result_url': result_url,
                'one_line_insight': one_line_insight,
                'user_persona': user_persona,
            }).execute()
            return True
        except Exception as e:
            log.error("Supabase compass link error: %s", e)
    # Fallback — JSON 추가
    log_path = ROOT / "content/state/compass_reports_local.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps({
            "user_id": user_id,
            "order_id": order_id,
            "result_url": result_url,
            "one_line_insight": one_line_insight,
            "user_persona": user_persona,
            "created_at": datetime.now(KST).isoformat(),
        }, ensure_ascii=False) + "\n")
    return True


def list_user_compass_reports(user_id: str) -> list[dict]:
    """회원의 모든 진단 기록 조회."""
    sb = _get_supabase()
    if sb:
        try:
            result = sb.table('compass_reports').select('*').eq('user_id', user_id).execute()
            return result.data or []
        except Exception as e:
            log.error("Supabase query error: %s", e)

    # Fallback
    log_path = ROOT / "content/state/compass_reports_local.jsonl"
    if not log_path.exists():
        return []
    out = []
    with open(log_path, encoding="utf-8") as f:
        for line in f:
            try:
                rec = json.loads(line)
                if rec.get("user_id") == user_id:
                    out.append(rec)
            except Exception:
                continue
    return out


if __name__ == "__main__":
    # 테스트 — fallback (Supabase 미설정)
    print("=== auth.py 테스트 ===")
    u = get_or_create_user(email="test@example.com", name="테스트")
    print(f"User: {u['email']} (id={u['id']})")
    print()
    u2 = get_user_by_email("test@example.com")
    print(f"Found: {u2['name'] if u2 else 'None'}")
    print()
    print("Supabase active:", _get_supabase() is not None)
