"""Instagram Graph API wrapper — Core Campus.

[자율 결정 — 2026-05-15]
회원이 Instagram Graph API 토큰 심사 통과까지 1~2주 소요.
어댑터 코드는 *지금* 깔아두고, DRY_RUN=true 모드로 미리 검증.
.env에 토큰 추가되면 자동으로 실제 발행.

[필요한 환경변수]
- INSTAGRAM_ACCESS_TOKEN
- INSTAGRAM_BUSINESS_ACCOUNT_ID
- DRY_RUN=true (기본 — 토큰 없을 때 안전)

[API 흐름]
1. 미디어 컨테이너 생성 (POST /{ig-user-id}/media)
2. 컨테이너 게시 (POST /{ig-user-id}/media_publish)
3. (옵션) 토큰 7일 전 자동 갱신 (long-lived → 60일)
"""
from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

log = logging.getLogger("instagram_client")

API_BASE = "https://graph.facebook.com/v18.0"
REPO_ROOT = Path(__file__).resolve().parent.parent
PUB_LOG = REPO_ROOT / "content" / "state" / "instagram_publications.jsonl"
PUB_LOG.parent.mkdir(parents=True, exist_ok=True)
KST = timezone(timedelta(hours=9))


def is_dry_run() -> bool:
    """전역 DRY_RUN 또는 Instagram 특정 SKIP."""
    return (
        os.environ.get("DRY_RUN", "").lower() in ("1", "true", "yes")
        or os.environ.get("INSTAGRAM_SKIP", "").lower() in ("1", "true", "yes")
        or not os.environ.get("INSTAGRAM_ACCESS_TOKEN")
    )


def _log_publication(entry: dict):
    """발행 결과 JSONL 누적."""
    entry["ts"] = datetime.now(KST).isoformat()
    with PUB_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=4, max=30))
def _post(url: str, params: dict) -> dict:
    r = requests.post(url, params=params, timeout=30)
    if r.status_code >= 400:
        log.warning("[ig] HTTP %d — %s", r.status_code, r.text[:200])
        r.raise_for_status()
    return r.json()


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=4, max=30))
def _get(url: str, params: dict) -> dict:
    r = requests.get(url, params=params, timeout=30)
    if r.status_code >= 400:
        log.warning("[ig] HTTP %d — %s", r.status_code, r.text[:200])
        r.raise_for_status()
    return r.json()


def create_media_container(
    image_url: str,
    caption: str,
    *,
    business_account_id: Optional[str] = None,
    access_token: Optional[str] = None,
) -> Optional[str]:
    """1단계: 미디어 컨테이너 생성. container_id 반환.

    Args:
        image_url: 공개 접근 가능 이미지 URL (GitHub raw 가능)
        caption: 본문 (해시태그 포함, ≤2200자)
    """
    if is_dry_run():
        fake_id = f"dryrun-container-{int(time.time())}"
        log.info("[ig DRY_RUN] create_media_container → %s", fake_id)
        _log_publication({
            "mode": "DRY_RUN",
            "step": "create_container",
            "image_url": image_url,
            "caption_len": len(caption),
            "fake_id": fake_id,
        })
        return fake_id

    business_account_id = business_account_id or os.environ["INSTAGRAM_BUSINESS_ACCOUNT_ID"]
    access_token = access_token or os.environ["INSTAGRAM_ACCESS_TOKEN"]
    url = f"{API_BASE}/{business_account_id}/media"
    params = {
        "image_url": image_url,
        "caption": caption,
        "access_token": access_token,
    }
    result = _post(url, params)
    container_id = result.get("id")
    log.info("[ig] container 생성: %s", container_id)
    return container_id


def publish_media(
    container_id: str,
    *,
    business_account_id: Optional[str] = None,
    access_token: Optional[str] = None,
) -> Optional[str]:
    """2단계: 미디어 게시. published_post_id 반환."""
    if is_dry_run():
        fake_post = f"dryrun-post-{int(time.time())}"
        log.info("[ig DRY_RUN] publish_media(%s) → %s", container_id, fake_post)
        _log_publication({
            "mode": "DRY_RUN",
            "step": "publish",
            "container_id": container_id,
            "fake_post_id": fake_post,
        })
        return fake_post

    business_account_id = business_account_id or os.environ["INSTAGRAM_BUSINESS_ACCOUNT_ID"]
    access_token = access_token or os.environ["INSTAGRAM_ACCESS_TOKEN"]
    url = f"{API_BASE}/{business_account_id}/media_publish"
    params = {"creation_id": container_id, "access_token": access_token}
    result = _post(url, params)
    post_id = result.get("id")
    log.info("[ig] 발행 성공: %s", post_id)
    _log_publication({
        "mode": "LIVE",
        "step": "publish",
        "container_id": container_id,
        "post_id": post_id,
    })
    return post_id


def publish_post(image_url: str, caption: str) -> Optional[str]:
    """원샷 발행 — container 생성 + 게시 2단계 합침."""
    container = create_media_container(image_url, caption)
    if not container:
        return None
    # 컨테이너 처리 대기 (실제 API에서는 status_code=FINISHED까지)
    if not is_dry_run():
        time.sleep(5)
    return publish_media(container)


def refresh_token() -> Optional[str]:
    """long-lived 토큰 갱신 (60일 → 60일). 만료 7일 전 자동 호출 권장."""
    if is_dry_run():
        log.info("[ig DRY_RUN] refresh_token → 가짜 토큰")
        return "dryrun-refreshed-token"

    access_token = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
    if not access_token:
        log.warning("[ig] INSTAGRAM_ACCESS_TOKEN 없음 — 갱신 불가")
        return None
    url = f"{API_BASE}/refresh_access_token"
    params = {"grant_type": "ig_refresh_token", "access_token": access_token}
    result = _get(url, params)
    new_token = result.get("access_token")
    if new_token:
        log.info("[ig] 토큰 갱신 성공 (만료 in %d초)", result.get("expires_in", 0))
        # .env 자동 업데이트는 보안상 안 함. 회원이 직접 갱신.
    return new_token
