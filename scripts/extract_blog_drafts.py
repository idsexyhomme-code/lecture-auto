"""approved/의 blog_post 결과물을 한 페이지로 모아서 회원님이 복붙으로 티스토리에 게시 가능하게.

티스토리 자동 게시는 셀렉터 변경 등으로 실패해도 *글 본문은 이미 다 작성*되어 있음.
이 스크립트가 그것을 site/blog-drafts/index.html로 묶어서:
    1. 각 글의 *제목 + HTML 본문* 보임
    2. *복사* 버튼 클릭 → 클립보드로 본문 들어감
    3. 회원님이 티스토리 쓰기 페이지에 붙여넣기 → 발행

실행:
    .venv/bin/python scripts/extract_blog_drafts.py
"""
from __future__ import annotations

import json
import os
import sys
from html import escape
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
APPROVED_DIR = REPO_ROOT / "content" / "approved"
OUT_DIR = REPO_ROOT / "site" / "blog-drafts"


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # 모든 blog_post 산출물 수집
    drafts = []
    for f in sorted(APPROVED_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if d.get("kind") != "blog_post":
            continue
        meta = d.get("meta") or {}
        drafts.append({
            "id": d.get("id"),
            "title": meta.get("title") or d.get("title", ""),
            "body_html": meta.get("body_html") or "",
            "tistory_status": meta.get("tistory_status", "?"),
            "tistory_url": meta.get("tistory_url"),
            "course_id": d.get("course_id", ""),
            "created_at": d.get("created_at", ""),
        })

    print(f"발견된 블로그 초안: {len(drafts)}개")
    if not drafts:
        print("approved/에 blog_post 산출물이 없습니다.")
        return

    # 같은 course_id는 최신만
    seen = set()
    unique_drafts = []
    for d in drafts:
        key = d["course_id"]
        if key in seen:
            continue
        seen.add(key)
        unique_drafts.append(d)

    print(f"unique 코스: {len(unique_drafts)}개")

    # HTML 페이지 생성
    cards = []
    for i, d in enumerate(unique_drafts, start=1):
        status_emoji = "✅" if d["tistory_status"] == "draft" else "⚠️"
        status_text = "티스토리 임시저장됨" if d["tistory_status"] == "draft" else f"자동 게시 실패 — *수동 복붙 필요*"
        cards.append(f"""
<div class="draft-card" data-idx="{i}">
  <div class="card-head">
    <h2>{escape(d["title"])}</h2>
    <span class="status">{status_emoji} {status_text}</span>
  </div>
  <div class="meta">course: <code>{escape(d["course_id"])}</code> · {escape(d["created_at"][:19])}</div>
  <div class="actions">
    <button class="copy-btn" onclick="copyBody({i})">📋 본문 복사 (클립보드)</button>
    <a class="action-btn" href="https://jejumomdad.tistory.com/manage/newpost/" target="_blank">→ 티스토리 새 글 쓰기</a>
    <button class="toggle-btn" onclick="toggleBody({i})">👁 본문 펼치기</button>
  </div>
  <div class="body" id="body-{i}" style="display:none">
    <div class="body-preview">
      {d["body_html"]}
    </div>
    <textarea class="body-source" id="source-{i}" readonly>{escape(d["body_html"])}</textarea>
  </div>
</div>
""")

    html = f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>코어 캠퍼스 — 블로그 초안 ({len(unique_drafts)}개)</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{ font-family: -apple-system, "Pretendard", sans-serif; background: #f6f7fb; color: #1a1a1a; margin: 0; padding: 20px; line-height: 1.55; }}
  .container {{ max-width: 900px; margin: 0 auto; }}
  h1 {{ color: #1A3558; font-size: 24px; margin-bottom: 8px; }}
  .subtitle {{ color: #6b7280; font-size: 14px; margin-bottom: 24px; }}
  .summary {{ background: #DBEAFE; border: 1px solid #93C5FD; padding: 12px 16px; border-radius: 8px; margin-bottom: 20px; font-size: 13px; }}

  .draft-card {{
    background: #fff; border: 1px solid #e5e7eb; border-radius: 12px;
    padding: 18px 22px; margin-bottom: 14px;
  }}
  .card-head {{ display: flex; justify-content: space-between; align-items: flex-start; gap: 10px; margin-bottom: 4px; }}
  .card-head h2 {{ font-size: 18px; margin: 0; color: #1A3558; }}
  .status {{ font-size: 11px; padding: 3px 10px; border-radius: 999px; background: #FEF3C7; color: #92400E; border: 1px solid #FCD34D; white-space: nowrap; }}
  .meta {{ font-size: 12px; color: #6b7280; margin-bottom: 12px; }}
  .meta code {{ background: #f3f4f6; padding: 1px 6px; border-radius: 3px; }}

  .actions {{ display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 12px; }}
  button, .action-btn {{
    padding: 7px 14px; border-radius: 6px; font-size: 12.5px; font-weight: 600;
    cursor: pointer; border: none; text-decoration: none;
  }}
  .copy-btn {{ background: #1A3558; color: #fff; }}
  .copy-btn:hover {{ background: #2C5282; }}
  .copy-btn.copied {{ background: #10B981; }}
  .action-btn {{ background: #fff; color: #1A3558; border: 1px solid #1A3558; }}
  .action-btn:hover {{ background: #1A3558; color: #fff; }}
  .toggle-btn {{ background: #f3f4f6; color: #1a1a1a; border: 1px solid #e5e7eb; }}
  .toggle-btn:hover {{ background: #e5e7eb; }}

  .body {{ border-top: 1px solid #e5e7eb; padding-top: 12px; margin-top: 8px; }}
  .body-preview {{ font-size: 14px; padding: 14px; background: #f9fafb; border-radius: 6px; max-height: 300px; overflow-y: auto; }}
  .body-source {{ display: block; width: 100%; height: 200px; padding: 10px; border: 1px solid #e5e7eb; border-radius: 6px; font-family: "SF Mono", monospace; font-size: 11px; margin-top: 8px; }}
</style>
</head>
<body>
<div class="container">
  <h1>📝 블로그 초안 ({len(unique_drafts)}개) — 코어 캠퍼스 자동 생산</h1>
  <p class="subtitle">자동 생산된 블로그 글들. 티스토리 자동 게시가 실패한 경우 *수동 복붙*으로 5분에 게시 가능.</p>

  <div class="summary">
    💡 <b>사용법:</b><br>
    1. 각 카드의 <b>📋 본문 복사</b> 클릭 (클립보드에 HTML 들어감)<br>
    2. <b>→ 티스토리 새 글 쓰기</b> 버튼으로 새 탭 열기<br>
    3. 제목 카드의 제목 복사 → 티스토리 제목 입력란<br>
    4. 티스토리 에디터 *HTML 모드*로 전환 → 붙여넣기 → 발행<br>
    5. 5분 안에 6개 다 가능
  </div>

  {''.join(cards)}
</div>

<script>
async function copyBody(idx) {{
  const source = document.getElementById('source-' + idx);
  const text = source.value;
  try {{
    await navigator.clipboard.writeText(text);
    const btn = document.querySelector(`.draft-card[data-idx="${{idx}}"] .copy-btn`);
    btn.textContent = '✓ 복사됨';
    btn.classList.add('copied');
    setTimeout(() => {{
      btn.textContent = '📋 본문 복사 (클립보드)';
      btn.classList.remove('copied');
    }}, 2500);
  }} catch (e) {{
    // fallback: textarea select
    source.style.display = 'block';
    source.select();
    document.execCommand('copy');
    alert('복사됨 (fallback)');
  }}
}}

function toggleBody(idx) {{
  const body = document.getElementById('body-' + idx);
  body.style.display = body.style.display === 'none' ? 'block' : 'none';
}}
</script>
</body>
</html>
"""

    out_path = OUT_DIR / "index.html"
    out_path.write_text(html, encoding="utf-8")
    print(f"\n✓ 생성됨: {out_path}")
    print(f"  로컬 열기: open '{out_path}'")
    print(f"  사이트 URL (push 후): https://idsexyhomme-code.github.io/lecture-auto/blog-drafts/")


if __name__ == "__main__":
    main()
