"""돈 주고 생성된 산출물(content/approved)을 사람이 바로 쓰는 자산으로 추출.

흩어진 JSON 568개 + 블로그 이미지 28장을 강의별로 묶어 마크다운으로 내보낸다.
출력: ../_복구자산_2026-06-08/
"""
from __future__ import annotations

import glob
import json
import re
import shutil
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT.parent / "_복구자산_2026-06-08"

KIND_KR = {
    "lecture_script": "영상스크립트",
    "blog_post": "블로그글",
    "landing_copy": "랜딩카피",
    "curriculum_outline": "커리큘럼",
    "faq": "FAQ",
    "design_variants": "디자인시안",
    "qna_draft": "QnA",
    "ceo_daily_report": "CEO일일보고",
    "ceo_w1_step": "CEO주간계획",
    "ceo_w1_plan": "CEO주간계획",
    "ceo_first_setup": "CEO초기설정",
    "site_config_change": "사이트설정",
}


def slug(s: str, maxlen: int = 50) -> str:
    s = (s or "").strip().replace("\n", " ")
    s = re.sub(r'[\\/:*?"<>|]+', "_", s)      # 파일명 금지문자
    s = re.sub(r"\s+", " ", s).strip()
    return s[:maxlen] or "무제"


def body_of(d: dict) -> str:
    return (d.get("body_md") or d.get("body") or "").strip()


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    items = []
    for f in glob.glob(str(ROOT / "content/approved/*.json")):
        try:
            d = json.load(open(f, encoding="utf-8"))
        except Exception:
            continue
        items.append(d)

    # 강의별 그룹 (블로그·CEO보고는 별도)
    by_course = defaultdict(list)
    blogs, ops = [], []
    for d in items:
        kind = d.get("kind", "")
        if kind == "blog_post":
            blogs.append(d)
        elif kind.startswith("ceo_") or kind in ("site_config_change",):
            ops.append(d)
        else:
            by_course[d.get("course_id") or "_기타"].append(d)

    stats = defaultdict(int)
    for d in items:
        stats[d.get("kind", "?")] += 1

    # ── 1) 강의별 자산 ──────────────────────────────────────
    courses_dir = OUT / "강의"
    course_titles = {}
    for cid, docs in sorted(by_course.items()):
        cdir = courses_dir / slug(cid, 40)
        cdir.mkdir(parents=True, exist_ok=True)
        # 강의 대표 제목 추정
        for d in docs:
            if d.get("kind") == "curriculum_outline":
                course_titles[cid] = d.get("title", cid)
                break
        course_titles.setdefault(cid, docs[0].get("title", cid))

        scripts_dir = cdir / "영상스크립트"
        order = {"curriculum_outline": 0, "landing_copy": 1, "faq": 2}
        for d in sorted(docs, key=lambda x: (order.get(x.get("kind"), 5),
                                             x.get("created_at", ""))):
            kind = d.get("kind", "")
            title = d.get("title", "무제")
            md = f"# {title}\n\n"
            md += f"> 종류: {KIND_KR.get(kind, kind)} · 생성: {d.get('created_at','?')[:10]} · id: {d.get('id','')}\n\n"
            md += body_of(d) + "\n"
            if kind == "lecture_script":
                scripts_dir.mkdir(exist_ok=True)
                (scripts_dir / f"{slug(title)}.md").write_text(md, encoding="utf-8")
            else:
                prefix = {"curriculum_outline": "00_커리큘럼",
                          "landing_copy": "01_랜딩카피", "faq": "02_FAQ"}.get(kind, KIND_KR.get(kind, kind))
                fn = cdir / f"{prefix}__{slug(title)}.md"
                # 같은 종류 여러 개면 덮어쓰기 방지
                i = 2
                while fn.exists():
                    fn = cdir / f"{prefix}_{i}__{slug(title)}.md"
                    i += 1
                fn.write_text(md, encoding="utf-8")

    # ── 2) 블로그 글 ────────────────────────────────────────
    bdir = OUT / "블로그글"
    bdir.mkdir(exist_ok=True)
    for i, d in enumerate(sorted(blogs, key=lambda x: x.get("created_at", "")), 1):
        title = d.get("title", "무제")
        md = f"# {title}\n\n> 생성: {d.get('created_at','?')[:10]} · 강의: {d.get('course_id','')}\n\n"
        md += body_of(d) + "\n"
        (bdir / f"{i:03d}_{slug(title)}.md").write_text(md, encoding="utf-8")

    # ── 3) 운영기록(CEO 보고 등) ───────────────────────────
    odir = OUT / "운영기록"
    odir.mkdir(exist_ok=True)
    for i, d in enumerate(sorted(ops, key=lambda x: x.get("created_at", "")), 1):
        title = d.get("title", "무제")
        md = f"# {title}\n\n{body_of(d)}\n"
        (odir / f"{i:03d}_{slug(title)}.md").write_text(md, encoding="utf-8")

    # ── 4) 이미지 복사 ──────────────────────────────────────
    img_out = OUT / "이미지"
    img_out.mkdir(exist_ok=True)
    img_n = 0
    for src in glob.glob(str(ROOT / "site/blog-images/*.png")) + \
               glob.glob(str(ROOT / "site/card-news/**/*.png"), recursive=True):
        shutil.copy2(src, img_out / Path(src).name)
        img_n += 1

    # ── 5) README 인덱스 ────────────────────────────────────
    lines = ["# 복구 자산 — Core Campus 산출물 추출본\n",
             f"> 추출일 2026-06-08 · content/approved 568건 + 이미지에서 복구\n",
             "\n## 자산 요약\n"]
    for k, c in sorted(stats.items(), key=lambda x: -x[1]):
        lines.append(f"- {KIND_KR.get(k, k)}: **{c}개**")
    lines.append(f"- 복사한 이미지: **{img_n}장**\n")
    lines.append("\n## 폴더 구조\n")
    lines.append("- `강의/{course_id}/` — 커리큘럼·랜딩카피·FAQ + `영상스크립트/`")
    lines.append("- `블로그글/` — 블로그 글 110편 (마크다운)")
    lines.append("- `운영기록/` — CEO 일일보고 등 내부 기록")
    lines.append("- `이미지/` — 블로그/카드뉴스 이미지 원본\n")
    lines.append("\n## 강의 목록\n")
    for cid in sorted(by_course):
        n = len(by_course[cid])
        lines.append(f"- **{cid}** ({course_titles.get(cid,'')[:40]}) — 산출물 {n}건")
    (OUT / "00_README.md").write_text("\n".join(lines), encoding="utf-8")

    print(f"✓ 추출 완료 → {OUT}")
    print(f"  강의 {len(by_course)}개 · 블로그 {len(blogs)}편 · 운영기록 {len(ops)}건 · 이미지 {img_n}장")


if __name__ == "__main__":
    main()
