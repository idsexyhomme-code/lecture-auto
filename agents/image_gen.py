"""Image generation — gpt-image-2 (블로그·카드뉴스 hero 이미지).

저장:
    site/blog-images/{slug}.png        — 블로그 메인용
    site/card-news/{course_id}/01.png  — 카드뉴스용

GitHub Pages 호스팅 → URL 형식:
    https://{owner}.github.io/{repo}/blog-images/{slug}.png

CLI:
    python -m agents.image_gen test
"""
from __future__ import annotations

import base64
import logging
import os
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.base import REPO_ROOT

try:
    from dotenv import load_dotenv
    load_dotenv(REPO_ROOT / ".env")
except ImportError:
    pass

log = logging.getLogger("image_gen")

SITE_IMAGES_DIR = REPO_ROOT / "site" / "blog-images"
SITE_IMAGES_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_IMAGE_MODEL = os.environ.get("OPENAI_IMAGE_MODEL", "gpt-image-1")
DEFAULT_QUALITY = os.environ.get("BLOG_IMAGE_QUALITY", "high")  # 회원 결정: 비용 OK·고품질


def _pages_base_url() -> str:
    """이미지 호스팅 베이스 URL — raw.githubusercontent.com.

    Pages 빌드 기다릴 필요 없음 → push 즉시 라이브.
    URL 형식: https://raw.githubusercontent.com/{owner}/{repo}/main/site
    """
    repo = os.environ.get("GITHUB_REPOSITORY") or "idsexyhomme-code/lecture-auto"
    if "/" not in repo:
        return ""
    branch = os.environ.get("GITHUB_BRANCH", "main")
    return f"https://raw.githubusercontent.com/{repo}/{branch}/site"


def _save_and_url(img_bytes: bytes, slug: str, save_dir: Optional[Path]) -> tuple[Path, str]:
    """이미지 바이트 → 파일 저장 + public URL 반환."""
    target_dir = save_dir or SITE_IMAGES_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    save_path = target_dir / f"{slug}.png"
    save_path.write_bytes(img_bytes)
    rel_path = save_path.relative_to(REPO_ROOT / "site")
    public_url = f"{_pages_base_url()}/{rel_path.as_posix()}"
    log.info("[image] ✓ %s (%d bytes)", save_path.name, save_path.stat().st_size)
    return save_path, public_url


def _generate_image_openai(
    prompt: str, slug: str, size: str, quality: str, save_dir: Optional[Path]
) -> tuple[Path, str]:
    """OpenAI gpt-image-1로 생성. (DEFAULT_IMAGE_MODEL=gpt-image-1, quality=high)"""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY 없음")

    from openai import OpenAI
    log.info("[image] openai generating: %s / %s / %s", prompt[:60], size, quality)
    client = OpenAI(api_key=api_key)

    model = DEFAULT_IMAGE_MODEL
    try:
        resp = client.images.generate(model=model, prompt=prompt, n=1, size=size, quality=quality)
    except Exception as e:
        if "gpt-image-2" in str(e):
            log.warning("[image] gpt-image-2 unavailable — fallback gpt-image-1")
            resp = client.images.generate(
                model="gpt-image-1", prompt=prompt, n=1, size=size, quality=quality,
            )
        else:
            raise

    b64 = resp.data[0].b64_json
    if not b64:
        raise RuntimeError("OpenAI 응답에 b64_json 없음")
    return _save_and_url(base64.b64decode(b64), slug, save_dir)


def _generate_image_gemini(
    prompt: str, slug: str, save_dir: Optional[Path]
) -> tuple[Path, str]:
    """Gemini 2.5 Flash Image (나노바나나)로 생성.

    회원의 GOOGLE_GENERATIVEAI_API_KEY 사용. REST API 직접 호출 (SDK 의존성 없음).
    """
    api_key = os.environ.get("GOOGLE_GENERATIVEAI_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_GENERATIVEAI_API_KEY 없음")

    import requests

    # 환경변수에 회원이 명시한 모델이 있으면 그것만, 없으면 폴백 체인 시도.
    custom = os.environ.get("GEMINI_IMAGE_MODEL")
    if custom:
        candidate_models = [custom]
    else:
        candidate_models = [
            "gemini-2.5-flash-image",
            "gemini-2.5-flash-image-preview",
            "gemini-2.0-flash-exp-image-generation",
        ]

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]},
    }
    log.info("[image] gemini generating: %s", prompt[:60])

    r = None
    last_err = ""
    for model in candidate_models:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent?key={api_key}"
        )
        log.info("[image] try model: %s", model)
        r = requests.post(url, json=payload, timeout=90)
        if r.status_code == 200:
            break
        last_err = f"{model} → {r.status_code} {r.text[:200]}"
        log.warning("[image] %s", last_err)
        # 404/NOT_FOUND만 다음 모델 시도. 다른 에러(quota 등)는 즉시 중단.
        if r.status_code != 404:
            break

    if r is None or r.status_code != 200:
        raise RuntimeError(
            f"Gemini API 호출 실패. 마지막: {last_err}\n"
            f"진단: list-gemini-models.command 더블클릭하여 사용 가능 모델 확인"
        )

    data = r.json()
    candidates = data.get("candidates") or []
    if not candidates:
        raise RuntimeError(f"Gemini no candidates: {str(data)[:300]}")

    parts = (candidates[0].get("content") or {}).get("parts") or []
    img_b64: Optional[str] = None
    for part in parts:
        inline = part.get("inlineData") or part.get("inline_data") or {}
        if inline.get("data"):
            img_b64 = inline["data"]
            break

    if not img_b64:
        raise RuntimeError(f"Gemini no image data: {str(data)[:300]}")

    return _save_and_url(base64.b64decode(img_b64), slug, save_dir)


def generate_blog_image(
    prompt: str,
    slug: str,
    *,
    size: str = "1536x1024",   # 가로형 (OpenAI에서만 사용 — Gemini는 자동)
    quality: str = DEFAULT_QUALITY,
    save_dir: Optional[Path] = None,
) -> tuple[Path, str]:
    """블로그 메인 이미지 1장 생성 — BLOG_IMAGE_MODEL 환경변수로 백엔드 분기.

    BLOG_IMAGE_MODEL=gemini (기본) → Gemini 2.5 Flash Image (나노바나나)
    BLOG_IMAGE_MODEL=openai → OpenAI gpt-image-1 (회원 결제 한도 영향)

    Returns: (로컬 파일 경로, GitHub Pages URL)
    """
    backend = os.environ.get("BLOG_IMAGE_MODEL", "gemini").lower()
    if backend == "openai":
        return _generate_image_openai(prompt, slug, size, quality, save_dir)
    return _generate_image_gemini(prompt, slug, save_dir)


def _cli_test():
    prompt = (
        "Editorial magazine cover for Korean online learning platform 'Core Campus'. "
        "Warm beige and dark brown palette, minimalist composition, "
        "abstract geometric shapes representing knowledge and growth. "
        "No Korean text in image (text rendering inconsistent). "
        "Quiet, intellectual atmosphere."
    )
    print(f"테스트: {prompt[:80]}...")
    path, url = generate_blog_image(prompt, "test-blog-hero")
    print(f"\n✓ 저장: {path}")
    print(f"✓ URL: {url}")
    print(f"\n로컬 열기: open '{path}'")


if __name__ == "__main__":
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s [%(name)s] %(message)s",
    )
    _cli_test()
