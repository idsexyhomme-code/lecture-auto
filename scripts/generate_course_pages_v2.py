#!/usr/bin/env python3
"""19개 코스 페이지를 design-system v1.1 템플릿으로 일괄 생성.

입력: design-system/data/courses_metadata.json
템플릿: design-system/templates/course_v2.html
출력: site/design-previews/courses-v2/{slug}.html
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
META = ROOT / "design-system/data/courses_metadata.json"
TPL = ROOT / "design-system/templates/course_v2.html"
OUT_DIR = ROOT / "site/design-previews/courses-v2"

OUT_DIR.mkdir(parents=True, exist_ok=True)


def derive_meta_chips(meta: dict) -> str:
    """카테고리·레벨 표시"""
    chips = []
    if meta.get("category"):
        chips.append(meta["category"])
    chips.append("실전 코스")
    return "\n        ".join(f'<span class="meta-chip">{c}</span>' for c in chips)


def split_hero_title(title: str) -> str:
    """제목을 두 줄로 나눠 강조 단어 코랄 처리"""
    title = title.strip()
    # ' — ' 가 있으면 그 자리로 분할
    if " — " in title:
        a, b = title.split(" — ", 1)
        return f'{a}<br><span class="text-coral">{b}</span>'
    # 그 다음 우선순위: ' · '
    if " · " in title:
        a, b = title.split(" · ", 1)
        return f'{a}<br><span class="text-coral">{b}</span>'
    # 길면 절반
    if len(title) > 18:
        # 단어 단위 절반
        words = title.split(" ")
        mid = len(words) // 2
        return " ".join(words[:mid]) + "<br>" + f'<span class="text-coral">{" ".join(words[mid:])}</span>'
    return title


def derive_hero_sub(desc: str) -> str:
    """desc를 hero sub로. 70자 안에서 자연 절단."""
    if len(desc) <= 70:
        return desc
    # 첫 문장으로 자르기
    parts = re.split(r'[.!?]\s+', desc, maxsplit=1)
    if parts:
        return parts[0].strip() + "."
    return desc[:70] + "..."


def derive_price(meta: dict) -> str:
    """가격 기본값. 시안 단계라 TBD인 경우 49,000 가정."""
    raw = meta.get("price", "")
    if raw and "원" in raw or "₩" in raw:
        return raw
    return "₩49,000"


def derive_receive_cards(meta: dict) -> str:
    """받게 되는 것 3카드 기본 셋"""
    cards = [
        ("01", "실행 가능한 결과물", f"{meta.get('title', '코스')} 완료 시 손에 남는 명확한 결과."),
        ("02", "다음 단계 실행 순서", "결제만으로 끝이 아니라, 다음에 뭘 해야 할지 정리된 로드맵."),
        ("03", "반복 가능한 루틴", "한 번 익히면 다른 주제에도 그대로 쓸 수 있는 방법."),
    ]
    out = []
    for num, title, body in cards:
        out.append(
            f'        <div class="card card--feature">'
            f'<div class="card__index">{num}</div>'
            f'<h3 class="card__title">{title}</h3>'
            f'<p class="card__body">{body}</p>'
            f'</div>'
        )
    return "\n".join(out)


def derive_curriculum_intro(meta: dict) -> str:
    """커리큘럼 인트로 — 실제 차시 정보는 v1 페이지에 있음. 시안 단계 placeholder."""
    return (
        "각 차시는 시간 분배·실행 가능성·후속 조치 기준으로 설계됐습니다. "
        "차시별 상세는 결제 후 학습 페이지에서 확인하실 수 있습니다."
    )


def derive_faq_fit(meta: dict) -> str:
    return f"이 코스는 {meta.get('description', '1인 사업 실행에 관심 있는 분')}에게 가장 잘 맞습니다."


def derive_final_cta_title(meta: dict) -> str:
    """최종 CTA — '딱, 한 줄 결과' 형식"""
    title = meta.get("title", "")
    if "줄이기" in title:
        return "시간 줄이고, 본업으로."
    if "런칭" in title or "출시" in title:
        return "런칭, 7일 안에."
    if "쓰기" in title or "콘텐츠" in title:
        return "쓰기, 끊기지 않게."
    return "지금 시작, 변화 시작."


def render_one(slug: str, meta: dict, tpl: str, watermark: bool = True) -> str:
    """1개 코스 → HTML 변환"""
    title = meta.get("title", slug)
    description = meta.get("description", title)

    # 기본값
    info = {
        "TITLE": title,
        "DESCRIPTION": description,
        "DS_PREFIX": "../../../design-system/",
        "BREADCRUMB_TITLE": title,
        "META_CHIPS": derive_meta_chips(meta),
        "HERO_TITLE_HTML": split_hero_title(title),
        "HERO_SUB": derive_hero_sub(description),
        "PRICE": derive_price(meta),
        "TOTAL_LESSONS": "6편",
        "DURATION": "약 2시간",
        "LEVEL": "입문 → 실전",
        "FORMAT": "영상 + PDF",
        "RECEIVE_SUB": "이 코스를 들으면",
        "RECEIVE_TITLE": "손에 남는 3가지",
        "RECEIVE_CARDS": derive_receive_cards(meta),
        "CURRICULUM_TITLE": "단계별로 정리",
        "CURRICULUM_INTRO": derive_curriculum_intro(meta),
        "FAQ_FIT": derive_faq_fit(meta),
        "FINAL_CTA_TITLE": derive_final_cta_title(meta),
        "WATERMARK": '<div class="preview-watermark">시안 — 회원 ✅ 전</div>' if watermark else "",
    }

    out = tpl
    for k, v in info.items():
        out = out.replace("{{" + k + "}}", v)
    return out


def main():
    with open(META, encoding="utf-8") as f:
        all_meta = json.load(f)
    tpl = TPL.read_text(encoding="utf-8")

    print(f"Generating {len(all_meta)} course pages → {OUT_DIR}")
    generated = []
    for slug, meta in all_meta.items():
        html = render_one(slug, meta, tpl, watermark=True)
        out_path = OUT_DIR / f"{slug}.html"
        out_path.write_text(html, encoding="utf-8")
        size_kb = out_path.stat().st_size / 1024
        print(f"  ✓ {slug}.html ({size_kb:.1f} KB)")
        generated.append(slug)

    # 인덱스
    index_html = build_index(all_meta)
    (OUT_DIR / "index.html").write_text(index_html, encoding="utf-8")
    print(f"  ✓ index.html (전체 {len(all_meta)} 코스 그리드)")

    print(f"\n총 {len(generated)} 코스 + 1 인덱스 생성 완료.")


def build_index(all_meta: dict) -> str:
    cards = []
    for slug, m in all_meta.items():
        cards.append(
            f'<a href="{slug}.html" class="card card--feature" style="text-decoration:none;color:inherit;">'
            f'<div class="card__index">{slug.split("-")[0].upper()[:3]}</div>'
            f'<h3 class="card__title">{m.get("title", slug)}</h3>'
            f'<p class="card__body">{m.get("description", "")[:80]}</p>'
            f'</a>'
        )
    cards_html = "\n        ".join(cards)
    return f"""<!DOCTYPE html>
<html lang="ko"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>코어 캠퍼스 — 코스 v2 시안 인덱스</title>
<link rel="stylesheet" href="../../../design-system/base.css">
<link rel="stylesheet" href="../../../design-system/components.css">
<style>
.preview-watermark {{ position: fixed; top: 12px; right: 12px; background: var(--color-warning); color: #fff; padding: 4px 10px; border-radius: var(--r-full); font-size: 11px; font-weight: 700; z-index: 999; }}
.grid {{ gap: var(--sp-4); }}
.grid--3 {{ grid-template-columns: repeat(3, 1fr); }}
@media (max-width: 720px) {{ .grid--3 {{ grid-template-columns: 1fr; }} }}
</style></head><body>
<div class="preview-watermark">시안 인덱스</div>
<header class="site-header"><div class="site-header__inner">
<a class="site-logo" href="/site/index.html"><span class="site-logo__mark"></span>코어 캠퍼스 v2 시안</a>
</div></header>
<main class="container container--wide section">
<p class="tg-caption">Courses v2 · 시안</p>
<h1 class="tg-display" style="margin-bottom:var(--sp-8);">19개 코스 디자인 시스템 v1.1 적용 시안</h1>
<div class="grid grid--3">
        {cards_html}
</div>
</main>
</body></html>"""


if __name__ == "__main__":
    main()
