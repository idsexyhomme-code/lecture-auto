"""publisher 디버그 — headless=False + 단계별 로깅으로 세션 만료 원인 파악.

사용:
    python scripts/debug_publish.py          # 1건만 (claude-autowork)
    python scripts/debug_publish.py --idx 3  # republish_v2_targets.json 의 4번째

화면이 뜬 채로 진행 — *어디서 login으로 redirect되는지* 직접 확인.
스크린샷도 /tmp/tistory_debug_*.png에 저장.
"""
from __future__ import annotations
import argparse, json, os, sys, time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

try:
    from dotenv import load_dotenv
    load_dotenv(REPO / ".env")
except Exception:
    pass

from playwright.sync_api import sync_playwright

SESSION = REPO / "content" / "state" / "tistory_session.json"
SHOTS = Path("/tmp")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--idx", type=int, default=0, help="republish_v2_targets.json 인덱스")
    ap.add_argument("--blog", type=str, default=os.environ.get("TISTORY_BLOG_NAME","jejumomdad"))
    args = ap.parse_args()

    targets = json.load(open(REPO / "content" / "state" / "republish_v2_targets.json"))
    t = targets[args.idx]
    d = json.load(open(t["path"]))
    title = t["title"]
    body_html = (d.get("meta") or {}).get("body_html","")
    print(f"=== 디버그 발행 ===")
    print(f"  title: {title[:60]}")
    print(f"  body_len: {len(body_html):,}")

    if not SESSION.exists():
        print("[FATAL] 세션 파일 없음")
        return

    session = json.loads(SESSION.read_text())
    print(f"  세션 cookies: {len(session.get('cookies',[]))}")
    print(f"  세션 mtime: {time.ctime(SESSION.stat().st_mtime)}")
    print()

    write_url = f"https://{args.blog}.tistory.com/manage/newpost/"
    print(f"[1] navigating to {write_url}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=200)  # 시각·천천히
        ctx = browser.new_context(
            storage_state=session,
            viewport={"width":1280,"height":900},
            locale="ko-KR",
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 13_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )
        page = ctx.new_page()
        page.goto(write_url, timeout=30000)
        page.wait_for_load_state("domcontentloaded", timeout=30000)
        time.sleep(3)
        print(f"[2] 현재 URL: {page.url}")
        print(f"    페이지 제목: {page.title()}")
        page.screenshot(path=str(SHOTS / "debug_1_loaded.png"))
        print(f"    스크린샷: /tmp/debug_1_loaded.png")

        if "login" in page.url.lower():
            print()
            print("⚠️ 로그인 페이지로 리다이렉트됨. 원인 분석 중...")
            print(f"    페이지 텍스트(앞 500자): {page.inner_text('body')[:500]}")
            print()
            print("→ 이 창에서 *지금* 카카오 로그인 직접 진행해주세요.")
            print("  로그인 끝나면 터미널로 돌아와서 Enter")
            input("로그인 완료 후 Enter ▶ ")
            # 로그인 끝났으면 새 세션 캡처
            new_state = ctx.storage_state()
            SESSION.write_text(json.dumps(new_state, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"  ✓ 새 세션 저장 ({len(new_state.get('cookies',[]))} cookies)")
            page.goto(write_url, timeout=30000)
            page.wait_for_load_state("domcontentloaded")
            time.sleep(2)
            print(f"  → 재시도 URL: {page.url}")

        if "newpost" not in page.url:
            print(f"[FAIL] newpost 페이지 도달 실패: {page.url}")
            input("창 닫으려면 Enter ▶ ")
            browser.close()
            return

        print()
        print("[3] 제목·본문 입력 중...")
        page.wait_for_selector("#post-title-inp", timeout=10000, state="visible")
        page.fill("#post-title-inp", title)
        time.sleep(1)
        page.wait_for_selector("iframe#editor-tistory_ifr", timeout=10000)
        # tinymce.activeEditor.setContent
        escaped = body_html.replace("\\","\\\\").replace("`","\\`").replace("$","\\$")
        result = page.evaluate(f"""
            (() => {{
                if (typeof tinymce === 'undefined' || !tinymce.activeEditor) return {{ok:false,reason:'no tinymce'}};
                tinymce.activeEditor.setContent(`{escaped}`);
                tinymce.activeEditor.save();
                return {{ok:true, len: tinymce.activeEditor.getContent().length}};
            }})()
        """)
        print(f"    본문 주입 결과: {result}")
        page.screenshot(path=str(SHOTS / "debug_2_filled.png"))
        print(f"    스크린샷: /tmp/debug_2_filled.png")

        print()
        print("[4] '완료' 버튼 클릭 직전. 화면 확인 후 Enter 누르면 발행 시도")
        input("발행 시도 ▶ ")
        page.click("#publish-layer-btn", timeout=5000)
        time.sleep(2)
        page.screenshot(path=str(SHOTS / "debug_3_publish_layer.png"))
        print(f"    layer 열림. 스크린샷: /tmp/debug_3_publish_layer.png")

        print()
        print("[5] 즉시 발행 vs 예약 — 회원님이 직접 선택해서 '공개 발행' 클릭")
        input("발행 완료 후 Enter ▶ ")
        time.sleep(2)
        print(f"    최종 URL: {page.url}")
        page.screenshot(path=str(SHOTS / "debug_4_done.png"))
        print(f"    스크린샷: /tmp/debug_4_done.png")
        print()
        print("=== 디버그 완료 ===")
        input("창 닫으려면 Enter ▶ ")
        browser.close()


if __name__ == "__main__":
    main()
