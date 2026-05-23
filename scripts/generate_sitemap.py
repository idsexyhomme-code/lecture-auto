#!/usr/bin/env python3
"""sitemap.xml + robots.txt 자동 생성.

사이트 모든 public 페이지를 발견해서 sitemap.xml에 등재.
private 페이지 (admin·_backups·_design_previews·v2)는 제외.
"""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
SITE_DIR = ROOT / "site"
BASE_URL = os.environ.get("SITE_BASE_URL", "https://corecampus.kr")

# 제외 패턴
EXCLUDE_DIRS = {"_backups", "_design_previews", "admin", "v2", "courses-v2", "_pycache_"}
EXCLUDE_PREFIX = ("_", ".")


def discover_pages() -> list[dict]:
    """모든 *.html 발견."""
    pages = []
    for p in sorted(SITE_DIR.rglob("*.html")):
        # 제외 디렉토리
        if any(d in p.parts for d in EXCLUDE_DIRS):
            continue
        # 점·언더바 시작 폴더
        if any(part.startswith(EXCLUDE_PREFIX) for part in p.relative_to(SITE_DIR).parts):
            continue
        # 개인 URL (r/{token}/)
        if "/r/" in str(p):
            continue
        # checkout / success / expired — 공개 인덱싱 X
        if any(x in p.name for x in ("checkout", "404", "expired", "success")):
            continue

        rel = p.relative_to(SITE_DIR)
        url = BASE_URL + "/" + str(rel).replace(os.sep, "/")
        mtime = datetime.fromtimestamp(p.stat().st_mtime)
        pages.append({
            "url": url,
            "lastmod": mtime.strftime("%Y-%m-%d"),
            "priority": _priority(p),
        })
    return pages


def _priority(p: Path) -> str:
    """페이지별 우선순위."""
    if p.name == "index.html" and p.parent == SITE_DIR:
        return "1.0"  # 메인
    if "courses" in p.parts:
        return "0.9"
    if "landing" in p.parts:
        return "0.9"
    if "posts" in p.parts or "blog" in p.parts:
        return "0.7"
    return "0.5"


def build_sitemap(pages: list[dict]) -> str:
    """sitemap.xml 빌드."""
    lines = ['<?xml version="1.0" encoding="UTF-8"?>']
    lines.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
    for p in pages:
        lines.append("  <url>")
        lines.append(f"    <loc>{p['url']}</loc>")
        lines.append(f"    <lastmod>{p['lastmod']}</lastmod>")
        lines.append(f"    <priority>{p['priority']}</priority>")
        lines.append("  </url>")
    lines.append("</urlset>")
    return "\n".join(lines)


def build_robots() -> str:
    return f"""User-agent: *
Allow: /
Disallow: /site/admin/
Disallow: /site/_backups/
Disallow: /site/_design_previews/
Disallow: /site/landing/core-compass/r/
Disallow: /site/landing/core-compass/v3/checkout-payapp.html
Disallow: /site/landing/checkout-toss/
Disallow: /site/landing/core-compass/v3/result.html
Disallow: /site/landing/core-compass/v3/expired.html
Disallow: /site/landing/core-compass/v3/success.html

Sitemap: {BASE_URL}/site/sitemap.xml
"""


def main():
    pages = discover_pages()
    print(f"발견: {len(pages)} 페이지")

    sitemap_path = SITE_DIR / "sitemap.xml"
    sitemap_path.write_text(build_sitemap(pages), encoding="utf-8")
    print(f"✓ {sitemap_path}")

    robots_path = SITE_DIR / "robots.txt"
    robots_path.write_text(build_robots(), encoding="utf-8")
    print(f"✓ {robots_path}")

    print(f"\n샘플 (TOP 10):")
    for p in pages[:10]:
        print(f"  {p['priority']}  {p['lastmod']}  {p['url']}")


if __name__ == "__main__":
    main()
