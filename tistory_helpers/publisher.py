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
from datetime import datetime, timedelta, timezone
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

# ─── 확정 셀렉터 (실제 jejumomdad 페이지 분석으로 검증) ───
TITLE_ID = "#post-title-inp"          # textarea (input 아님!)
TAG_ID = "#tagText"
PUBLISH_BTN = "#publish-layer-btn"    # 발행 버튼 — 페이지에 없으면 텍스트 매칭 fallback
SAVE_BTN = "#save-btn"                 # 임시저장 버튼
EDITOR_IFRAME = "iframe#editor-tistory_ifr"   # TinyMCE
EDITOR_BODY = "body#tinymce"           # iframe 안의 contenteditable body


def _shoot(page, name: str):
    """디버그용 스크린샷."""
    try:
        DEBUG_DIR.mkdir(parents=True, exist_ok=True)
        path = DEBUG_DIR / f"{name}.png"
        page.screenshot(path=str(path), full_page=True)
    except Exception:
        pass


def _handle_schedule_mode(page, schedule_at: datetime) -> bool:
    """티스토리 신에디터 모달의 '예약' 토글 + datepicker 시각 입력.

    schedule_at: KST timezone-aware datetime 권장. naive면 KST로 가정.
    Returns: 입력 성공 여부 (실패해도 raise 안 함 — 진단 흔적은 남기고 발행 시도)
    """
    # naive datetime → KST 가정
    if schedule_at.tzinfo is None:
        kst = timezone(timedelta(hours=9))
        schedule_at = schedule_at.replace(tzinfo=kst)

    target_date = schedule_at.strftime('%Y-%m-%d')   # YYYY-MM-DD
    target_time = schedule_at.strftime('%H:%M')       # HH:MM
    target_iso = schedule_at.strftime('%Y-%m-%dT%H:%M')
    log.info("[tistory] 📅 예약 발행 시각: %s %s (KST)", target_date, target_time)

    # 1. "예약" 버튼 클릭 (button.btn_date:has-text('예약'))
    schedule_clicked = False
    for sel in [
        "button.btn_date:has-text('예약')",
        "button:has-text('예약')",
        ".btn_date:has-text('예약')",
    ]:
        try:
            page.locator(sel).first.click(timeout=3000, force=True)
            log.info("[tistory] ✓ 예약 토글 클릭 (%s)", sel)
            schedule_clicked = True
            break
        except Exception:
            continue

    if not schedule_clicked:
        log.error("[tistory] ✗ 예약 버튼 못 찾음 — 즉시 발행으로 진행")
        return False

    time.sleep(1.5)  # datepicker 애니메이션 대기

    # 2. 모달 내부 input/select 덤프 (진단 — 셀렉터 못 잡으면 다음 작업 단서)
    try:
        inputs = page.evaluate("""
            () => {
                const els = [...document.querySelectorAll('input, select')];
                return els
                    .filter(i => i.offsetParent !== null)
                    .map(i => ({
                        tag: i.tagName, type: i.type || '',
                        id: i.id || '', name: i.name || '',
                        cls: (i.className || '').toString().slice(0, 60),
                        value: (i.value || '').toString().slice(0, 30),
                        placeholder: i.placeholder || ''
                    }));
            }
        """)
        log.info("[tistory] === 예약 모드 활성 input/select %d개 ===", len(inputs))
        for i in inputs:
            log.info("  · [%s/%s] id=%s name=%s cls=%s value='%s' ph='%s'",
                     i.get('tag'), i.get('type'),
                     i.get('id'), i.get('name'), i.get('cls'),
                     i.get('value'), i.get('placeholder'))
    except Exception as e:
        log.warning("[tistory] input 덤프 실패: %s", e)

    # 3. datepicker 시각 입력 — 확정 셀렉터 (input#dateHour, input#dateMinute)
    #    티스토리 신에디터: 예약 토글 클릭 시 자동으로 +1h default 채워짐.
    #    우리는 scheduler가 계산한 정확한 시각으로 덮어씀.
    filled_any = False
    target_hour = str(schedule_at.hour)
    target_minute = str(schedule_at.minute)

    for sel, value in [
        ("input#dateHour", target_hour),
        ("input#dateMinute", target_minute),
    ]:
        try:
            loc = page.locator(sel).first
            if loc.count() > 0:
                # JS로 강제 setting + change 이벤트 (Playwright fill 대신)
                page.evaluate(
                    f"""
                    () => {{
                        const el = document.querySelector('{sel}');
                        if (!el) return;
                        el.value = '{value}';
                        el.dispatchEvent(new Event('input', {{bubbles:true}}));
                        el.dispatchEvent(new Event('change', {{bubbles:true}}));
                        el.dispatchEvent(new Event('blur', {{bubbles:true}}));
                    }}
                    """
                )
                log.info("[tistory] ✓ %s = %s", sel, value)
                filled_any = True
        except Exception as e:
            log.warning("[tistory] %s 입력 실패: %s", sel, e)

    if not filled_any:
        log.error("[tistory] dateHour/dateMinute 둘 다 못 잡음 — 티스토리 default(+1h)로 발행")

    return filled_any


def publish_post(
    *,
    blog: str,
    title: str,
    body_html: str,
    tags: Optional[list] = None,
    publish: bool = True,
    schedule_at: Optional[datetime] = None,
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

            # 3. 본문 — TinyMCE 공식 API setContent() 사용 (내부 모델까지 동기화)
            #    iframe 안 body innerHTML 직접 조작은 TinyMCE 내부 모델과 *동기화 안 됨* → 발행 시 빈 본문
            try:
                page.wait_for_selector(EDITOR_IFRAME, timeout=10000)
                # TinyMCE editor가 main page (iframe 밖)에서 globally 접근 가능
                # tinymce.activeEditor.setContent(html) 가 정확한 방법
                escaped = (
                    body_html
                    .replace("\\", "\\\\")
                    .replace("`", "\\`")
                    .replace("$", "\\$")
                )
                inject_result = page.evaluate(f"""
                    () => {{
                        if (window.tinymce && window.tinymce.activeEditor) {{
                            window.tinymce.activeEditor.setContent(`{escaped}`);
                            window.tinymce.activeEditor.save();  // 내부 모델 → form input 동기화
                            const len = window.tinymce.activeEditor.getContent().length;
                            return 'tinymce.setContent OK, content length=' + len;
                        }}
                        return 'no tinymce — fallback to innerHTML';
                    }}
                """)
                log.info("[tistory] ✓ 본문 주입: %s", inject_result)
                # 검증 — 너무 짧으면 실패로 간주
                if "OK" not in str(inject_result):
                    raise RuntimeError(f"setContent 실패: {inject_result}")
            except Exception as e:
                _shoot(page, "FAIL-body")
                log.warning("[tistory] tinymce.setContent 실패: %s — innerHTML fallback", e)
                # Fallback — iframe innerHTML
                try:
                    frame = page.frame_locator(EDITOR_IFRAME)
                    body_locator = frame.locator(EDITOR_BODY)
                    body_locator.wait_for(state="visible", timeout=10000)
                    body_locator.evaluate(
                        f"el => {{ el.innerHTML = `{escaped}`; "
                        f"el.dispatchEvent(new Event('input', {{bubbles: true}})); "
                        f"el.dispatchEvent(new Event('change', {{bubbles: true}})); }}"
                    )
                    log.info("[tistory] ✓ 본문 (innerHTML fallback)")
                except Exception as e2:
                    _shoot(page, "FAIL-body-fallback")
                    raise RuntimeError(f"본문 입력 모두 실패: {e2}")
            _shoot(page, "3-body")

            # 4. 태그 입력 (옵션) — input#tagText
            if tags:
                try:
                    tag_input = page.wait_for_selector(TAG_ID, timeout=5000)
                    tag_input.click()
                    for tag in tags[:5]:
                        page.keyboard.type(str(tag))
                        page.keyboard.press("Enter")
                        time.sleep(0.4)
                    log.info("[tistory] ✓ 태그 %d개", len(tags[:5]))
                except Exception as e:
                    log.warning("[tistory] 태그 입력 무시: %s", e)
            _shoot(page, "4-tags")

            # 5. 완료/발행/임시저장 버튼 — 다양한 후보 시도
            time.sleep(1.5)
            # 완료 버튼 (페이지 상단 — 누르면 모달 띄움)
            done_clicked = False
            for sel in [
                "#publish-layer-btn",
                "button#save-btn",
                "button:has-text('완료')",
                ".btn-default:has-text('완료')",
                "button[id*='publish']",
            ]:
                try:
                    page.click(sel, timeout=2500)
                    log.info("[tistory] ✓ 완료 버튼 (%s)", sel)
                    done_clicked = True
                    break
                except Exception:
                    continue

            if not done_clicked:
                _shoot(page, "FAIL-no-done-btn")
                # 마지막 fallback: 키보드 단축키
                try:
                    page.keyboard.press("Control+S" if sys.platform != "darwin" else "Meta+S")
                    log.info("[tistory] ✓ Cmd+S 단축키")
                except Exception:
                    pass

            time.sleep(2.5)
            _shoot(page, "5-after-done")

            # ★ 5b. 예약 발행 모드 — schedule_at 주어지면 "예약" 토글 + 시각 입력
            if schedule_at and publish:
                _handle_schedule_mode(page, schedule_at)
                _shoot(page, "5b-schedule-set")

            # 6. 모달 진단 — 떠 있는 모든 visible 버튼 dump
            time.sleep(2)  # 모달 애니메이션 충분히 대기
            try:
                visible_buttons = page.evaluate("""
                    () => {
                        const all = [...document.querySelectorAll('button, a, [role="button"], input[type="button"], input[type="submit"]')];
                        return all
                            .filter(b => b.offsetParent !== null)
                            .map(b => ({
                                text: (b.textContent || b.value || '').trim().slice(0, 40),
                                tag: b.tagName,
                                id: b.id || '',
                                cls: (b.className || '').toString().slice(0, 60),
                            }));
                    }
                """)
                log.info("[tistory] === 모달 단계 visible 버튼 %d개 ===", len(visible_buttons))
                for b in visible_buttons:
                    log.info("  · '%s' [%s] id=%s class=%s",
                            b.get('text'), b.get('tag'), b.get('id'), b.get('cls'))
            except Exception as e:
                log.warning("[tistory] 버튼 dump 실패: %s", e)

            # 7. 모달 클릭 — JS로 정확히 매칭
            modal_clicked = False
            target_text_pattern = "공개\\s*발행|발행하기|^\\s*발행\\s*$" if publish else "임시저장|^\\s*저장\\s*$"
            try:
                clicked_info = page.evaluate(f"""
                    () => {{
                        const pattern = /{target_text_pattern}/;
                        const cancelPattern = /취소|닫기|cancel/i;
                        const all = [...document.querySelectorAll('button, a, [role="button"], input[type="button"], input[type="submit"]')];
                        const candidates = all.filter(b => {{
                            const t = (b.textContent || b.value || '').trim();
                            return pattern.test(t) && !cancelPattern.test(t) && b.offsetParent !== null;
                        }});
                        if (candidates.length === 0) return 'no candidates';
                        // 우선순위: id에 publish 들어있는 것 > 마지막에 추가된 것 (모달 안)
                        const sorted = candidates.sort((a, b) => {{
                            const aPub = /publish/i.test(a.id + a.className) ? 1 : 0;
                            const bPub = /publish/i.test(b.id + b.className) ? 1 : 0;
                            return bPub - aPub;
                        }});
                        const target = sorted[0];
                        const text = (target.textContent || target.value || '').trim().slice(0, 30);
                        // 클릭 + 강제 이벤트 발생
                        target.click();
                        target.dispatchEvent(new MouseEvent('click', {{bubbles: true, cancelable: true}}));
                        return 'clicked: ' + text + ' [' + target.tagName + ' id=' + target.id + ']';
                    }}
                """)
                log.info("[tistory] 모달 JS 클릭: %s", clicked_info)
                modal_clicked = "clicked" in str(clicked_info)
            except Exception as e:
                log.warning("[tistory] JS 클릭 실패: %s", e)

            # 8. 그래도 안 되면 — Playwright 셀렉터 시도
            if not modal_clicked:
                modal_options = ["공개 발행", "발행하기", "발행", "확인"] if publish else ["임시저장", "저장"]
                for label in modal_options:
                    for sel in [
                        f"button:has-text('{label}')",
                        f"a:has-text('{label}')",
                        f"[role='button']:has-text('{label}')",
                    ]:
                        try:
                            loc = page.locator(sel).last
                            loc.click(timeout=3000, force=True)
                            log.info("[tistory] ✓ Playwright fallback 클릭 (%s)", sel)
                            modal_clicked = True
                            break
                        except Exception:
                            continue
                    if modal_clicked:
                        break

            # 9. URL 변경 대기 — newpost에서 실제 글 페이지로
            try:
                page.wait_for_url(
                    lambda u: "/manage/newpost" not in u and "tistory.com" in u,
                    timeout=15000,
                )
                log.info("[tistory] ✓ URL 변경 감지")
            except Exception as e:
                log.warning("[tistory] URL 변경 안됨 (%ds 대기): %s", 15, e)
                # Enter 키 fallback
                try:
                    page.keyboard.press("Enter")
                    time.sleep(3)
                except Exception:
                    pass

            time.sleep(3)
            _shoot(page, "6-final")
            final_url = page.url
            log.info("[tistory] 🌐 final URL: %s", final_url)

            browser.close()

            # 발행 검증 — manage/newpost에 머물러 있으면 실패
            if "/manage/newpost" in final_url or "/login" in final_url:
                raise RuntimeError(f"발행 확정 실패. final URL: {final_url}")

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
