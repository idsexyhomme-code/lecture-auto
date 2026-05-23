#!/usr/bin/env python3
"""사이트 빌드 자동 검증.

모든 페이지의:
- 깨진 링크 (href·src) 검증 (정적 분석)
- design_qa score 점검
- 카피 ban (self_review) 점검

사용: python scripts/smoke_test_site.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from agents.base import BaseAgent
from scripts.design_qa import design_qa_review


def check_links(html: str, base_path: Path) -> list[str]:
    """깨진 상대 링크 검출."""
    issues = []
    # href·src 추출
    matches = re.findall(r'(href|src)=["\']([^"\']+)["\']', html)
    for attr, link in matches:
        if link.startswith(("http://", "https://", "//", "mailto:", "tel:", "#", "data:", "javascript:")):
            continue
        if link.startswith("/"):
            # 절대 경로 — 사이트 루트 기준
            target = ROOT / "site" / link[1:].split("?")[0].split("#")[0]
        else:
            target = (base_path.parent / link).resolve()
            target = target.with_name(target.name.split("?")[0].split("#")[0])
        # 상위 디렉토리 escape는 안전성 검사 X
        if not target.exists():
            issues.append(f"BROKEN: {attr}={link}")
    return issues


def check_one(path: Path) -> dict:
    """1 페이지 종합 검사."""
    html = path.read_text(encoding="utf-8", errors="ignore")

    # 1. self_review (카피)
    text = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.S)
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.S)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    sr = BaseAgent.self_review(text, kind="copy")

    # 2. design_qa
    qa = design_qa_review(path)

    # 3. links
    broken = check_links(html, path)

    return {
        "path": str(path),
        "self_review": sr["severity"],
        "design_qa_score": qa["score"],
        "design_qa": qa["severity"],
        "broken_links": broken,
        "issues": qa["issues"],
    }


def main():
    targets = []
    # 검사 대상
    for pattern in [
        "site/courses-v2/*.html",
        "site/v2/*.html",
        "site/landing/core-compass/v3/*.html",
        "design-system/preview/*.html",
    ]:
        targets.extend(sorted(ROOT.glob(pattern)))

    print(f"smoke test: {len(targets)} 페이지\n")

    summary = {"pass": 0, "warn": 0, "fail": 0, "broken_links_total": 0}

    for p in targets:
        r = check_one(p)
        sr = r["self_review"]
        qa = r["design_qa"]
        broken = len(r["broken_links"])
        summary["broken_links_total"] += broken

        worst = "pass" if sr == "pass" and qa == "pass" and broken == 0 else \
                ("fail" if sr == "fail" or qa == "fail" else "warn")
        summary[worst] += 1

        icon = "✓" if worst == "pass" else "⚠" if worst == "warn" else "✗"
        name = str(p.relative_to(ROOT))[:60]
        print(f"  {icon} {name:60s} sr={sr:5s} qa={r['design_qa_score']:3d} links={broken}")

    print(f"\n총 {sum([summary['pass'], summary['warn'], summary['fail']])} 페이지")
    print(f"  ✓ pass: {summary['pass']}")
    print(f"  ⚠ warn: {summary['warn']}")
    print(f"  ✗ fail: {summary['fail']}")
    print(f"  깨진 링크 합계: {summary['broken_links_total']}")
    return summary["fail"] == 0


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
