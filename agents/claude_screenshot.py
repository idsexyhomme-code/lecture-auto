"""Claude 대화창 '실제 화면 캡처' 생성기.

블로그에 넣을 진짜 정보성 이미지를 만든다:
    프롬프트 → 실제 Claude API 답변 → claude.ai 풍 대화창 HTML 렌더 → headless Chrome 캡처 → PNG

저장: site/blog-images/{slug}.png  (다른 hero 이미지와 같은 폴더)
공개 URL: raw.githubusercontent.com/{owner}/{repo}/main/site/blog-images/{slug}.png
          (이미지 호스팅은 현재 방식 유지 — 회원 결정 2026-05-24)

사용:
    from agents.claude_screenshot import generate_claude_shot
    path, url = generate_claude_shot(
        prompt="지금부터 60분 동안 기획서 서론만 쓸 거야. ...",
        slug="deepwork-1hr-shot1",
    )
"""
from __future__ import annotations

import html
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
SITE_IMAGES_DIR = REPO_ROOT / "site" / "blog-images"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

try:
    from dotenv import load_dotenv
    load_dotenv(REPO_ROOT / ".env")
except ImportError:
    pass


# ── 공개 URL (raw.githubusercontent 핫링크 — 기존 방식) ──────────────
def _pages_raw_base() -> str:
    owner = os.environ.get("GH_OWNER", "idsexyhomme-code")
    repo = os.environ.get("GH_REPO", "lecture-auto")
    branch = os.environ.get("GH_BRANCH", "main")
    return f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/site"


# ── 마크다운 → 간단 HTML (Claude 답변 렌더용) ────────────────────────
def _md_to_html(text: str) -> str:
    text = text.strip()
    out: list[str] = []
    list_buf: list[str] = []
    list_type: Optional[str] = None

    def flush_list():
        nonlocal list_buf, list_type
        if list_buf:
            tag = list_type or "ul"
            items = "".join(f"<li>{li}</li>" for li in list_buf)
            out.append(f'<{tag} style="margin:8px 0 12px;padding-left:22px">{items}</{tag}>')
            list_buf = []
            list_type = None

    def inline(s: str) -> str:
        s = html.escape(s)
        s = re.sub(r"\*\*(.+?)\*\*", r'<strong>\1</strong>', s)
        s = re.sub(r"`(.+?)`", r'<code style="background:#f0eee6;padding:1px 5px;border-radius:4px;font-size:0.92em">\1</code>', s)
        return s

    for raw in text.split("\n"):
        line = raw.rstrip()
        if not line.strip():
            flush_list()
            continue
        m_ol = re.match(r"^\s*\d+[\.\)]\s+(.*)", line)
        m_ul = re.match(r"^\s*[-•*]\s+(.*)", line)
        m_h = re.match(r"^(#{1,3})\s+(.*)", line)
        if m_h:
            flush_list()
            out.append(f'<p style="font-weight:700;margin:14px 0 6px">{inline(m_h.group(2))}</p>')
        elif m_ol:
            if list_type not in (None, "ol"):
                flush_list()
            list_type = "ol"
            list_buf.append(inline(m_ol.group(1)))
        elif m_ul:
            if list_type not in (None, "ul"):
                flush_list()
            list_type = "ul"
            list_buf.append(inline(m_ul.group(1)))
        else:
            flush_list()
            out.append(f'<p style="margin:0 0 12px">{inline(line)}</p>')
    flush_list()
    return "\n".join(out)


# ── claude.ai 풍 대화창 HTML ─────────────────────────────────────────
CLAUDE_MARK = (
    '<svg width="22" height="22" viewBox="0 0 24 24" fill="#d97757" '
    'xmlns="http://www.w3.org/2000/svg"><path d="M12 2c.3 3.1.9 4.7 2.1 5.9C15.3 9.1 16.9 9.7 20 '
    '10v4c-3.1.3-4.7.9-5.9 2.1C12.9 17.3 12.3 18.9 12 22c-.3-3.1-.9-4.7-2.1-5.9C8.7 14.9 7.1 14.3 '
    '4 14v-4c3.1-.3 4.7-.9 5.9-2.1C11.1 6.7 11.7 5.1 12 2z"/></svg>'
)


def _render_chat(prompt: str, response_md: str) -> str:
    prompt_html = html.escape(prompt).replace("\n", "<br>")
    resp_html = _md_to_html(response_md)
    return f"""<!doctype html><html lang="ko"><head><meta charset="utf-8">
<style>
  *{{box-sizing:border-box}}
  body{{margin:0;background:#ffffff;
       font-family:'Apple SD Gothic Neo',-apple-system,'Segoe UI',ui-sans-serif,sans-serif;
       -webkit-font-smoothing:antialiased}}
  .wrap{{width:760px;padding:30px 34px}}
  .user-row{{display:flex;justify-content:flex-end;margin-bottom:24px}}
  .user-bubble{{background:#f0eee6;color:#1f1d1a;border-radius:16px;padding:13px 17px;
       font-size:16px;line-height:1.6;max-width:80%;white-space:pre-wrap}}
  .claude-row{{display:flex;gap:12px;align-items:flex-start}}
  .claude-ic{{flex-shrink:0;margin-top:2px}}
  .claude-msg{{color:#1f1d1a;font-size:16px;line-height:1.72;flex:1}}
  .claude-msg p{{margin:0 0 12px}}
  .claude-msg strong{{font-weight:700}}
  .claude-name{{font-size:13px;color:#8a8578;font-weight:600;margin-bottom:4px}}
</style></head><body>
<div class="wrap">
  <div class="user-row"><div class="user-bubble">{prompt_html}</div></div>
  <div class="claude-row">
    <div class="claude-ic">{CLAUDE_MARK}</div>
    <div class="claude-msg"><div class="claude-name">Claude</div>{resp_html}</div>
  </div>
</div>
</body></html>"""


# ── headless 캡처 + 아래 여백 크롭 ───────────────────────────────────
def _capture(html_str: str, slug: str, width: int = 760, scale: int = 2) -> Path:
    from PIL import Image

    SITE_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
        f.write(html_str)
        tmp_html = f.name

    raw_png = Path(tempfile.gettempdir()) / f"{slug}_raw.png"
    subprocess.run(
        [CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
         f"--force-device-scale-factor={scale}",
         f"--window-size={width},2600", f"--screenshot={raw_png}", tmp_html],
        check=True, capture_output=True,
    )

    # 아래 흰 여백 잘라내기 — 흰색(>=250)이 아닌 마지막 행을 찾는다
    img = Image.open(raw_png).convert("RGB")
    w, h = img.size
    px = img.load()
    bg = px[2, 2]  # 좌상단 = 배경(흰색)
    bottom = 0
    step = max(1, w // 60)  # 가로 표본만 검사 (속도)
    for y in range(h - 1, -1, -1):
        row_has_content = False
        for x in range(0, w, step):
            r, g, b = px[x, y]
            if abs(r - bg[0]) > 12 or abs(g - bg[1]) > 12 or abs(b - bg[2]) > 12:
                row_has_content = True
                break
        if row_has_content:
            bottom = y
            break
    pad = 28 * scale
    crop_h = min(h, bottom + pad)
    cropped = img.crop((0, 0, w, crop_h))

    out_path = SITE_IMAGES_DIR / f"{slug}.png"
    cropped.save(out_path)
    try:
        os.unlink(tmp_html)
        os.unlink(raw_png)
    except OSError:
        pass
    return out_path


# ── Claude API로 실제 답변 받기 ──────────────────────────────────────
def _get_response(prompt: str, model: Optional[str] = None, max_tokens: int = 700) -> str:
    from anthropic import Anthropic

    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    model = model or os.environ.get("WORKER_MODEL", "claude-sonnet-4-6")
    system = (
        "너는 한국 1인 사업가를 돕는 Claude다. 사용자의 요청에 실제로 바로 쓸 수 있게, "
        "짧고 구체적으로 한국어로 답한다. 군더더기 인사말·메타발언 없이 본론부터. "
        "필요하면 번호 목록·굵은 글씨로 정리. 6~12줄 분량."
    )
    msg = client.messages.create(
        model=model, max_tokens=max_tokens,
        system=system, messages=[{"role": "user", "content": prompt}],
    )
    return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()


# ── 공개 진입점 ──────────────────────────────────────────────────────
def generate_claude_shot(
    prompt: str, slug: str, *, response: Optional[str] = None, model: Optional[str] = None
) -> tuple[Path, str]:
    """프롬프트로 실제 Claude 답변을 받아 대화창 캡처 PNG를 만든다.

    response를 직접 주면 API 호출 없이 그 내용으로 렌더(테스트·고정 답변용).
    반환: (저장 경로, 공개 raw URL)
    """
    resp_md = response if response is not None else _get_response(prompt, model=model)
    html_str = _render_chat(prompt, resp_md)
    path = _capture(html_str, slug)
    url = f"{_pages_raw_base()}/blog-images/{path.name}"
    return path, url


if __name__ == "__main__":
    # 빠른 수동 테스트
    p, u = generate_claude_shot(
        "지금부터 60분 동안 기획서 서론만 쓸 거야. 60분을 20분 3덩어리로 쪼개서, 각 덩어리에 뭘 끝내야 하는지 알려줘.",
        "manual-test-shot",
    )
    print("saved:", p)
    print("url:", u)
