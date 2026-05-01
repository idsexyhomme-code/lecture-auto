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

import markdown as md_lib
from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agents.base import APPROVED_DIR, AgentResult  # noqa: E402

SITE_DIR = ROOT / "site"
TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
SITE_CONFIG_PATH = ROOT / "site_config.json"

DEFAULT_CONFIG = {
    "site_name": "강의 홈페이지",
    "site_tagline_top": "AI Agent × Human-in-the-Loop",
    "site_headline": "학습이 짧을수록, 결과는 또렷해집니다",
    "site_subtagline": "15분 안에 끝나는 단일 학습목표 · 실습 산출물 1개. AI 에이전트와 강사가 함께 설계한 강의들.",
    "course_order": [],
    "course_overrides": {},
    "design_tokens": {},
}

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

    print(f"Built site with {len(courses)} course(s) and {len(posts)} post(s).")


def _render(template_name: str, out: Path, **ctx):
    out.parent.mkdir(parents=True, exist_ok=True)
    tpl = env.get_template(template_name)
    out.write_text(tpl.render(**ctx), encoding="utf-8")


if __name__ == "__main__":
    build()
