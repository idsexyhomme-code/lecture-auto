"""approved/ 의 결과물을 site/*.html 로 빌드.

- index.html : 모든 코스의 카드 랜딩
- courses/<course_id>.html : 코스별 페이지 (커리큘럼 + 랜딩 카피 + FAQ 결합)
- posts/<id>.html : 단일 산출물(스크립트 등) 상세 페이지
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import bleach
from bleach.css_sanitizer import CSSSanitizer
import markdown as md_lib
from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agents.base import APPROVED_DIR, PENDING_DIR, AgentResult  # noqa: E402

SITE_DIR = ROOT / "site"
TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
SITE_CONFIG_PATH = ROOT / "site_config.json"
DESIGN_PREVIEWS_DIR = SITE_DIR / "_design_previews"

DEFAULT_CONFIG = {
    "site_name": "강의 홈페이지",
    "site_tagline_top": "AI Agent × Human-in-the-Loop",
    "site_headline": "학습이 짧을수록, 결과는 또렷해집니다",
    "site_subtagline": "15분 안에 끝나는 단일 학습목표 · 실습 산출물 1개. AI 에이전트와 강사가 함께 설계한 강의들.",
    "course_order": [],
    "course_overrides": {},
    "design_tokens": {},
    # Tier 3
    "hero_html": "",
    "home_intro_html": "",
    "footer_html": "",
    # Tier 4
    "categories_html": "",
    "cta_html": "",
    "testimonials_html": "",
    "pricing_html": "",
    # Tier 5
    "extra_pages": [],
}

# Tier 3 — HTML 슬롯 sanitize 화이트리스트 (이중 방어 — build 단 2차)
_BLEACH_TAGS = [
    "div", "section", "p", "h1", "h2", "h3", "h4", "h5", "h6",
    "span", "strong", "em", "b", "i", "u", "br", "hr",
    "ul", "ol", "li", "a", "img", "button", "blockquote",
    "code", "figure", "figcaption", "small", "mark",
]
_BLEACH_ATTRS = {
    "*": ["class", "id", "title", "role", "style",
          "aria-label", "aria-labelledby", "aria-describedby", "aria-hidden"],
    "a": ["href", "target", "rel"],
    "img": ["src", "alt", "width", "height", "loading"],
    "button": ["type"],
}
_BLEACH_PROTOCOLS = ["http", "https", "mailto", "tel", "data"]
_BLEACH_CSS_PROPS = [
    "color", "background", "background-color", "background-image", "background-size",
    "background-position", "background-repeat",
    "font-size", "font-weight", "font-family", "font-style", "line-height", "letter-spacing",
    "text-align", "text-transform", "text-decoration",
    "padding", "padding-top", "padding-right", "padding-bottom", "padding-left",
    "margin", "margin-top", "margin-right", "margin-bottom", "margin-left",
    "border", "border-top", "border-bottom", "border-radius", "box-shadow",
    "display", "flex", "flex-direction", "flex-wrap", "justify-content", "align-items", "gap",
    "grid", "grid-template-columns", "grid-template-rows", "grid-gap",
    "width", "height", "max-width", "max-height", "min-width", "min-height",
    "opacity", "transform",
]


def _sanitize_html_slot(s: str) -> str:
    """build 단 2차 sanitize. site_developer 1차 sanitize 우회 시도까지 차단."""
    if not s or not isinstance(s, str):
        return ""
    css_sanitizer = CSSSanitizer(
        allowed_css_properties=_BLEACH_CSS_PROPS
    )
    return bleach.clean(
        s,
        tags=_BLEACH_TAGS,
        attributes=_BLEACH_ATTRS,
        protocols=_BLEACH_PROTOCOLS,
        css_sanitizer=css_sanitizer,
        strip=True,
    )

# design_tokens 키 → styles.css의 :root 변수명 매핑 (site_developer.py와 동일)
DESIGN_TOKEN_MAP = {
    "color_bg":         "--bg",
    "color_fg":         "--fg",
    "color_muted":      "--muted",
    "color_line":       "--line",
    "color_brand":      "--brand",
    "color_brand_2":    "--brand-2",
    "color_accent":     "--accent",
    "color_soft":       "--soft",
    "font_family_sans": "--font-family-sans",
    "radius_card":      "--radius-card",
}


def _render_tokens_css(tokens: dict) -> str:
    """design_tokens를 :root { --x: y; } 형태 CSS로 렌더 (없으면 빈 문자열)."""
    if not tokens:
        return ""
    rules = []
    for key, val in tokens.items():
        var = DESIGN_TOKEN_MAP.get(key)
        if not var or not isinstance(val, str) or not val.strip():
            continue
        # CSS injection 방지: 따옴표·중괄호 등 위험 문자 검사
        v = val.strip()
        if any(ch in v for ch in ("{", "}", ";", "<", ">")):
            continue
        rules.append(f"  {var}: {v};")
    if not rules:
        return ""
    return (
        "\n\n/* design_tokens — site_developer Tier 2 (overrides above) */\n"
        ":root {\n" + "\n".join(rules) + "\n}\n"
    )


def _detect_repo_owner_repo() -> tuple[str, str]:
    """GitHub Actions 환경 변수 GITHUB_REPOSITORY = 'owner/repo' 사용.
    로컬 빌드 시엔 .git/config에서 origin URL 파싱하거나 환경변수로.
    실패하면 ('', '') — admin.js가 작동 안 함.
    """
    import os, re
    repo_full = os.environ.get("GITHUB_REPOSITORY", "")
    if "/" in repo_full:
        owner, name = repo_full.split("/", 1)
        return owner, name
    # 로컬 fallback — .git/config 시도
    try:
        cfg = (ROOT / ".git" / "config").read_text(encoding="utf-8")
        m = re.search(r"github\.com[:/]([^/\s]+)/([^/\s.]+)", cfg)
        if m:
            return m.group(1), m.group(2)
    except Exception:
        pass
    return "", ""


def _load_site_config() -> dict:
    if not SITE_CONFIG_PATH.exists():
        return dict(DEFAULT_CONFIG)
    try:
        cfg = json.loads(SITE_CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return dict(DEFAULT_CONFIG)
    # 누락 키는 기본값으로 보완
    out = dict(DEFAULT_CONFIG)
    out.update({k: v for k, v in cfg.items() if k in DEFAULT_CONFIG})
    return out


env = Environment(
    loader=FileSystemLoader(str(TEMPLATE_DIR)),
    autoescape=select_autoescape(["html"]),
)
# 모든 템플릿에서 site_config 전역 사용 가능
env.globals["site_config"] = _load_site_config()


def _md_to_html(s: str) -> str:
    return md_lib.markdown(s, extensions=["tables", "fenced_code"])


def _group_by_course(items: list[AgentResult]) -> dict[str, list[AgentResult]]:
    out: dict[str, list[AgentResult]] = defaultdict(list)
    for it in items:
        out[it.course_id or "_misc"].append(it)
    return out


def build():
    # 빌드마다 최신 site_config 다시 읽기 (이전 빌드 이후 승인된 변경 반영)
    config = _load_site_config()
    # Tier 3 + Tier 4 — HTML 슬롯 2차 sanitize (defense in depth)
    for slot in (
        "hero_html", "home_intro_html", "footer_html",
        "categories_html", "cta_html", "testimonials_html", "pricing_html",
    ):
        if config.get(slot):
            config[slot] = _sanitize_html_slot(config[slot])
    # Tier 5 — extra_pages도 body_html 2차 sanitize
    for p in (config.get("extra_pages") or []):
        if isinstance(p, dict) and p.get("body_html"):
            p["body_html"] = _sanitize_html_slot(p["body_html"])
    env.globals["site_config"] = config
    overrides = config.get("course_overrides", {}) or {}

    items = [AgentResult.load(p) for p in sorted(APPROVED_DIR.glob("*.json"))]
    grouped = _group_by_course(items)

    # 코스 카드 데이터 구성
    courses = []
    for cid, group in grouped.items():
        if cid == "_misc":
            continue
        curriculum = next((g for g in group if g.kind == "curriculum_outline"), None)
        landing = next((g for g in group if g.kind == "landing_copy"), None)
        scripts = [g for g in group if g.kind == "lecture_script"]
        faqs = [g for g in group if g.kind == "faq"]
        base_title = (curriculum.title if curriculum else (landing.title if landing else cid))
        base_tagline = (curriculum.meta.get("raw", {}).get("tagline") if curriculum else "") or \
                       (landing.meta.get("raw", {}).get("hero", {}).get("subhead") if landing else "")
        # site_developer가 만든 오버라이드 적용
        ov = overrides.get(cid) or {}
        title = ov.get("title_override") or base_title
        tagline = ov.get("tagline_override") or base_tagline
        courses.append({
            "id": cid,
            "title": title,
            "tagline": tagline,
            "curriculum": curriculum,
            "landing": landing,
            "scripts": scripts,
            "faqs": faqs,
            "url": f"courses/{cid}.html",
        })
        # 코스 페이지 빌드
        _render(
            "course.html",
            SITE_DIR / "courses" / f"{cid}.html",
            course=courses[-1],
            md_to_html=_md_to_html,
            base_path="..",
        )

        # 짧은 URL redirect 페이지 — site/{cid}/index.html
        # 회원님이 lecture-auto/{cid}/ 로 가면 자동으로 lecture-auto/courses/{cid}.html 로 이동
        short_dir = SITE_DIR / cid
        short_dir.mkdir(parents=True, exist_ok=True)
        course_title = courses[-1]["title"]
        redirect_html = (
            '<!DOCTYPE html>\n'
            '<html lang="ko">\n<head>\n'
            '<meta charset="utf-8">\n'
            f'<meta http-equiv="refresh" content="0; url=../courses/{cid}.html">\n'
            f'<link rel="canonical" href="../courses/{cid}.html">\n'
            f'<title>{course_title}</title>\n'
            '<script>location.replace("../courses/' + cid + '.html");</script>\n'
            '</head>\n<body>\n'
            f'<p>이동 중... <a href="../courses/{cid}.html">{course_title}</a></p>\n'
            '</body>\n</html>'
        )
        (short_dir / "index.html").write_text(redirect_html, encoding="utf-8")

    # course_order 기반 정렬 (목록에 없는 코스는 뒤로)
    order = config.get("course_order") or []
    if order:
        order_map = {cid: i for i, cid in enumerate(order)}
        courses.sort(key=lambda c: order_map.get(c["id"], 9999))

    # 단일 포스트 상세 (스크립트 등)
    posts = []
    for it in items:
        if it.kind in ("lecture_script", "qna_draft"):
            posts.append({
                "id": it.id,
                "title": it.title,
                "agent": it.agent,
                "kind": it.kind,
                "course_id": it.course_id,
                "body_html": _md_to_html(it.body_md),
                "url": f"posts/{it.id}.html",
            })
            _render(
                "post.html",
                SITE_DIR / "posts" / f"{it.id}.html",
                post=posts[-1],
                base_path="..",
            )

    # 인덱스
    _render(
        "index.html",
        SITE_DIR / "index.html",
        courses=courses,
        posts=posts[:10],
        total_count=len(items),
        base_path=".",
    )

    # 정적 자원(공통 CSS) 복사 + design_tokens inject
    css_src = TEMPLATE_DIR / "styles.css"
    if css_src.exists():
        css_text = css_src.read_text(encoding="utf-8")
        # design_tokens가 있으면 끝에 :root 블록 추가 (CSS 캐스케이드로 우선 적용)
        css_text += _render_tokens_css(config.get("design_tokens") or {})
        (SITE_DIR / "styles.css").write_text(css_text, encoding="utf-8")

    # 어드민 모드 자원 복사 (admin.css 그대로, admin.js는 repo 정보 inject)
    admin_css_src = TEMPLATE_DIR / "admin.css"
    if admin_css_src.exists():
        (SITE_DIR / "admin.css").write_text(
            admin_css_src.read_text(encoding="utf-8"), encoding="utf-8"
        )
    admin_js_src = TEMPLATE_DIR / "admin.js"
    if admin_js_src.exists():
        owner, repo_name = _detect_repo_owner_repo()
        prefix = (
            "// auto-injected by build.py\n"
            f"window.__ADMIN_REPO_OWNER__ = {owner!r};\n"
            f"window.__ADMIN_REPO_NAME__  = {repo_name!r};\n"
            f"window.__ADMIN_BRANCH__     = 'main';\n\n"
        )
        (SITE_DIR / "admin.js").write_text(
            prefix + admin_js_src.read_text(encoding="utf-8"),
            encoding="utf-8",
        )

    # ui_designer가 만든 시안 미리보기 렌더 (pending에 있는 동안만)
    n_previews = _build_design_previews()
    if n_previews:
        print(f"Rendered {n_previews} design preview page(s).")

    print(f"Built site with {len(courses)} course(s) and {len(posts)} post(s).")


# ─────────────────────────────────────────────────────────────────────────
# ui_designer 시안 미리보기 렌더
# ─────────────────────────────────────────────────────────────────────────

DESIGN_PREVIEW_HTML = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>{title}</title>
<link rel="stylesheet" href="../../styles.css">
<style>
  /* 시안용 inline 토큰 — 본 사이트 토큰을 덮어씀 */
  :root {{
{token_rules}
  }}
  body {{ margin:0; padding:0; }}
  .design-preview-banner {{
    position:sticky; top:0; z-index:100;
    background:#111; color:#fff; padding:8px 16px;
    font:13px/1.4 system-ui, sans-serif;
    border-bottom:1px solid #333;
    display:flex; justify-content:space-between; align-items:center;
  }}
  .design-preview-banner .vid {{ background:#FFD600; color:#111; padding:2px 8px; border-radius:4px; font-weight:700; }}
  .design-preview-stage {{ padding:48px 0; background:var(--bg, #fff); min-height:80vh; }}
  .design-preview-stage > .wrap {{ max-width:1100px; margin:0 auto; padding:0 24px; }}
</style>
</head>
<body>
<div class="design-preview-banner">
  <span><span class="vid">{vid_upper}</span> · {variant_name} · <em style="opacity:.7">{vibe}</em></span>
  <span style="opacity:.6">target: {target}</span>
</div>
<section class="design-preview-stage" role="region" aria-label="디자인 시안 미리보기">
{slot_html}
</section>
</body>
</html>
"""


def _render_variant_preview(result_id: str, target: str, variant: dict) -> Path | None:
    """단일 variant 미리보기 HTML 파일 작성. 실패 시 None."""
    vid = variant.get("id")
    if not vid:
        return None

    raw_html = variant.get("html") or ""
    safe_html = _sanitize_html_slot(raw_html)
    if not safe_html.strip():
        return None

    # target=hero/home_intro/footer 외엔 같은 컨테이너 안에 그대로 넣음
    if target == "hero":
        slot_html = f'  <div class="wrap">\n{safe_html}\n  </div>'
    elif target in ("home_intro", "footer"):
        slot_html = f'  <div class="wrap">\n{safe_html}\n  </div>'
    else:  # landing_full 등
        slot_html = safe_html

    # design_tokens를 inline :root 변수로
    token_rules = []
    for k, v in (variant.get("design_tokens") or {}).items():
        var = DESIGN_TOKEN_MAP.get(k)
        if not var or not isinstance(v, str):
            continue
        v = v.strip()
        if any(ch in v for ch in ("{", "}", ";", "<", ">")):
            continue
        token_rules.append(f"    {var}: {v};")
    token_rules_str = "\n".join(token_rules) if token_rules else "    /* (no tokens) */"

    name = variant.get("name") or vid
    vibe = variant.get("vibe") or ""

    out_dir = DESIGN_PREVIEWS_DIR / result_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{vid}.html"

    out_path.write_text(
        DESIGN_PREVIEW_HTML.format(
            title=f"[{vid.upper()}] {name} — 시안 미리보기",
            token_rules=token_rules_str,
            vid_upper=vid.upper(),
            variant_name=_html_escape(name),
            vibe=_html_escape(vibe),
            target=target,
            slot_html=slot_html,
        ),
        encoding="utf-8",
    )
    return out_path


def _render_variant_index(result_id: str, target: str, variants: list[dict]) -> Path:
    """index.html — 시안 3개를 한 페이지에서 비교."""
    cards = []
    for v in variants:
        vid = v.get("id", "?")
        name = v.get("name", "")
        vibe = v.get("vibe", "")
        cards.append(
            f'<a class="card" href="./{vid}.html" target="_blank" rel="noopener">'
            f'<h3>{vid.upper()} · {_html_escape(name)}</h3>'
            f'<p class="muted">{_html_escape(vibe)}</p>'
            f'<p style="color:var(--brand-2);font-size:14px">미리보기 →</p>'
            f'</a>'
        )

    page = f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>디자인 시안 — {result_id}</title>
<link rel="stylesheet" href="../../styles.css">
<style>
  body {{ padding:48px 24px; max-width:1000px; margin:0 auto; }}
  h1 {{ font-size:28px; margin:0 0 8px; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(280px,1fr)); gap:16px; margin-top:32px; }}
  .card {{ display:block; padding:24px; border:1px solid var(--line,#ddd); border-radius:12px; text-decoration:none; color:inherit; }}
  .card:hover {{ background:var(--soft,#f5f5f5); }}
  .card h3 {{ margin:0 0 8px; }}
</style>
</head><body>
<h1>디자인 시안 — target: {target}</h1>
<p class="muted">아래 3개 변형을 비교하고 텔레그램 카드에서 채택하실 시안을 선택하세요.</p>
<div class="grid">
{''.join(cards)}
</div>
</body></html>
"""
    out_path = DESIGN_PREVIEWS_DIR / result_id / "index.html"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(page, encoding="utf-8")
    return out_path


def _build_design_previews() -> int:
    """pending/*.json 중 kind=design_variants 항목들의 미리보기 페이지 렌더.

    return: 렌더된 *시안 결과* 개수 (한 결과 = 변형 N개).
    """
    if not PENDING_DIR.exists():
        return 0

    rendered = 0
    seen_ids: set[str] = set()

    for path in sorted(PENDING_DIR.glob("*.json")):
        try:
            r = AgentResult.load(path)
        except Exception:
            continue
        if r.kind != "design_variants":
            continue
        target = (r.meta or {}).get("target", "hero")
        variants = (r.meta or {}).get("variants") or []
        if not variants:
            continue

        seen_ids.add(r.id)
        for v in variants:
            try:
                _render_variant_preview(r.id, target, v)
            except Exception as e:
                print(f"[warn] variant preview failed {r.id}/{v.get('id')}: {e}")
        try:
            _render_variant_index(r.id, target, variants)
        except Exception as e:
            print(f"[warn] variant index failed {r.id}: {e}")
        rendered += 1

    # pending에서 이미 사라진 result_id의 미리보기 디렉토리는 정리
    if DESIGN_PREVIEWS_DIR.exists():
        for d in DESIGN_PREVIEWS_DIR.iterdir():
            if not d.is_dir():
                continue
            if d.name not in seen_ids:
                try:
                    import shutil
                    shutil.rmtree(d)
                except Exception:
                    pass

    return rendered


def _html_escape(s: str) -> str:
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def _render(template_name: str, out: Path, **ctx):
    out.parent.mkdir(parents=True, exist_ok=True)
    tpl = env.get_template(template_name)
    out.write_text(tpl.render(**ctx), encoding="utf-8")


if __name__ == "__main__":
    build()
