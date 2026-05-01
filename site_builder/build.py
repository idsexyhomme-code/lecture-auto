"""approved/ 의 결과물을 site/*.html 로 빌드.

- index.html : 모든 코스의 카드 랜딩
- courses/<course_id>.html : 코스별 페이지 (커리큘럼 + 랜딩 카피 + FAQ 결합)
- posts/<id>.html : 단일 산출물(스크립트 등) 상세 페이지
"""
from __future__ import annotations

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

env = Environment(
    loader=FileSystemLoader(str(TEMPLATE_DIR)),
    autoescape=select_autoescape(["html"]),
)


def _md_to_html(s: str) -> str:
    return md_lib.markdown(s, extensions=["tables", "fenced_code"])


def _group_by_course(items: list[AgentResult]) -> dict[str, list[AgentResult]]:
    out: dict[str, list[AgentResult]] = defaultdict(list)
    for it in items:
        out[it.course_id or "_misc"].append(it)
    return out


def build():
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
        title = (curriculum.title if curriculum else (landing.title if landing else cid))
        tagline = (curriculum.meta.get("raw", {}).get("tagline") if curriculum else "") or \
                  (landing.meta.get("raw", {}).get("hero", {}).get("subhead") if landing else "")
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

    # 정적 자원(공통 CSS) 복사
    css_src = TEMPLATE_DIR / "styles.css"
    if css_src.exists():
        (SITE_DIR / "styles.css").write_text(css_src.read_text(encoding="utf-8"), encoding="utf-8")

    print(f"Built site with {len(courses)} course(s) and {len(posts)} post(s).")


def _render(template_name: str, out: Path, **ctx):
    out.parent.mkdir(parents=True, exist_ok=True)
    tpl = env.get_template(template_name)
    out.write_text(tpl.render(**ctx), encoding="utf-8")


if __name__ == "__main__":
    build()
