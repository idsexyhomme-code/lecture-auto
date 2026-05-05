"""티스토리 1회 수동 로그인 → 쿠키 캡처.

흐름:
    1. python -m tistory_helpers.auth 실행
    2. Chromium 창이 *headed*로 뜸 (회원님 직접 보임)
    3. 회원님이 *수동*으로 카카오·티스토리 로그인
    4. 로그인 끝나면 터미널에서 Enter 누름
    5. 스크립트가 쿠키 캡처 → content/state/tistory_session.json 저장
    6. 이후 데몬은 *이 쿠키로 자동 게시*

⚠️ 보안:
    - 세션 파일은 .gitignore에 등록되어야 함
    - 만료 시 (티스토리 세션 보통 1-3개월) 다시 한 번 수동 로그인
    - 만약 노출되면 즉시 카카오 비밀번호 변경 + 모든 기기 로그아웃
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

# .env 로드
try:
    from dotenv import load_dotenv
    load_dotenv(REPO_ROOT / ".env")
except ImportError:
    pass

SESSION_FILE = REPO_ROOT / "content" / "state" / "tistory_session.json"


def capture_session():
    """헤드리스 *아닌* Chromium 띄워 회원님 수동 로그인 → 쿠키 저장."""
    from playwright.sync_api import sync_playwright

    print("=" * 60)
    print("티스토리 1회 수동 로그인 — 브라우저 창이 곧 뜹니다")
    print("=" * 60)
    print()
    print("순서:")
    print("  1. Chromium 창에서 카카오 또는 티스토리 로그인 진행")
    print("  2. 로그인 완료되면 ↓ 이 터미널에 *돌아와서 Enter*")
    print("  3. 스크립트가 쿠키 자동 캡처")
    print()

    SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            locale="ko-KR",
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_0) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()
        page.goto("https://www.tistory.com/auth/login", timeout=60000)

        print("👉 브라우저에서 로그인 진행하세요...")
        try:
            input("로그인 끝났으면 여기 터미널에 Enter ▶ ")
        except (KeyboardInterrupt, EOFError):
            print("\n취소됨")
            browser.close()
            return

        # 쿠키 + storage_state 모두 저장
        storage = context.storage_state()
        SESSION_FILE.write_text(
            json.dumps(storage, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        # 로그인 검증
        print()
        print("✓ 세션 캡처 완료. 검증 중...")
        page.goto("https://www.tistory.com/", timeout=30000)
        page.wait_for_load_state("networkidle", timeout=15000)

        url = page.url
        title = page.title()
        print(f"  현재 URL: {url}")
        print(f"  페이지 제목: {title}")

        if "login" in url.lower():
            print("  ⚠️ URL에 'login'이 있음 — 로그인 안 됐을 수 있습니다")
            print("     브라우저 창에서 다시 로그인 후 Enter")
            try:
                input("재시도 ▶ ")
                storage = context.storage_state()
                SESSION_FILE.write_text(
                    json.dumps(storage, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                print("  ✓ 재시도 세션 저장")
            except (KeyboardInterrupt, EOFError):
                print("  취소됨")

        print()
        print(f"세션 저장됨: {SESSION_FILE}")
        print(f"  쿠키 개수: {len(storage.get('cookies', []))}")
        print()

        # gitignore 검증
        gitignore = REPO_ROOT / ".gitignore"
        gi_text = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
        if "tistory_session" in gi_text:
            print("✓ .gitignore에 tistory_session 등록 확인됨 (세션 파일 안전)")
        else:
            print("⚠️ .gitignore에 tistory_session 미등록 — 즉시 추가 권장:")
            print("   echo 'content/state/tistory_session.json' >> .gitignore")

        try:
            input("브라우저 닫고 종료하려면 Enter ▶ ")
        except (KeyboardInterrupt, EOFError):
            pass
        browser.close()

    print("✓ 완료. 이제 publisher가 이 세션을 사용합니다.")


def load_session() -> dict | None:
    if not SESSION_FILE.exists():
        return None
    try:
        return json.loads(SESSION_FILE.read_text(encoding="utf-8"))
    except Exception:
        return None


if __name__ == "__main__":
    capture_session()
