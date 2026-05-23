"""사이트 스냅샷 — 빌드 후 메인 페이지 스크린샷 + Lighthouse 점수.

Phase 1.2 — site_config_change·design_variants 승인 → 빌드 → 스냅샷 → 텔레그램 전송.

지원:
- Playwright (기본) — chromium headless로 site/index.html 또는 라이브 URL 캡처
- Lighthouse CLI (선택) — `npx lighthouse` 있으면 점수 측정
- Both gracefully degrade — 도구 없으면 그 단계만 건너뜀

설계 원칙:
- 빌드 직후 실행되므로 절대 빌드 결과를 막지 않음 — 예외 다 swallow
- 결과는 텔레그램 카드로 즉시 전송
- 비교용으로 변경 전/후 capture는 별도 호출에서 처리
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SITE_DIR = REPO_ROOT / "site"
SNAPSHOT_DIR = REPO_ROOT / "content" / "state" / "snapshots"

# .env 자동 로드 — 텔레그램·라이브 URL 등 환경변수가 빈 상태로 시작하지 않도록
try:
    from dotenv import load_dotenv
    load_dotenv(REPO_ROOT / ".env")
except ImportError:
    pass

log = logging.getLogger("site_snapshot")

# 라이브 사이트 URL (GitHub Pages)
LIVE_BASE = os.environ.get("SITE_LIVE_URL", "https://idsexyhomme-code.github.io/lecture-auto")

# 캡처 대상 페이지
# Note: 코스 인덱스는 site_builder 버전에 따라 /courses/ 또는 /courses-v2/ 가능
# capture_pages가 fallback 자동 탐색
DEFAULT_TARGETS = [
    ("home", "/", "메인"),
    ("courses_index", "/courses-v2/", "코스 목록"),
]

# courses_index가 없을 때 시도할 대안 경로
COURSES_INDEX_FALLBACKS = [
    "/courses-v2/index.html",
    "/courses/index.html",
    "/courses-v2/",
    "/courses/",
]

VIEWPORT_DESKTOP = {"width": 1440, "height": 900}
VIEWPORT_MOBILE = {"width": 390, "height": 844}  # iPhone 13


def _resolve_local_path(url_path: str, slug: str) -> Path | None:
    """url_path를 site/ 폴더 안 실제 .html 파일 경로로 변환.

    빌드 버전에 따라 /courses/, /courses-v2/ 등 다를 수 있으므로 자동 fallback.
    """
    def _try(p: str) -> Path | None:
        candidate = SITE_DIR / p.lstrip("/")
        if candidate.is_file():
            return candidate
        if candidate.is_dir():
            idx = candidate / "index.html"
            if idx.is_file():
                return idx
        if not str(candidate).endswith(".html"):
            html_variant = candidate.with_suffix(".html")
            if html_variant.is_file():
                return html_variant
        return None

    # 1차: 그대로
    found = _try(url_path)
    if found:
        return found

    # 2차: courses_index 슬러그에 fallback 적용
    if slug == "courses_index":
        for alt in COURSES_INDEX_FALLBACKS:
            found = _try(alt)
            if found:
                log.info("[snapshot] courses_index fallback hit: %s", alt)
                return found

    return None


def capture_pages(targets: list[tuple[str, str, str]] | None = None,
                  *,
                  use_live: bool = True,
                  full_page: bool = True,
                  mobile: bool = False) -> dict:
    """페이지를 스크린샷.

    Args:
        targets: [(slug, url_path, label), ...] — None이면 DEFAULT_TARGETS
        use_live: True면 LIVE_BASE 사용, False면 로컬 file:// + site/
        full_page: True면 페이지 전체 (스크롤), False면 viewport만
        mobile: True면 mobile viewport

    Returns:
        {"ok": bool, "paths": [Path, ...], "errors": [str, ...], "method": str}
    """
    if targets is None:
        targets = DEFAULT_TARGETS

    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d-%H%M%S")
    out_paths: list[Path] = []
    errors: list[str] = []

    # Playwright 시도
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {
            "ok": False,
            "paths": [],
            "errors": ["playwright 미설치 — pip install playwright && playwright install chromium"],
            "method": "none",
        }

    viewport = VIEWPORT_MOBILE if mobile else VIEWPORT_DESKTOP
    device_label = "mobile" if mobile else "desktop"

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport=viewport, device_scale_factor=2)
            page = context.new_page()

            for slug, url_path, label in targets:
                try:
                    if use_live:
                        url = f"{LIVE_BASE.rstrip('/')}{url_path}"
                    else:
                        # 로컬 file:// — 경로 자동 fallback 처리
                        local = _resolve_local_path(url_path, slug)
                        if local is None:
                            errors.append(f"{slug}: 파일 없음 (시도한 경로 모두 실패)")
                            continue
                        url = f"file://{local.as_posix()}"

                    page.goto(url, wait_until="networkidle", timeout=30000)
                    # 폰트 로드 대기
                    page.wait_for_timeout(800)

                    out = SNAPSHOT_DIR / f"{ts}-{slug}-{device_label}.png"
                    page.screenshot(path=str(out), full_page=full_page)
                    out_paths.append(out)
                    log.info("[snapshot] ✓ %s → %s", slug, out.name)
                except Exception as e:
                    errors.append(f"{slug}: {type(e).__name__}: {e}")
                    log.warning("[snapshot] ❌ %s: %s", slug, e)

            browser.close()
    except Exception as e:
        return {
            "ok": False,
            "paths": [],
            "errors": [f"playwright launch failed: {e}"],
            "method": "playwright",
        }

    return {
        "ok": bool(out_paths),
        "paths": out_paths,
        "errors": errors,
        "method": "playwright",
        "viewport": device_label,
    }


def lighthouse_score(url: str | None = None, timeout: int = 90) -> dict:
    """Lighthouse CLI로 점수 측정. lighthouse 없으면 graceful skip.

    Returns:
        {"ok": bool, "scores": {performance, accessibility, best-practices, seo, pwa},
         "error": str | None}
    """
    if not shutil.which("npx") and not shutil.which("lighthouse"):
        return {"ok": False, "scores": {}, "error": "npx/lighthouse 미설치 (skip)"}

    target = url or LIVE_BASE
    out_json = REPO_ROOT / "content" / "state" / "lighthouse_last.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "npx", "--yes", "lighthouse", target,
        "--quiet",
        "--chrome-flags=--headless --no-sandbox",
        "--output=json",
        f"--output-path={out_json}",
        "--only-categories=performance,accessibility,best-practices,seo",
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if proc.returncode != 0:
            return {
                "ok": False, "scores": {},
                "error": f"lighthouse exit {proc.returncode}: {proc.stderr[-200:]}",
            }
    except subprocess.TimeoutExpired:
        return {"ok": False, "scores": {}, "error": f"lighthouse timeout {timeout}s"}
    except Exception as e:
        return {"ok": False, "scores": {}, "error": f"{type(e).__name__}: {e}"}

    try:
        data = json.loads(out_json.read_text(encoding="utf-8"))
        cats = data.get("categories", {})
        scores = {
            k: int(round((cats.get(k, {}).get("score") or 0) * 100))
            for k in ("performance", "accessibility", "best-practices", "seo")
        }
        return {"ok": True, "scores": scores, "error": None}
    except Exception as e:
        return {"ok": False, "scores": {}, "error": f"json parse: {e}"}


def format_lighthouse_card(lh: dict, url: str) -> str:
    """Lighthouse 결과 텔레그램 카드."""
    if not lh.get("ok"):
        return f"💡 *Lighthouse 측정 건너뜀* — {lh.get('error', '')[:80]}"

    s = lh["scores"]

    def emoji(v):
        return "🟢" if v >= 90 else "🟡" if v >= 50 else "🔴"

    return (
        f"💡 *Lighthouse 점수* — {url}\n\n"
        f"{emoji(s.get('performance', 0))} Performance: *{s.get('performance', 0)}*\n"
        f"{emoji(s.get('accessibility', 0))} Accessibility: *{s.get('accessibility', 0)}*\n"
        f"{emoji(s.get('best-practices', 0))} Best Practices: *{s.get('best-practices', 0)}*\n"
        f"{emoji(s.get('seo', 0))} SEO: *{s.get('seo', 0)}*"
    )


def send_snapshot_to_telegram(snap_result: dict, lh_result: dict | None,
                              trigger_label: str) -> bool:
    """스냅샷 결과 + Lighthouse를 텔레그램에 전송."""
    try:
        from telegram_bot import client as tg
    except ImportError:
        log.warning("telegram_bot import 실패 — 발송 건너뜀")
        return False

    paths = snap_result.get("paths") or []

    caption_lines = [f"📸 *사이트 스냅샷* — {trigger_label}"]
    if snap_result.get("ok"):
        caption_lines.append(f"✓ {len(paths)}장 캡처 ({snap_result.get('viewport', 'desktop')})")
    if snap_result.get("errors"):
        caption_lines.append(f"⚠️ 일부 실패: {len(snap_result['errors'])}건")
    if lh_result and lh_result.get("ok"):
        s = lh_result["scores"]
        caption_lines.append(
            f"💡 LH: P{s.get('performance', 0)}·A{s.get('accessibility', 0)}·"
            f"BP{s.get('best-practices', 0)}·S{s.get('seo', 0)}"
        )
    caption = "\n".join(caption_lines)

    try:
        if not paths:
            # 사진 없으면 텍스트만
            tg.send_text(caption + "\n\n_캡처 실패_")
            return False
        if len(paths) == 1:
            tg.send_photo(str(paths[0]), caption=caption)
        else:
            tg.send_media_group([str(p) for p in paths], caption=caption)
        return True
    except Exception as e:
        log.warning("snapshot 발송 실패: %s", e)
        try:
            tg.send_text(caption + f"\n\n_사진 발송 실패: {e}_")
        except Exception:
            pass
        return False


def capture_and_report(trigger_label: str, *, use_live: bool = False,
                       mobile_too: bool = False) -> dict:
    """원샷 헬퍼 — 캡처 + 점수 + 텔레그램 발송까지.

    Returns 결과 dict.
    """
    # Desktop 캡처
    snap = capture_pages(use_live=use_live, mobile=False)
    if mobile_too and snap.get("ok"):
        # 모바일 캡처 추가
        snap_m = capture_pages(use_live=use_live, mobile=True)
        if snap_m.get("paths"):
            snap["paths"] = list(snap["paths"]) + list(snap_m["paths"])

    # Lighthouse (라이브 URL일 때만 의미 있음)
    lh = None
    if use_live:
        lh = lighthouse_score()

    sent = send_snapshot_to_telegram(snap, lh, trigger_label)
    return {"snapshot": snap, "lighthouse": lh, "telegram_sent": sent}


def main():
    """CLI: python3 scripts/site_snapshot.py [--live] [--mobile]"""
    import argparse
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true", help="라이브 URL 사용 (기본: 로컬)")
    ap.add_argument("--mobile", action="store_true", help="모바일 뷰포트도 함께 캡처")
    ap.add_argument("--lighthouse", action="store_true", help="Lighthouse 점수 측정 (라이브일 때만)")
    ap.add_argument("--send", action="store_true", help="텔레그램 전송")
    ap.add_argument("--label", default="manual", help="텔레그램 카드 라벨")
    args = ap.parse_args()

    snap = capture_pages(use_live=args.live, mobile=False)
    print(f"\n📸 Desktop 캡처: ok={snap['ok']} files={len(snap['paths'])}")
    for p in snap.get("paths", []):
        print(f"  {p}")
    for e in snap.get("errors", []):
        print(f"  ⚠️ {e}")

    if args.mobile:
        snap_m = capture_pages(use_live=args.live, mobile=True)
        print(f"\n📱 Mobile 캡처: ok={snap_m['ok']} files={len(snap_m['paths'])}")
        snap["paths"] = list(snap["paths"]) + list(snap_m["paths"])

    lh = None
    if args.lighthouse and args.live:
        lh = lighthouse_score()
        print(f"\n💡 Lighthouse: {lh}")

    if args.send:
        sent = send_snapshot_to_telegram(snap, lh, args.label)
        print(f"\n📨 텔레그램 발송: {sent}")

    return 0 if snap.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
