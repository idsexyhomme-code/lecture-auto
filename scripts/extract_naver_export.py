"""네이버 블로그 복붙 최적화 페이지 — 회원님이 5분에 5개 네이버 발행 가능.

출력: site/naver-export/index.html
요소 (각 글마다):
  📋 제목 (원클릭 복사)
  🖼 대표이미지 URL (원클릭 복사)
  📝 본문 HTML (네이버 스마트에디터 ONE — HTML 모드용)
  📝 본문 plain text (네이버 기본 에디터 — 줄바꿈 보존)
  🏷 추천 태그
  🔗 네이버 새 글 쓰기 바로가기

흐름:
    1. *네이버 새 글 쓰기* 클릭 → 새 탭
    2. 카드의 *제목 복사* → 네이버 제목란 붙여넣기
    3. 카드의 *대표이미지 URL 복사* → 네이버 이미지 첨부 (URL로 추가)
    4. 카드의 *본문 복사* (HTML 또는 plain) → 네이버 본문에 붙여넣기
    5. *태그 복사* → 네이버 태그란
    6. 발행

실행:
    .venv/bin/python scripts/extract_naver_export.py
"""
from __future__ import annotations

import json
import re
from html import escape, unescape
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
APPROVED_DIR = REPO_ROOT / "content" / "approved"
OUT_DIR = REPO_ROOT / "site" / "naver-export"


def html_to_plain(html: str) -> str:
    """HTML → 줄바꿈 보존된 plain text (네이버 기본 에디터용)."""
    s = html
    # 블록 요소 → 줄바꿈
    s = re.sub(r"</(p|div|h[1-6]|li|br|hr)>", "\n", s, flags=re.IGNORECASE)
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.IGNORECASE)
    s = re.sub(r"<li[^>]*>", "• ", s, flags=re.IGNORECASE)
    s = re.sub(r"<h[1-6][^>]*>", "\n## ", s, flags=re.IGNORECASE)
    # 이미지 → URL 표시
    s = re.sub(r'<img[^>]*src="([^"]+)"[^>]*>', r"\n[이미지: \1]\n", s, flags=re.IGNORECASE)
    # 모든 태그 제거
    s = re.sub(r"<[^>]+>", "", s)
    # HTML entity 복원
    s = unescape(s)
    # 연속 줄바꿈 정리
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # 모든 blog_post — course_id별 최신만
    seen = set()
    drafts = []
    for f in sorted(APPROVED_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if d.get("kind") != "blog_post":
            continue
        cid = d.get("course_id")
        if not cid or cid in seen:
            continue
        seen.add(cid)
        meta = d.get("meta") or {}
        body = meta.get("body_html", "")
        if not body:
            continue
        drafts.append({
            "course_id": cid,
            "title": meta.get("title") or d.get("title", ""),
            "body_html": body,
            "body_plain": html_to_plain(body),
            "hero_image_url": meta.get("hero_image_url", ""),
            "tistory_status": meta.get("tistory_status", "?"),
            "tistory_url": meta.get("tistory_url"),
            "scheduled_at": meta.get("scheduled_at"),
            "created_at": d.get("created_at", "")[:19],
        })

    cards_html = ""
    for i, d in enumerate(drafts, 1):
        status = d["tistory_status"]
        if status == "scheduled":
            badge = '<span class="badge ok">티스토리 예약됨</span>'
        elif status == "draft" and d.get("tistory_url"):
            badge = '<span class="badge ok">티스토리 발행됨</span>'
        elif status == "ignored_old_failure":
            continue  # 옛 실패 — 표시 X
        else:
            badge = '<span class="badge pending">티스토리 미발행</span>'

        sched = ""
        if d.get("scheduled_at"):
            sched = f'<span class="meta-time">📅 {d["scheduled_at"][:16].replace("T", " ")}</span>'

        img_block = ""
        if d.get("hero_image_url"):
            img_block = f"""
            <div class="block">
              <div class="block-head"><span class="block-label">🖼 대표 이미지 URL</span>
                <button class="btn copy" data-target="img-{i}">📋 복사</button>
              </div>
              <input class="text-input" id="img-{i}" readonly value="{escape(d['hero_image_url'])}">
              <img class="preview" src="{escape(d['hero_image_url'])}" alt="">
            </div>
            """

        tags = ["Claude", "1인 사업가", "코어 캠퍼스", d["course_id"]]
        tags_str = ", ".join(tags)

        cards_html += f"""
        <article class="card" data-idx="{i}">
          <header class="card-head">
            <h2>{escape(d['title'])}</h2>
            <div class="head-meta">
              {badge}
              {sched}
              <code>{escape(d['course_id'])}</code>
            </div>
          </header>

          <div class="actions-bar">
            <a class="btn primary" href="https://blog.naver.com/PostWriteForm.naver?blogId=&Redirect=Write" target="_blank" rel="noopener">→ 네이버 새 글 쓰기</a>
            <a class="btn secondary" href="https://blog.naver.com" target="_blank" rel="noopener">📂 네이버 블로그 홈</a>
          </div>

          <div class="block">
            <div class="block-head"><span class="block-label">📋 제목</span>
              <button class="btn copy" data-target="title-{i}">📋 복사</button>
            </div>
            <input class="text-input" id="title-{i}" readonly value="{escape(d['title'])}">
          </div>

          {img_block}

          <div class="block">
            <div class="block-head"><span class="block-label">📝 본문 (네이버 기본 에디터 — plain text)</span>
              <button class="btn copy" data-target="plain-{i}">📋 복사</button>
            </div>
            <textarea class="textarea-plain" id="plain-{i}" readonly>{escape(d['body_plain'])}</textarea>
          </div>

          <div class="block">
            <div class="block-head"><span class="block-label">📝 본문 (스마트에디터 ONE — HTML 모드)</span>
              <button class="btn copy" data-target="html-{i}">📋 복사</button>
            </div>
            <textarea class="textarea-html" id="html-{i}" readonly>{escape(d['body_html'])}</textarea>
          </div>

          <div class="block">
            <div class="block-head"><span class="block-label">🏷 추천 태그</span>
              <button class="btn copy" data-target="tags-{i}">📋 복사</button>
            </div>
            <input class="text-input" id="tags-{i}" readonly value="{escape(tags_str)}">
          </div>

          <details class="preview-toggle">
            <summary>🔍 본문 미리보기</summary>
            <div class="preview-body">{d['body_html']}</div>
          </details>
        </article>
        """

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>네이버 복붙 페이지 — {len(drafts)}개</title>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
  background: #FAF7F2; color: #1A1A1A;
  font-family: -apple-system, "Pretendard", sans-serif;
  line-height: 1.55; padding: 24px 20px 60px;
  max-width: 920px; margin: 0 auto;
}}
header.page {{ margin-bottom: 20px; padding-bottom: 14px; border-bottom: 2px solid #1A3558; }}
h1.page {{ font-size: 22px; color: #1A3558; margin-bottom: 6px; }}
.subtitle {{ font-size: 13px; color: #6B5C4A; }}
.note {{
  background: #DBEAFE; border: 1px solid #93C5FD; border-radius: 8px;
  padding: 12px 16px; margin: 16px 0 24px; font-size: 13px; line-height: 1.7;
}}

.card {{
  background: #FFFDFA; border: 1px solid #E8DDC9; border-radius: 12px;
  padding: 18px 22px; margin-bottom: 18px;
}}
.card-head {{ margin-bottom: 14px; padding-bottom: 10px; border-bottom: 1px solid #E8DDC9; }}
.card-head h2 {{ font-size: 16px; color: #1A3558; margin-bottom: 6px; }}
.head-meta {{ display: flex; gap: 10px; align-items: center; font-size: 12px; flex-wrap: wrap; }}
.head-meta code {{ background: #F5EFE0; padding: 1px 6px; border-radius: 3px; font-family: "SF Mono", monospace; }}
.meta-time {{ color: #6B5C4A; }}
.badge {{
  font-size: 11px; padding: 3px 10px; border-radius: 999px; font-weight: 600;
}}
.badge.ok {{ background: #D4EDDA; color: #155724; border: 1px solid #C3E6CB; }}
.badge.pending {{ background: #FEF3C7; color: #92400E; border: 1px solid #FCD34D; }}

.actions-bar {{ display: flex; gap: 8px; margin-bottom: 14px; }}
.btn {{
  padding: 7px 14px; border-radius: 6px; font-size: 12.5px; font-weight: 600;
  cursor: pointer; border: none; text-decoration: none; display: inline-block;
}}
.btn.primary {{ background: #03C75A; color: white; }} /* 네이버 그린 */
.btn.primary:hover {{ background: #02A148; }}
.btn.secondary {{ background: #fff; color: #03C75A; border: 1px solid #03C75A; }}
.btn.copy {{ background: #1A3558; color: white; padding: 4px 10px; font-size: 11px; }}
.btn.copy:hover {{ background: #2C5282; }}
.btn.copy.copied {{ background: #10B981; }}

.block {{ margin-bottom: 14px; }}
.block-head {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }}
.block-label {{ font-size: 12px; font-weight: 600; color: #1A3558; }}

.text-input {{
  width: 100%; padding: 8px 12px; font-size: 13px;
  background: #F9F7F2; border: 1px solid #E8DDC9; border-radius: 6px;
  font-family: "SF Mono", monospace;
}}
.textarea-plain {{
  width: 100%; height: 180px; padding: 10px 12px; font-size: 12px;
  background: #F9F7F2; border: 1px solid #E8DDC9; border-radius: 6px;
  font-family: -apple-system, sans-serif; line-height: 1.5;
}}
.textarea-html {{
  width: 100%; height: 120px; padding: 10px 12px; font-size: 11px;
  background: #F9F7F2; border: 1px solid #E8DDC9; border-radius: 6px;
  font-family: "SF Mono", monospace; line-height: 1.4;
}}
.preview {{ max-width: 100%; height: auto; border-radius: 6px; margin-top: 8px; max-height: 200px; }}

.preview-toggle {{ margin-top: 10px; padding-top: 10px; border-top: 1px solid #F5EFE0; }}
.preview-toggle summary {{ cursor: pointer; padding: 6px 10px; background: #F5EFE0; border-radius: 4px; font-size: 12px; font-weight: 600; }}
.preview-body {{ padding: 14px; margin-top: 8px; background: #fffdfa; border-radius: 6px; max-height: 400px; overflow-y: auto; font-size: 13px; line-height: 1.7; }}
.preview-body img {{ max-width: 100%; height: auto; border-radius: 6px; }}
.preview-body h2, .preview-body h3 {{ color: #1A3558; margin: 12px 0 6px; font-size: 15px; }}
.preview-body p {{ margin-bottom: 8px; }}

.summary-bar {{
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px;
  margin-bottom: 24px;
}}
.stat {{
  background: #FFFDFA; border: 1px solid #E8DDC9; border-radius: 10px;
  padding: 14px; text-align: center;
}}
.stat-num {{ font-size: 22px; font-weight: 700; color: #1A3558; }}
.stat-label {{ font-size: 11px; color: #6B5C4A; margin-top: 4px; }}
</style>
</head>
<body>

<header class="page">
  <h1 class="page">📰 네이버 블로그 복붙 페이지</h1>
  <div class="subtitle">티스토리 = 자동 SEO 미끼 · 네이버 = 회원님 본진 (수동 복붙 5분/글)</div>
</header>

<div class="summary-bar">
  <div class="stat"><div class="stat-num">{len(drafts)}</div><div class="stat-label">발행 가능 글</div></div>
  <div class="stat"><div class="stat-num">{sum(1 for d in drafts if d['tistory_status'] in ('scheduled', 'draft'))}</div><div class="stat-label">티스토리 라이브</div></div>
  <div class="stat"><div class="stat-num">5분</div><div class="stat-label">글 1개당 복붙</div></div>
</div>

<div class="note">
  <b>워크플로우:</b><br>
  1. <b>→ 네이버 새 글 쓰기</b> 클릭 (새 탭) → 회원님 네이버 블로그 에디터 열림<br>
  2. <b>📋 제목 복사</b> → 네이버 제목 영역에 붙여넣기<br>
  3. <b>📋 대표 이미지 URL 복사</b> → 네이버 사진 추가 (URL로 첨부)<br>
  4. <b>📝 본문 복사</b> (plain 권장) → 네이버 본문 영역에 붙여넣기<br>
  5. <b>🏷 태그 복사</b> → 네이버 태그란<br>
  6. 발행 — 글 1개당 약 3-5분
</div>

{cards_html}

<script>
async function copyToClipboard(text, btn) {{
  try {{
    await navigator.clipboard.writeText(text);
  }} catch (e) {{
    // fallback
    const ta = document.createElement('textarea');
    ta.value = text;
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    document.body.removeChild(ta);
  }}
  if (btn) {{
    const orig = btn.textContent;
    btn.textContent = '✓ 복사됨';
    btn.classList.add('copied');
    setTimeout(() => {{
      btn.textContent = orig;
      btn.classList.remove('copied');
    }}, 1800);
  }}
}}

document.querySelectorAll('.btn.copy').forEach(btn => {{
  btn.addEventListener('click', () => {{
    const target = document.getElementById(btn.dataset.target);
    if (target) copyToClipboard(target.value || target.textContent, btn);
  }});
}});
</script>

</body>
</html>
"""

    out_path = OUT_DIR / "index.html"
    out_path.write_text(html, encoding="utf-8")
    print(f"✓ {len(drafts)}개 글 → {out_path}")
    print(f"  사이트 URL: https://idsexyhomme-code.github.io/lecture-auto/naver-export/")
    print(f"  로컬: open '{out_path}'")


if __name__ == "__main__":
    main()
