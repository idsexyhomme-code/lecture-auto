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

DEFAULT_IMAGE_MODEL = os.environ.get("OPENAI_IMAGE_MODEL", "gpt-image-2")


def _pages_base_url() -> str:
    """GitHub Pages 베이스 URL."""
    repo = os.environ.get("GITHUB_REPOSITORY") or "idsexyhomme-code/lecture-auto"
    if "/" not in repo:
        return ""
    owner, name = repo.split("/", 1)
    return f"https://{owner.lower()}.github.io/{name}"


def generate_blog_image(
    prompt: str,
    slug: str,
    *,
    size: str = "1536x1024",   # 가로형 (블로그 메인)
    quality: str = "medium",   # medium = ~$0.04, high = ~$0.17
    save_dir: Optional[Path] = None,
) -> tuple[Path, str]:
    """gpt-image-2로 블로그 메인 이미지 1장 생성.

    Returns: (로컬 파일 경로, GitHub Pages URL)
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY 없음")

    from openai import OpenAI

    log.info("[image] generating: %s / %s / %s", prompt[:60], size, quality)
    client = OpenAI(api_key=api_key)

    model = DEFAULT_IMAGE_MODEL
    try:
        resp = client.images.generate(
            model=model, prompt=prompt, n=1, size=size, quality=quality,
        )
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
        raise RuntimeError("이미지 응답에 b64_json 없음")

    img_bytes = base64.b64decode(b64)
    target_dir = save_dir or SITE_IMAGES_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    save_path = target_dir / f"{slug}.png"
    save_path.write_bytes(img_bytes)

    # GitHub Pages URL — 사이트 루트 기준 상대 경로
    rel_path = save_path.relative_to(REPO_ROOT / "site")
    public_url = f"{_pages_base_url()}/{rel_path.as_posix()}"

    log.info("[image] ✓ %s (%d bytes)", save_path.name, save_path.stat().st_size)
    log.info("[image]   URL: %s", public_url)
    return save_path, public_url


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
