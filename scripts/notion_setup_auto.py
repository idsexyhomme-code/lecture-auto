#!/usr/bin/env python3
"""
Notion 셋업 자동화 — 토큰 1개만 받으면 나머지 다 자동.

흐름:
1. .env에서 NOTION_TOKEN 읽기
2. Notion API search로 Integration이 접근 가능한 페이지 찾기
3. 없으면 → 회원에게 1개 페이지에 권한 부여 요청 (이것만 회원이 직접)
4. 있으면 → 자동:
   a. 그 페이지 안에 "Core Campus" 페이지 자동 생성
   b. .env에 NOTION_PARENT_PAGE_ID 자동 추가
   c. notion_sync.py 호출 → DB 자동 생성 + 산출물 sync
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(REPO_ROOT / ".env")
except ImportError:
    pass

NOTION_API = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"
NOTION_TOKEN = os.environ.get("NOTION_TOKEN", "")
ENV_FILE = REPO_ROOT / ".env"


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def search_accessible_pages() -> list[dict]:
    """Integration이 접근 가능한 모든 페이지/DB 검색."""
    r = requests.post(
        f"{NOTION_API}/search",
        headers=_headers(),
        json={"filter": {"property": "object", "value": "page"}, "page_size": 100},
        timeout=30,
    )
    if r.status_code != 200:
        print(f"  ❌ Notion API 오류 {r.status_code}: {r.text[:200]}")
        return []
    results = r.json().get("results", [])
    return [p for p in results if p.get("object") == "page"]


def create_core_campus_page(parent_page_id: str) -> str | None:
    """지정된 부모 페이지 안에 'Core Campus' 페이지 자동 생성."""
    r = requests.post(
        f"{NOTION_API}/pages",
        headers=_headers(),
        json={
            "parent": {"type": "page_id", "page_id": parent_page_id},
            "icon": {"type": "emoji", "emoji": "🌳"},
            "properties": {
                "title": {
                    "title": [
                        {"type": "text", "text": {"content": "Core Campus — 산출물 인박스"}}
                    ]
                }
            },
            "children": [
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": "Core Campus 8 에이전트가 만든 모든 산출물이 자동으로 이 페이지 안 데이터베이스에 들어옵니다. 모바일 Notion 앱에서 어디서나 확인하세요."
                                },
                            }
                        ]
                    },
                },
            ],
        },
        timeout=30,
    )
    if r.status_code >= 400:
        print(f"  ❌ 페이지 생성 실패 {r.status_code}: {r.text[:200]}")
        return None
    return r.json().get("id")


def update_env_var(key: str, value: str) -> None:
    """.env 파일에 변수 추가 또는 갱신."""
    if not ENV_FILE.exists():
        ENV_FILE.write_text(f"{key}={value}\n", encoding="utf-8")
        return

    text = ENV_FILE.read_text(encoding="utf-8")
    pattern = re.compile(rf"^{re.escape(key)}=.*$", re.MULTILINE)
    if pattern.search(text):
        text = pattern.sub(f"{key}={value}", text)
    else:
        if not text.endswith("\n"):
            text += "\n"
        text += f"{key}={value}\n"
    ENV_FILE.write_text(text, encoding="utf-8")


def get_page_title(page: dict) -> str:
    """페이지 객체에서 제목 추출 (Notion API 응답 구조)."""
    props = page.get("properties", {})
    for prop_name, prop_data in props.items():
        if prop_data.get("type") == "title":
            title_items = prop_data.get("title", [])
            if title_items:
                return "".join(t.get("plain_text", "") for t in title_items)
    return "(제목 없음)"


def main():
    print()
    print("═" * 60)
    print("  🌳 Notion 셋업 자동화")
    print("═" * 60)
    print()

    if not NOTION_TOKEN:
        print("  ❌ NOTION_TOKEN 환경변수 미설정")
        print()
        print("  📋 회원 액션 필요:")
        print("  1. https://www.notion.so/my-integrations 에서 Integration 만들기")
        print("  2. Internal Integration Token 복사 (secret_xxx... 형태)")
        print("  3. .env 파일에 다음 줄 추가 (이 파일과 같은 폴더 .env):")
        print("       NOTION_TOKEN=secret_여기에_복사")
        print()
        print("  4. 이 명령 다시 실행")
        return 1

    print(f"  ✓ NOTION_TOKEN 인식됨 (앞 14자): {NOTION_TOKEN[:14]}...")
    print()

    print("  🔍 Integration 권한 있는 페이지 검색 중...")
    pages = search_accessible_pages()

    if not pages:
        print()
        print("  ❌ Integration이 접근 가능한 페이지가 0개입니다.")
        print()
        print("  📋 회원 액션 필요 (Notion 보안 정책 — 자동화 불가 단계):")
        print()
        print("  1. Naver Whale에서 https://www.notion.so 접속")
        print("  2. 왼쪽 사이드바 + Add a page → 페이지 이름 자유 (예: '내 워크스페이스')")
        print("  3. 그 페이지 우측 상단 ⋯ 메뉴")
        print("  4. Connections → Core Campus Integration 검색 + 선택")
        print("  5. Confirm 클릭")
        print()
        print("  6. 이 명령 다시 실행하면 자동으로 'Core Campus' 페이지 만들고 DB까지 셋업합니다.")
        return 2

    print(f"  ✓ 접근 가능한 페이지 {len(pages)}개 발견:")
    for i, p in enumerate(pages[:5], 1):
        title = get_page_title(p)
        print(f"     {i}. {title[:60]}")
    if len(pages) > 5:
        print(f"     ... 외 {len(pages) - 5}개")
    print()

    # 이미 "Core Campus" 페이지가 있는지 확인
    existing = next(
        (p for p in pages if "core campus" in get_page_title(p).lower()), None
    )

    if existing:
        page_id = existing["id"].replace("-", "")
        print(f"  ✓ 기존 'Core Campus' 페이지 발견 → 재사용")
        print(f"     ID: {page_id}")
    else:
        # 첫 번째 페이지를 부모로 'Core Campus' 자동 생성
        parent = pages[0]
        parent_title = get_page_title(parent)
        print(f"  📝 부모 페이지: '{parent_title[:50]}'")
        print(f"  🌳 그 안에 'Core Campus — 산출물 인박스' 페이지 자동 생성 중...")
        new_id = create_core_campus_page(parent["id"])
        if not new_id:
            print("  ❌ 페이지 생성 실패")
            return 3
        page_id = new_id.replace("-", "")
        print(f"  ✓ 페이지 생성 완료")
        print(f"     ID: {page_id}")

    # .env 업데이트
    print()
    print("  📝 .env 자동 업데이트 중...")
    update_env_var("NOTION_PARENT_PAGE_ID", page_id)
    print(f"  ✓ NOTION_PARENT_PAGE_ID 설정됨")

    # notion_sync.py 호출
    print()
    print("  🚀 데이터베이스 생성 + 산출물 sync 시작...")
    print()

    # 환경변수 갱신
    os.environ["NOTION_PARENT_PAGE_ID"] = page_id

    # notion_sync 직접 import해서 실행
    from scripts import notion_sync
    # 모듈 변수도 갱신
    notion_sync.NOTION_PARENT_PAGE_ID = page_id

    sys.argv = ["notion_sync.py"]  # argparse 깨끗하게
    return notion_sync.main()


if __name__ == "__main__":
    sys.exit(main() or 0)
