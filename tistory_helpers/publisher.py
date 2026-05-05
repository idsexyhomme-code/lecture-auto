"""티스토리 자동 글 게시 — 저장된 쿠키로 Playwright 자동화.

사용:
    from tistory_helpers.publisher import publish_post

    url = publish_post(
        blog="myblogname",       # myblogname.tistory.com 의 myblogname
        title="제목",
        body_html="<p>본문 HTML</p>",
        tags=["Claude", "1인 사업가"],
        publish=True,            # False면 임시저장
    )

CLI 테스트:
    python -m tistory_helpers.publisher test
"""
from __future__ import annotations

import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

# .env 로드
try:
    from dotenv import load_dotenv
    load_dotenv(REPO_ROOT / ".env")
except ImportError:
    pass

from tistory_helpers.auth import load_session, SESSION_FILE

log = logging.getLogger("tistory_publisher")


def publish_post(
    *,
    blog: str,
    title: str,
    body_html: str,
    tags: Optional[list] = None,
    publish: bool = True,
    timeout: int = 60000,
) -> Optional[str]:
    """티스토리에 글 게시. 게시된 URL 반환 (실패 시 None).

    Args:
        blog: 블로그 subdomain (myblogname.tistory.com 의 myblogname)
        title: 글 제목
        body_html: 본문 HTML
        tags: 태그 리스트 (옵션)
        publish: True=발행, False=임시저장
    """
    session = load_session()
    if not session:
        raise RuntimeError(
            "티스토리 세션이 없습니다. 먼저 1회 수동 로그인:\n"
            "  python -m tistory_helpers.auth"
        )

    from playwright.sync_api import sync_playwright

    write_url = f"https://{blog}.tistory.com/manage/newpost/"
    log.info("[tistory] navigating to %s", write_url)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            storage_state=session,
            viewport={"width": 1280, "height": 900},
            locale="ko-KR",
        )
        page = context.new_page()

        try:
            page.goto(write_url, timeout=timeout)
            page.wait_for_load_state("networkidle", timeout=timeout)

            if "login" in page.url.lower():
                browser.close()
                raise RuntimeError(
                    "티스토리 세션 만료. 다시 수동 로그인 필요:\n"
                    "  python -m tistory_helpers.auth"
                )

            # 제목 입력
            title_selectors = [
                "input[placeholder*='제목']",
                "#post-title-input",
                "textarea[name='title']",
            ]
            title_input = None
            for sel in title_selectors:
                try:
                    el = page.wait_for_selector(sel, timeout=5000)
                    if el:
                        title_input = el
                        break
                except Exception:
                    continue
            if not title_input:
                browser.close()
                raise RuntimeError("제목 입력란을 못 찾았습니다 — 티스토리 UI 변경 의심")
            title_input.fill(title)
            log.info("[tistory] title filled")

            # 본문 입력 — HTML 모드로 전환 시도
            time.sleep(2)
            try:
                page.click("button:has-text('HTML')", timeout=3000)
                time.sleep(1)
                page.fill("textarea.tx-source", body_html, timeout=10000)
                log.info("[tistory] body filled (HTML mode)")
            except Exception:
                try:
                    iframe = page.frame_locator("iframe").first
                    iframe.locator("body").fill(body_html)
                    log.info("[tistory] body filled (iframe mode)")
                except Exception as e:
                    log.warning("[tistory] body 입력 실패: %s", e)

            # 태그 입력
            if tags:
                try:
                    tag_input = page.wait_for_selector(
                        "input[placeholder*='태그']", timeout=5000
                    )
                    for tag in tags:
                        tag_input.fill(tag)
                        page.keyboard.press("Enter")
                        time.sleep(0.3)
                    log.info("[tistory] %d tags filled", len(tags))
                except Exception:
                    log.warning("[tistory] 태그 입력 실패 (무시)")

            # 게시 또는 임시저장
            if publish:
                publish_btn_sel = [
                    "button:has-text('공개 발행')",
                    "button:has-text('발행')",
                    "#publish-btn",
                ]
            else:
                publish_btn_sel = ["button:has-text('임시저장')"]

            for sel in publish_btn_sel:
                try:
                    page.click(sel, timeout=3000)
                    log.info("[tistory] %s clicked", sel)
                    break
                except Exception:
                    continue

            time.sleep(3)
            try:
                page.click("button:has-text('공개 발행')", timeout=2000)
            except Exception:
                pass
            try:
                page.click("button:has-text('확인')", timeout=2000)
            except Exception:
                pass

            time.sleep(5)

            final_url = page.url
            log.info("[tistory] final URL: %s", final_url)
            browser.close()
            return final_url

        except Exception as e:
            log.exception("[tistory] 게시 실패: %s", e)
            try:
                debug_path = REPO_ROOT / "content" / "state" / "tistory_debug.png"
                page.screenshot(path=str(debug_path), full_page=True)
                log.info("[tistory] 디버그 스크린샷: %s", debug_path)
            except Exception:
                pass
            browser.close()
            raise


def _cli_test():
    blog = os.environ.get("TISTORY_BLOG")
    if not blog:
        print("TISTORY_BLOG 환경변수를 설정하세요. 예:")
        print("  echo 'TISTORY_BLOG=jejumomdad' >> .env")
        return

    print(f"테스트 글 게시 중 → {blog}.tistory.com")
    url = publish_post(
        blog=blog,
        title="[테스트] 코어 캠퍼스 자동 게시 검증",
        body_html=(
            "<h2>이 글은 자동 게시 검증용입니다</h2>"
            "<p>코어 캠퍼스 봇이 Playwright로 자동 게시한 글입니다.</p>"
            "<p>잘 보이면 검증 성공 — 회원님이 이 글을 임시저장에서 삭제하시면 됩니다.</p>"
        ),
        tags=["테스트", "코어캠퍼스"],
        publish=False,  # 테스트는 임시저장
    )
    print(f"\n✓ 완료. URL: {url}")
    print("  (publish=False라 임시저장으로 들어갔어요)")


if __name__ == "__main__":
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s [%(name)s] %(message)s",
    )
    cmd = sys.argv[1] if len(sys.argv) > 1 else "test"
    if cmd == "test":
        _cli_test()
    else:
        print(f"사용: python -m tistory_helpers.publisher [test]")
