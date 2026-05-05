"""티스토리 자동 글 게시 — 확정 셀렉터 사용.

티스토리 표준 ID (몇 년째 동일):
    #post-title-input  — 제목 input
    #tag-input         — 태그 input
    #publish-btn       — 공개 발행 버튼 → 모달 띄움
    #save-btn          — 임시저장 버튼 (바로 저장)
    iframe#tx_canvas_iframe — 본문 에디터 iframe

본문은 iframe 안의 body에 evaluate로 innerHTML을 *직접 주입*. fill보다 안정적.
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

try:
    from dotenv import load_dotenv
    load_dotenv(REPO_ROOT / ".env")
except ImportError:
    pass

from tistory_helpers.auth import load_session, SESSION_FILE

log = logging.getLogger("tistory_publisher")

DEBUG_DIR = REPO_ROOT / "content" / "state" / "tistory_debug"

# ─── 확정 셀렉터 ──────────────────────────────────────────
TITLE_ID = "#post-title-input"
TAG_ID = "#tag-input"
PUBLISH_BTN = "#publish-btn"
SAVE_BTN = "#save-btn"
EDITOR_IFRAME = "iframe#tx_canvas_iframe"


def _shoot(page, name: str):
    """디버그용 스크린샷."""
    try:
        DEBUG_DIR.mkdir(parents=True, exist_ok=True)
        path = DEBUG_DIR / f"{name}.png"
        page.screenshot(path=str(path), full_page=True)
    except Exception:
        pass


def publish_post(
    *,
    blog: str,
    title: str,
    body_html: str,
    tags: Optional[list] = None,
    publish: bool = True,
    timeout: int = 60000,
    headless: bool = True,
) -> Optional[str]:
    """티스토리에 글 게시. 게시된 URL 반환 (실패 시 예외).

    Args:
        blog: 블로그 subdomain (myblog.tistory.com 의 myblog)
        title: 글 제목
        body_html: 본문 HTML
        tags: 태그 리스트 (옵션, 최대 5개)
        publish: True=공개 발행, False=임시저장
        headless: False면 브라우저 창 띄움 (디버그용)
    """
    session = load_session()
    if not session:
        raise RuntimeError(
            "티스토리 세션 없음. 먼저: python -m tistory_helpers.auth"
        )

    from playwright.sync_api import sync_playwright

    write_url = f"https://{blog}.tistory.com/manage/newpost/"
    log.info("[tistory] → %s", write_url)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            storage_state=session,
            viewport={"width": 1280, "height": 900},
            locale="ko-KR",
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_0) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()

        try:
            # 1. 페이지 진입
            page.goto(write_url, timeout=timeout)
            page.wait_for_load_state("domcontentloaded", timeout=timeout)
            time.sleep(3)  # 에디터 JS 로딩 대기
            _shoot(page, "1-loaded")

            if "login" in page.url.lower():
                browser.close()
                raise RuntimeError("세션 만료. 다시 로그인: python -m tistory_helpers.auth")

            # 2. 제목 입력
            try:
                page.wait_for_selector(TITLE_ID, timeout=10000, state="visible")
                page.fill(TITLE_ID, title)
                log.info("[tistory] ✓ 제목")
            except Exception as e:
                _shoot(page, "FAIL-title")
                raise RuntimeError(f"제목 입력 실패: {e}")
            _shoot(page, "2-title")

            # 3. 본문 — iframe 안의 body에 innerHTML 직접 주입
            try:
                page.wait_for_selector(EDITOR_IFRAME, timeout=10000)
                # frame_locator로 iframe 안 진입 → body의 innerHTML 설정
                frame = page.frame_locator(EDITOR_IFRAME)
                frame.locator("body").wait_for(state="visible", timeout=10000)
                # JavaScript evaluate로 innerHTML 직접 주입 (가장 안정적)
                # body_html에 백틱·달러·백슬래시 escape
                escaped = (
                    body_html
                    .replace("\\", "\\\\")
                    .replace("`", "\\`")
                    .replace("$", "\\$")
                )
                frame.locator("body").evaluate(
                    f"el => {{ el.innerHTML = `{escaped}`; "
                    f"el.dispatchEvent(new Event('input', {{bubbles: true}})); }}"
                )
                log.info("[tistory] ✓ 본문 (iframe innerHTML)")
            except Exception as e:
                _shoot(page, "FAIL-body")
                log.warning("[tistory] iframe 주입 실패: %s — keyboard fallback", e)
                # fallback: 키보드 입력 (HTML 태그가 텍스트로 들어가지만 일단 저장은 됨)
                try:
                    frame = page.frame_locator(EDITOR_IFRAME)
                    frame.locator("body").click()
                    page.keyboard.insert_text(body_html[:5000])  # 길이 제한
                    log.info("[tistory] ✓ 본문 (keyboard fallback)")
                except Exception as e2:
                    _shoot(page, "FAIL-body-fallback")
                    raise RuntimeError(f"본문 입력 모두 실패: {e2}")
            _shoot(page, "3-body")

            # 4. 태그 입력 (옵션)
            if tags:
                try:
                    tag_input = page.wait_for_selector(TAG_ID, timeout=5000)
                    for tag in tags[:5]:
                        tag_input.fill(str(tag))
                        page.keyboard.press("Enter")
                        time.sleep(0.4)
                    log.info("[tistory] ✓ 태그 %d개", len(tags[:5]))
                except Exception as e:
                    log.warning("[tistory] 태그 입력 무시: %s", e)
            _shoot(page, "4-tags")

            # 5. 임시저장 또는 발행
            time.sleep(1)
            if publish:
                # 공개 발행 → 모달 → 모달 안의 공개 발행 버튼 클릭
                page.click(PUBLISH_BTN, timeout=5000)
                log.info("[tistory] ✓ 발행 버튼 클릭 (1차)")
                _shoot(page, "5a-publish-modal")
                # 모달의 확인 버튼 — 다양한 후보
                modal_clicked = False
                for sel in [
                    "button:has-text('공개 발행')",
                    "button:has-text('발행하기')",
                    "button:has-text('확인')",
                    "#publish-layer .btn",
                    ".btn-publish-confirm",
                ]:
                    try:
                        # 모달 안에서 visible한 발행 버튼만
                        page.wait_for_selector(sel, timeout=2000, state="visible")
                        page.click(sel, timeout=2000)
                        log.info("[tistory] ✓ 모달 확인 (%s)", sel)
                        modal_clicked = True
                        break
                    except Exception:
                        continue
                if not modal_clicked:
                    log.warning("[tistory] 모달 확인 못 찾음 — 그래도 1차 클릭으로 발행됐을 수 있음")
            else:
                page.click(SAVE_BTN, timeout=5000)
                log.info("[tistory] ✓ 임시저장 버튼 클릭")

            # 6. 처리 대기
            time.sleep(6)
            _shoot(page, "6-final")
            final_url = page.url
            log.info("[tistory] 🌐 final URL: %s", final_url)

            browser.close()
            return final_url

        except Exception as e:
            log.exception("[tistory] 게시 실패: %s", e)
            try:
                _shoot(page, "ERROR")
            except Exception:
                pass
            browser.close()
            raise


def _cli_test(headless: bool = True):
    blog = os.environ.get("TISTORY_BLOG")
    if not blog:
        print("TISTORY_BLOG 환경변수 없음. .env에 추가하세요:")
        print("  echo 'TISTORY_BLOG=jejumomdad' >> .env")
        return

    print(f"테스트 글 게시 → {blog}.tistory.com (headless={headless})")
    print(f"디버그 스크린샷: {DEBUG_DIR}")
    try:
        url = publish_post(
            blog=blog,
            title=f"[테스트 {time.strftime('%H:%M')}] 자동 게시 검증",
            body_html=(
                "<h2>자동 게시 검증 — 코어 캠퍼스</h2>"
                "<p>이 글은 Playwright로 <b>자동 게시된</b> 테스트 글입니다.</p>"
                "<p>잘 보이면 검증 성공. 임시저장 탭에서 회원님이 *삭제* 가능.</p>"
                "<ul><li>제목 입력</li><li>iframe 본문 주입</li><li>태그</li>"
                "<li>임시저장 버튼 클릭</li></ul>"
            ),
            tags=["테스트", "코어캠퍼스", "자동화"],
            publish=False,  # 임시저장
            headless=headless,
        )
        print(f"\n✓ 완료. final URL: {url}")
        print(f"  티스토리 임시저장: https://{blog}.tistory.com/manage/posts")
    except Exception as e:
        print(f"\n✗ 실패: {e}")
        print(f"  스크린샷 폴더: {DEBUG_DIR}")
        print(f"  마지막 단계 스크린샷 보기: open '{DEBUG_DIR}'")


if __name__ == "__main__":
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s [%(name)s] %(message)s",
    )
    cmd = sys.argv[1] if len(sys.argv) > 1 else "test"
    if cmd == "test":
        _cli_test(headless=True)
    elif cmd == "debug":
        _cli_test(headless=False)  # 브라우저 창 띄움
    else:
        print("사용: python -m tistory_helpers.publisher [test | debug]")
