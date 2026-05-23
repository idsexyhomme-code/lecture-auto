"""design_qa_agent — HTML 산출물의 design-system 적합성 자동 검증.

룰 기반 (LLM 호출 X — 빠름·결정적).

검사 항목:
1. design-system/base.css 및 components.css import
2. CSS 변수 var(--*) 사용률
3. 하드코딩 컬러 (#RRGGBB) 발견
4. 한글 자간 (letter-spacing 음수) 적용 확인
5. word-break: keep-all 적용 (한글 페이지인 경우)
6. preconnect/preload 폰트 최적화 (랜딩 페이지)

사용:
    from scripts.design_qa import design_qa_review
    result = design_qa_review("path/to/page.html")
    # → {"score": 87, "severity": "warn", "issues": [...], "ok": True}
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any


def design_qa_review(html_path: str | Path) -> dict[str, Any]:
    """HTML 파일 design-system 적합성 검사."""
    path = Path(html_path)
    if not path.exists():
        return {"score": 0, "severity": "fail", "issues": ["file not found"], "ok": False}

    html = path.read_text(encoding="utf-8")
    issues: list[str] = []
    score = 100

    # 1. design-system import 확인
    has_base = "design-system/base.css" in html
    has_components = "design-system/components.css" in html
    if not has_base:
        issues.append("MISS: design-system/base.css not imported")
        score -= 20
    if not has_components:
        issues.append("MISS: design-system/components.css not imported")
        score -= 15

    # 2. CSS 변수 사용 카운트
    var_count = len(re.findall(r"var\(--[\w-]+\)", html))
    if var_count < 5 and (has_base or has_components):
        issues.append(f"LOW: CSS var() 사용 {var_count}건 (5+ 권장)")
        score -= 10

    # 3. 하드코딩 컬러 — style 태그 안 또는 인라인 style 안
    style_blocks = re.findall(r"<style[^>]*>(.+?)</style>", html, re.S)
    inline_styles = re.findall(r'\sstyle="([^"]+)"', html)
    all_style_text = "\n".join(style_blocks) + "\n" + "\n".join(inline_styles)
    hardcoded = re.findall(r"#[0-9a-fA-F]{3,8}\b", all_style_text)
    # 화이트(#fff)·블랙(#000)·CSS 변수 fallback은 OK
    real_hardcoded = [c for c in hardcoded if c.lower() not in ("#fff", "#ffffff", "#000", "#000000")]
    if len(real_hardcoded) > 5:
        issues.append(f"WARN: 하드코딩 컬러 {len(real_hardcoded)}건 — CSS 변수 사용 권장")
        score -= 10

    # 4. 한글 자간 (negative letter-spacing)
    has_neg_letter = bool(re.search(r"letter-spacing:\s*-0\.\d+em", all_style_text))
    if not has_neg_letter and "한글" not in html and re.search(r"[가-힣]", html):
        # 한글 텍스트 있는데 자간 음수 없음
        issues.append("WARN: 한글 페이지인데 letter-spacing 음수 미적용")
        score -= 5

    # 5. word-break keep-all
    has_keep_all = "word-break" in all_style_text and "keep-all" in all_style_text
    if not has_keep_all and re.search(r"[가-힣]", html):
        # base.css가 적용되면 keep-all이 이미 있음 — 미적용은 base.css 없음 의미
        if not has_base:
            issues.append("MISS: 한글 페이지인데 word-break: keep-all 누락 (base.css 없음)")

    # 6. 폰트 최적화 (랜딩 페이지만 — title에 'Core Compass'·'코어 캠퍼스')
    is_landing = bool(re.search(r"<title>.*?(Core Compass|코어 캠퍼스).*?</title>", html))
    has_preconnect = "rel=\"preconnect\"" in html
    has_preload = "rel=\"preload\"" in html and "font" in html.lower()
    if is_landing and not has_preconnect:
        issues.append("HINT: 폰트 preconnect 누락 (TTI 개선)")
        score -= 3
    if is_landing and not has_preload:
        issues.append("HINT: Pretendard preload 누락 (FOIT 줄이기)")
        score -= 3

    # 7. SEO 메타 (랜딩 페이지)
    has_og = "og:title" in html
    has_meta_desc = bool(re.search(r"<meta\s+name=[\"']description[\"']", html))
    if is_landing and not has_og:
        issues.append("WARN: og:title 누락 (소셜 공유 미리보기)")
        score -= 5
    if not has_meta_desc:
        issues.append("WARN: meta description 누락 (SEO)")
        score -= 5

    score = max(0, min(100, score))
    severity = "pass" if score >= 85 else "warn" if score >= 60 else "fail"

    return {
        "path": str(path),
        "score": score,
        "severity": severity,
        "ok": severity != "fail",
        "checks": {
            "has_base_css": has_base,
            "has_components_css": has_components,
            "var_count": var_count,
            "hardcoded_count": len(real_hardcoded),
            "has_neg_letter_spacing": has_neg_letter,
            "has_word_break_keep_all": has_keep_all,
            "has_preconnect": has_preconnect,
            "has_preload": has_preload,
            "has_og": has_og,
            "has_meta_desc": has_meta_desc,
        },
        "issues": issues,
    }


def batch_review(glob_pattern: str) -> list[dict]:
    """여러 페이지 일괄 검수."""
    import glob
    results = []
    for p in sorted(glob.glob(glob_pattern, recursive=True)):
        results.append(design_qa_review(p))
    return results


if __name__ == "__main__":
    import sys
    import json
    if len(sys.argv) > 1:
        pattern = sys.argv[1]
        if "*" in pattern:
            results = batch_review(pattern)
            print(f"검수: {len(results)} 페이지")
            for r in results:
                status = "✓" if r["severity"] == "pass" else "⚠" if r["severity"] == "warn" else "✗"
                name = Path(r["path"]).name
                print(f"  {status} {name:40s} score={r['score']:3d} {r['severity']:5s} ({len(r['issues'])} issues)")
            # 종합
            passed = sum(1 for r in results if r["severity"] == "pass")
            print(f"\n통과: {passed}/{len(results)}")
        else:
            r = design_qa_review(pattern)
            print(json.dumps(r, indent=2, ensure_ascii=False))
    else:
        print("Usage: python design_qa.py <html_path_or_glob>")
