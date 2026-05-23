#!/usr/bin/env python3
"""
Core Campus 산출물 → Notion 데이터베이스 자동 동기화.

흐름:
1. NOTION_TOKEN + NOTION_PARENT_PAGE_ID 확인 (.env)
2. 첫 실행: 부모 페이지 안에 "Core Campus 산출물" 데이터베이스 자동 생성
   (생성된 DB ID는 content/state/notion_database_id.txt 에 저장 — 이후 재사용)
3. content/approved/*.json + content/pending/*.json 읽기
4. 각 산출물 → Notion 페이지 (idempotent — 같은 ID는 update)
5. body_md 본문 → Notion blocks 변환

사용:
    python3 scripts/notion_sync.py            # approved + pending 동기화
    python3 scripts/notion_sync.py --pending  # pending만
    python3 scripts/notion_sync.py --setup    # DB만 만들고 종료 (산출물 sync X)

Notion DB Properties:
- Title (제목)
- Agent (Select: ceo / curriculum / producer / marketing / success / ...)
- Kind (Select: curriculum_outline / lecture_script / landing_copy / ...)
- Course ID (Text)
- Status (Select: pending / approved / rejected)
- Self Review (Select: pass / warn / fail)
- HARD violations (Number)
- SOFT violations (Number)
- Created at (Date)
- Summary (Text)
- DRI (Text — 새 SYSTEM에서 명시한 책임자)
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(REPO_ROOT / ".env")
except ImportError:
    pass

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("notion_sync")

NOTION_API = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"

NOTION_TOKEN = os.environ.get("NOTION_TOKEN", "")
NOTION_PARENT_PAGE_ID = os.environ.get("NOTION_PARENT_PAGE_ID", "")

DB_ID_FILE = REPO_ROOT / "content" / "state" / "notion_database_id.txt"

APPROVED_DIR = REPO_ROOT / "content" / "approved"
PENDING_DIR = REPO_ROOT / "content" / "pending"
REJECTED_DIR = REPO_ROOT / "content" / "rejected"


# ─────────────────────────────────────────────────────────────────────
# Notion API helpers
# ─────────────────────────────────────────────────────────────────────
def _headers() -> dict:
    if not NOTION_TOKEN:
        raise RuntimeError("NOTION_TOKEN 환경변수 미설정 — .env 확인")
    return {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def _post(path: str, payload: dict) -> dict:
    r = requests.post(f"{NOTION_API}{path}", headers=_headers(), json=payload, timeout=30)
    if r.status_code >= 400:
        log.error("Notion API error %s: %s", r.status_code, r.text[:500])
        r.raise_for_status()
    return r.json()


def _patch(path: str, payload: dict) -> dict:
    r = requests.patch(f"{NOTION_API}{path}", headers=_headers(), json=payload, timeout=30)
    if r.status_code >= 400:
        log.error("Notion API error %s: %s", r.status_code, r.text[:500])
        r.raise_for_status()
    return r.json()


def _get(path: str) -> dict:
    r = requests.get(f"{NOTION_API}{path}", headers=_headers(), timeout=30)
    if r.status_code >= 400:
        log.error("Notion API error %s: %s", r.status_code, r.text[:500])
        r.raise_for_status()
    return r.json()


# ─────────────────────────────────────────────────────────────────────
# DB schema — 회원에게 보여줄 properties
# ─────────────────────────────────────────────────────────────────────
DB_SCHEMA = {
    "Title": {"title": {}},
    "Agent": {
        "select": {
            "options": [
                {"name": "🎩 CEO", "color": "red"},
                {"name": "📚 curriculum", "color": "blue"},
                {"name": "🎬 producer", "color": "purple"},
                {"name": "📣 marketing", "color": "pink"},
                {"name": "🎓 success", "color": "green"},
                {"name": "🛠 site_developer", "color": "orange"},
                {"name": "🎨 ui_designer", "color": "yellow"},
                {"name": "📝 blog_publisher", "color": "brown"},
            ]
        }
    },
    "Kind": {
        "select": {
            "options": [
                {"name": "curriculum_outline", "color": "blue"},
                {"name": "lecture_script", "color": "purple"},
                {"name": "landing_copy", "color": "pink"},
                {"name": "faq", "color": "green"},
                {"name": "cx_resolution", "color": "green"},
                {"name": "blog_post", "color": "brown"},
                {"name": "design_variants", "color": "yellow"},
                {"name": "site_config_change", "color": "orange"},
                {"name": "daily_report", "color": "red"},
            ]
        }
    },
    "Status": {
        "select": {
            "options": [
                {"name": "pending", "color": "yellow"},
                {"name": "approved", "color": "green"},
                {"name": "rejected", "color": "red"},
            ]
        }
    },
    "Self Review": {
        "select": {
            "options": [
                {"name": "pass", "color": "green"},
                {"name": "warn", "color": "yellow"},
                {"name": "fail", "color": "red"},
            ]
        }
    },
    "Course ID": {"rich_text": {}},
    "Summary": {"rich_text": {}},
    "DRI": {"rich_text": {}},
    "HARD": {"number": {"format": "number"}},
    "SOFT": {"number": {"format": "number"}},
    "Created at": {"date": {}},
    "Result ID": {"rich_text": {}},  # 외부 ID — 중복 체크용
}


def setup_database() -> str:
    """부모 페이지에 산출물 데이터베이스 자동 생성 — 첫 실행에만."""
    if not NOTION_PARENT_PAGE_ID:
        raise RuntimeError(
            "NOTION_PARENT_PAGE_ID 환경변수 미설정 — .env 확인\n"
            "Notion에서 부모 페이지 URL의 마지막 32자(하이픈 제거)가 ID입니다."
        )

    payload = {
        "parent": {"type": "page_id", "page_id": NOTION_PARENT_PAGE_ID},
        "title": [{"type": "text", "text": {"content": "🌳 Core Campus — 산출물 인박스"}}],
        "icon": {"type": "emoji", "emoji": "🌳"},
        "properties": DB_SCHEMA,
    }
    res = _post("/databases", payload)
    db_id = res["id"]
    DB_ID_FILE.parent.mkdir(parents=True, exist_ok=True)
    DB_ID_FILE.write_text(db_id, encoding="utf-8")
    log.info("✅ Notion DB 생성 완료: %s", db_id)
    return db_id


def get_or_create_db() -> str:
    if DB_ID_FILE.exists():
        db_id = DB_ID_FILE.read_text(encoding="utf-8").strip()
        try:
            _get(f"/databases/{db_id}")
            return db_id
        except Exception:
            log.warning("기존 DB ID 무효 — 새로 생성합니다")
    return setup_database()


# ─────────────────────────────────────────────────────────────────────
# 산출물 → Notion 페이지 변환
# ─────────────────────────────────────────────────────────────────────
AGENT_LABEL = {
    "ceo": "🎩 CEO",
    "curriculum": "📚 curriculum",
    "producer": "🎬 producer",
    "marketing": "📣 marketing",
    "success": "🎓 success",
    "site_developer": "🛠 site_developer",
    "ui_designer": "🎨 ui_designer",
    "blog_publisher": "📝 blog_publisher",
}


def _truncate(s: str, n: int = 1900) -> str:
    if not isinstance(s, str):
        return ""
    return s[:n] if len(s) > n else s


def _md_to_blocks(md: str) -> list[dict]:
    """간단한 마크다운 → Notion blocks 변환.

    Notion API 페이지 생성 시 children 배열에 들어감.
    H1·H2·H3·bullet·numbered·paragraph 정도만 처리.
    한 페이지 최대 100 블록 제한 — 넘으면 잘림.
    """
    blocks = []
    lines = (md or "").split("\n")
    i = 0
    while i < len(lines) and len(blocks) < 95:
        line = lines[i].rstrip()
        if not line.strip():
            i += 1
            continue

        if line.startswith("# "):
            blocks.append(_text_block("heading_1", line[2:].strip()))
        elif line.startswith("## "):
            blocks.append(_text_block("heading_2", line[3:].strip()))
        elif line.startswith("### "):
            blocks.append(_text_block("heading_3", line[4:].strip()))
        elif line.startswith("- ") or line.startswith("* "):
            blocks.append(_text_block("bulleted_list_item", line[2:].strip()))
        elif line.startswith("> "):
            blocks.append(_text_block("quote", line[2:].strip()))
        elif line.startswith("|") and "|" in line[1:]:
            # 표는 그대로 paragraph로 (Notion table 변환은 복잡)
            blocks.append(_text_block("paragraph", line))
        else:
            blocks.append(_text_block("paragraph", line))
        i += 1

    if len(lines) > 95 and len(blocks) >= 95:
        blocks.append(_text_block("paragraph",
            "⋯ (본문이 길어 일부 생략 — 원본은 content/approved/{id}.json)"))
    return blocks


def _text_block(block_type: str, text: str) -> dict:
    return {
        "object": "block",
        "type": block_type,
        block_type: {
            "rich_text": [{"type": "text", "text": {"content": _truncate(text)}}]
        },
    }


def _extract_dri(body_md: str) -> str:
    """body 안에 DRI 명시가 있으면 추출. 없으면 빈 문자열."""
    import re
    for pat in [r"DRI[:\s]*([^\n]+)", r"책임자[:\s]*([^\n]+)"]:
        m = re.search(pat, body_md or "", re.IGNORECASE)
        if m:
            return m.group(1).strip()[:80]
    return ""


def _make_properties(result: dict, status: str) -> dict:
    """AgentResult JSON → Notion DB properties."""
    meta = result.get("meta") or {}
    sr = meta.get("self_review") or {}
    severity = sr.get("severity") or "pass"

    return {
        "Title": {"title": [{"type": "text", "text": {"content": _truncate(result.get("title") or "(제목 없음)", 200)}}]},
        "Agent": {"select": {"name": AGENT_LABEL.get(result.get("agent") or "", result.get("agent") or "?")}},
        "Kind": {"select": {"name": result.get("kind") or "?"}},
        "Status": {"select": {"name": status}},
        "Self Review": {"select": {"name": severity}},
        "Course ID": {"rich_text": [{"type": "text", "text": {"content": _truncate(result.get("course_id") or "", 80)}}]},
        "Summary": {"rich_text": [{"type": "text", "text": {"content": _truncate(result.get("summary") or "", 200)}}]},
        "DRI": {"rich_text": [{"type": "text", "text": {"content": _truncate(_extract_dri(result.get("body_md") or ""), 80)}}]},
        "HARD": {"number": len(sr.get("hard_violations") or [])},
        "SOFT": {"number": len(sr.get("soft_violations") or [])},
        "Created at": {"date": {"start": result.get("created_at") or datetime.now().isoformat(timespec="seconds")}},
        "Result ID": {"rich_text": [{"type": "text", "text": {"content": _truncate(result.get("id") or "", 100)}}]},
    }


def _find_existing_page(db_id: str, result_id: str) -> str | None:
    """Result ID 기준 중복 체크. 있으면 page_id 반환."""
    try:
        res = _post(f"/databases/{db_id}/query", {
            "filter": {"property": "Result ID", "rich_text": {"equals": result_id}},
            "page_size": 1,
        })
        results = res.get("results") or []
        return results[0]["id"] if results else None
    except Exception as e:
        log.warning("중복 체크 실패: %s", e)
        return None


def sync_result(db_id: str, result: dict, status: str) -> bool:
    """1건 산출물을 Notion에 sync. 새 페이지 또는 update."""
    result_id = result.get("id") or ""
    if not result_id:
        log.warning("Result ID 없음 — skip: %s", result.get("title", "?"))
        return False

    existing_page_id = _find_existing_page(db_id, result_id)
    properties = _make_properties(result, status)

    if existing_page_id:
        # update — properties만 갱신, content는 그대로
        _patch(f"/pages/{existing_page_id}", {"properties": properties})
        log.info("✏️  update %s — %s", result_id[:8], result.get("title", "?")[:50])
        return False
    else:
        # 신규 페이지 — properties + body blocks
        blocks = _md_to_blocks(result.get("body_md") or "")
        _post("/pages", {
            "parent": {"database_id": db_id},
            "properties": properties,
            "children": blocks,
        })
        log.info("✅ create %s — %s", result_id[:8], result.get("title", "?")[:50])
        return True


# ─────────────────────────────────────────────────────────────────────
# 메인
# ─────────────────────────────────────────────────────────────────────
def iterate_results(include_pending: bool, include_approved: bool, include_rejected: bool):
    if include_approved and APPROVED_DIR.exists():
        for p in sorted(APPROVED_DIR.glob("*.json")):
            try:
                yield (json.loads(p.read_text(encoding="utf-8")), "approved")
            except Exception as e:
                log.warning("skip %s — %s", p.name, e)

    if include_pending and PENDING_DIR.exists():
        for p in sorted(PENDING_DIR.glob("*.json")):
            try:
                yield (json.loads(p.read_text(encoding="utf-8")), "pending")
            except Exception as e:
                log.warning("skip %s — %s", p.name, e)

    if include_rejected and REJECTED_DIR.exists():
        for p in sorted(REJECTED_DIR.glob("*.json")):
            try:
                yield (json.loads(p.read_text(encoding="utf-8")), "rejected")
            except Exception as e:
                log.warning("skip %s — %s", p.name, e)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--setup", action="store_true", help="데이터베이스만 생성하고 종료")
    parser.add_argument("--pending", action="store_true", help="pending만 sync")
    parser.add_argument("--approved", action="store_true", help="approved만 sync (기본: approved + pending)")
    parser.add_argument("--rejected", action="store_true", help="rejected까지 포함")
    parser.add_argument("--all", action="store_true", help="approved + pending + rejected 모두")
    parser.add_argument("--limit", type=int, default=0, help="최대 N건만 sync (0=무제한)")
    args = parser.parse_args()

    # 환경변수 체크
    if not NOTION_TOKEN:
        print("❌ NOTION_TOKEN 미설정. README의 Notion Integration 가이드를 따라주세요.")
        return 1
    if not NOTION_PARENT_PAGE_ID and not DB_ID_FILE.exists():
        print("❌ NOTION_PARENT_PAGE_ID 미설정.")
        print("   Notion에서 부모 페이지 URL 끝 32자(하이픈 빼고)를 .env에 추가하세요.")
        return 1

    # DB 확보 또는 생성
    db_id = get_or_create_db()
    print(f"📊 Notion DB ID: {db_id}")

    if args.setup:
        print("✅ Setup 완료. 다음 실행부터 산출물 sync됩니다.")
        return 0

    # 어떤 폴더를 sync 할지
    include_pending = args.pending or args.all or not (args.approved or args.rejected)
    include_approved = args.approved or args.all or not (args.pending or args.rejected)
    include_rejected = args.rejected or args.all

    created = 0
    updated = 0
    count = 0
    for result, status in iterate_results(include_pending, include_approved, include_rejected):
        if args.limit and count >= args.limit:
            break
        try:
            is_new = sync_result(db_id, result, status)
            if is_new:
                created += 1
            else:
                updated += 1
            count += 1
        except Exception as e:
            log.error("sync 실패 %s — %s", result.get("id", "?"), e)
            continue

    print()
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"  ✅ Notion 동기화 완료")
    print(f"     신규 페이지: {created}건")
    print(f"     업데이트:   {updated}건")
    print(f"     총 처리:    {count}건")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"  📱 모바일 Notion 앱에서 'Core Campus 산출물' 확인")
    return 0


if __name__ == "__main__":
    sys.exit(main())
