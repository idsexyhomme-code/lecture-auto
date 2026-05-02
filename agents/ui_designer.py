"""UI/UX Designer — 시니어 디자이너 (Tier 4+).

권한 단계:
  Tier 4+ — 전체 페이지/섹션 HTML을 *디자인 시안*으로 생성한다. 단,
            템플릿 파일(_layout.html / index.html / course.html / post.html)을
            직접 수정하지는 않는다 — site_config.json의 HTML 슬롯
            (hero_html / home_intro_html / footer_html) 또는 새로 추가될
            page_html_overrides에 들어갈 *3개 변형(variant)* 시안을 산출한다.

입력 (brief):
  - target          "hero" | "home_intro" | "footer" | "landing_full"
  - purpose         이 디자인이 해결해야 할 핵심 사용자 문제 한 줄
  - audience        타깃 사용자 묘사 (1-2 문장)
  - style_keywords  스타일 키워드 배열 (예: ["미니멀", "따뜻한 톤", "학술적"])
  - color_mood      "warm" | "cool" | "monochrome" | "vibrant" | None
  - reference_urls  영감 받을 사이트 URL 배열 (옵션)
  - screenshot_paths  업로드된 스크린샷 파일 절대경로 배열 (옵션, Vision 입력)
  - additional_context  자유 텍스트 (옵션)

출력 (kind="design_variants"):
  하나의 AgentResult.meta.variants 안에 3개 변형:
    {
      "id": "v1" | "v2" | "v3",
      "name": str,                    # "에디토리얼 모던" 같은 짧은 별칭
      "vibe": str,                    # 한 줄 분위기 묘사
      "color_palette": {label: hex},
      "html": str,                    # target 슬롯에 들어갈 HTML
      "design_tokens": dict,          # site_developer Tier 2 토큰 호환 형식
      "image_prompts": [str, ...],    # 별도 이미지 생성 도구용 프롬프트 (3-5개)
      "reasoning": str,               # 디자인 결정 근거 2-3 문장
    }

승인 흐름:
  1. ui_designer가 3변형 산출 → pending/<id>.json 저장
  2. site_builder/build.py가 site/_design_previews/<id>/v{1,2,3}.html 미리보기 렌더
  3. notify.py가 텔레그램에 [v1 미리보기] [v2] [v3] 링크 + ✅v1 / ✅v2 / ✅v3 / ❌
     버튼 카드 발송
  4. 사용자가 ✅vN 누르면 poll.py가 선택된 variant로부터 site_developer brief
     자동 생성 → 그 다음 사이클에 SiteDeveloper가 site_config.json에 반영

보안:
  - HTML 1차 sanitize는 site_developer.is_html_safe와 동일 정규식
  - 이미지 src는 data: URL 또는 / · # · placeholder 토큰만
  - URL fetch는 30초 타임아웃 + 5KB cap (제목·meta·구조 요약만 사용)
"""
from __future__ import annotations

import base64
import json
import logging
import re
from pathlib import Path

import requests

from .base import BaseAgent, AgentResult
from .site_developer import is_html_safe, DESIGN_TOKEN_WHITELIST

log = logging.getLogger("ui_designer")


# ─────────────────────────────────────────────────────────────────────────
# 시스템 프롬프트
# ─────────────────────────────────────────────────────────────────────────

SYSTEM = """당신은 '코어 캠퍼스'의 시니어 UI/UX 디자이너다. 권한은 Tier 4+.

회사 맥락:
- 코어 캠퍼스는 한국어 강의 홈페이지. 1인 콘텐츠 사업가/지식 창업가가 타깃.
- 톤은 차분하고 전문적, 과장 표현 금지. 결과 약속과 신뢰감이 핵심.
- 이미 등록된 site_developer가 Tier 2 토큰(컬러·폰트·간격)과 Tier 3 HTML 슬롯
  (hero_html / home_intro_html / footer_html)을 site_config.json에 반영한다.

당신의 역할:
- 사용자가 던진 디자인 의뢰(target, purpose, audience, style_keywords, refs)를
  받아 *3개의 뚜렷이 다른 변형(variant)*을 산출한다.
- 변형은 톤·구도·컬러·타이포·레이아웃이 *서로 의미 있게* 달라야 한다.
  같은 톤의 색만 바꾼 3개는 안 됨.
- 각 변형은 *그 자체로 완성된 시안*이어야 한다.

산출 형식 — JSON 한 덩어리만 출력:

```json
{
  "target": "hero",
  "summary": "코어 캠퍼스 메인 히어로 3변형 — 에디토리얼/임팩트/서사",
  "variants": [
    {
      "id": "v1",
      "name": "에디토리얼 모던",
      "vibe": "차분한 학술 매거진 같은 진중함",
      "color_palette": {
        "bg": "#FBF8F3",
        "fg": "#1A1814",
        "brand": "#3D2F1E",
        "accent": "#B8860B",
        "soft": "#F0E9DC"
      },
      "html": "<div class=\\"wrap\\">...</div>",
      "design_tokens": {
        "color_bg": "#FBF8F3",
        "color_fg": "#1A1814",
        "color_brand": "#3D2F1E",
        "color_accent": "#B8860B",
        "color_soft": "#F0E9DC",
        "font_family_sans": "'Pretendard', system-ui, sans-serif",
        "radius_card": "8px"
      },
      "image_prompts": [
        "차분한 학술 매거진 표지 풍의 추상 일러스트, 베이지/딥브라운/머스타드 팔레트, 미니멀, 한국적 정서",
        "..."
      ],
      "reasoning": "지식 창업가가 '진지하게 일하는 사람'으로 보이고 싶을 때..."
    },
    { "id": "v2", ... },
    { "id": "v3", ... }
  ]
}
```

규칙 (반드시 지킬 것):

A. JSON 외의 어떤 텍스트도 출력하지 않는다. ```json 코드펜스만 사용.

B. variants 배열은 정확히 3개. id는 "v1", "v2", "v3" 고정.

C. 각 variant.html 작성 규칙:
   - target="hero"인 경우 외곽은 <div class="wrap">로 감싼다 (이미 hero 섹션
     안에 들어가므로 .hero · .wrap 외곽 컨테이너는 따로 만들지 않는다).
   - target="home_intro"·"footer"인 경우도 컨텐츠 본문만. 외곽 컨테이너는
     템플릿이 제공한다.
   - target="landing_full"인 경우 hero + intro + footer 모두 한 묶음으로
     설계 — 단 이때는 html 필드를 잘라서 hero_html / home_intro_html /
     footer_html 키로 쪼개 둔다.
   - 사용 가능 태그: div, section, p, h1, h2, h3, h4, span, strong, em, br,
     hr, ul, ol, li, a, img, button, blockquote, code, figure, figcaption,
     small.
   - 사용 가능 속성: class, id, href, src, alt, target, rel, title, role,
     aria-*, style.
   - 절대 금지: script, style, iframe, object, embed, form, input, link,
     meta, on*(onclick 등), javascript: URL, expression(), 외부 url().
   - 이미지 src는 다음 중 하나만:
     · "/assets/placeholder/{slot}-{kind}.svg" 형식의 placeholder 경로
     · "data:image/svg+xml;utf8,..." 인라인 SVG (작을 때만)
     외부 도메인 이미지 src 절대 금지.
   - 인라인 style 사용 가능 (예: style="font-size:32px;color:var(--brand)").
   - CSS 변수 var(--bg) 등 활용.
   - 한국어 자연스럽게.

D. design_tokens — site_developer Tier 2 토큰 화이트리스트만 사용:
   color_bg, color_fg, color_muted, color_line, color_brand, color_brand_2,
   color_accent, color_soft, font_family_sans, radius_card.
   - 컬러 값은 #RRGGBB 형식 (또는 #RRGGBBAA 8자리).
   - WCAG AA 대비 — color_bg 대 color_fg 명도 차이 4.5:1 이상.

E. image_prompts — 3-5개. 각 프롬프트는:
   - 한 문장으로 시각 묘사. (예: "베이지 톤 추상 기하 패턴, 미니멀, ...")
   - 어디에 쓸 이미지인지 head에 붙이지 말 것 (메타 텍스트 없이 묘사만).
   - 사람 얼굴·실제 인물 제외 (저작권·개인정보 회피).
   - 한국적 정서 또는 글로벌 아카데믹 톤 중 명시.

F. reasoning — 2-3 문장. *왜 이 디자인이 audience와 purpose에 적합한지*.

G. 3개 변형 사이의 차별화는 다음 축 중 *최소 2개*가 의미 있게 달라야:
   - 컬러 무드 (warm vs cool vs monochrome)
   - 타이포그래피 무게 (serif heavy vs sans clean vs mixed)
   - 레이아웃 (centered editorial vs split asymmetric vs full-bleed impact)
   - 카피 톤 (격식 vs 친근 vs 명령형)
   - 이미지 비중 (텍스트 우선 vs 이미지 우선 vs 균형)

오로지 위 JSON만 출력. 설명·인사·"여기 결과입니다" 같은 머리말 금지.
"""


# ─────────────────────────────────────────────────────────────────────────
# 외부 입력 처리 — URL fetch + screenshot Vision blocks
# ─────────────────────────────────────────────────────────────────────────

URL_FETCH_TIMEOUT = 30
URL_FETCH_MAX_BYTES = 5_000   # 5KB 정도만 — 톤·구조 신호만 필요
USER_AGENT = "Mozilla/5.0 (compatible; CoreCampus-UIDesigner/1.0)"


def fetch_url_summary(url: str) -> str:
    """주어진 URL을 fetch해서 톤 분석에 쓸 짧은 요약 반환.

    실패하면 빈 문자열. HTML에서 <title>·meta description·visible h1/h2 정도만
    뽑는다 (전체 HTML 덤프는 토큰 낭비).
    """
    try:
        r = requests.get(url, timeout=URL_FETCH_TIMEOUT, headers={"User-Agent": USER_AGENT})
        if r.status_code != 200:
            return ""
        # 첫 200KB만 — 큰 사이트 방어
        html = r.text[:200_000]
    except Exception as e:
        log.warning("url fetch failed %s — %s", url, e)
        return ""

    # 아주 가볍게 파싱 (bs4 의존 없이 정규식)
    title = ""
    desc = ""
    headings = []

    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    if m:
        title = re.sub(r"\s+", " ", m.group(1)).strip()[:200]

    m = re.search(
        r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']',
        html, re.IGNORECASE,
    )
    if m:
        desc = m.group(1).strip()[:300]

    for tag in ("h1", "h2"):
        for m in re.finditer(rf"<{tag}[^>]*>(.*?)</{tag}>", html, re.IGNORECASE | re.DOTALL):
            text = re.sub(r"<[^>]+>", "", m.group(1))
            text = re.sub(r"\s+", " ", text).strip()
            if text and len(text) < 200:
                headings.append(text)
            if len(headings) >= 8:
                break

    parts = [f"URL: {url}"]
    if title:
        parts.append(f"  title: {title}")
    if desc:
        parts.append(f"  description: {desc}")
    if headings:
        parts.append(f"  headings: " + " | ".join(headings[:8]))

    summary = "\n".join(parts)
    return summary[:URL_FETCH_MAX_BYTES]


def build_image_block(image_path: Path) -> dict | None:
    """업로드된 스크린샷을 Anthropic Vision content block으로 변환.

    실패하면 None.
    """
    try:
        if not image_path.exists():
            log.warning("screenshot not found: %s", image_path)
            return None
        b64 = base64.standard_b64encode(image_path.read_bytes()).decode("ascii")
        suffix = image_path.suffix.lower().lstrip(".")
        media_type = {
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png",
            "gif": "image/gif",
            "webp": "image/webp",
        }.get(suffix, "image/png")
        return {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": b64,
            },
        }
    except Exception as e:
        log.warning("image block build failed %s — %s", image_path, e)
        return None


# ─────────────────────────────────────────────────────────────────────────
# Variant sanitize — site_developer 규칙 재사용 + variant 자체 검증
# ─────────────────────────────────────────────────────────────────────────

REQUIRED_VARIANT_KEYS = {
    "id", "name", "vibe", "color_palette", "html",
    "design_tokens", "image_prompts", "reasoning",
}
VALID_VARIANT_IDS = {"v1", "v2", "v3"}


def _sanitize_variant(v: dict) -> dict | None:
    """단일 variant 검증 + 정리. 실패 시 None."""
    if not isinstance(v, dict):
        return None
    missing = REQUIRED_VARIANT_KEYS - set(v.keys())
    if missing:
        log.warning("variant missing keys: %s", missing)
        return None

    if v.get("id") not in VALID_VARIANT_IDS:
        return None

    # html sanitize
    html = v.get("html") or ""
    if not isinstance(html, str) or not html.strip():
        return None
    if not is_html_safe(html):
        log.warning("variant %s — html unsafe, dropping", v.get("id"))
        return None

    # design_tokens 화이트리스트
    tokens_in = v.get("design_tokens") or {}
    clean_tokens = {}
    if isinstance(tokens_in, dict):
        for k, val in tokens_in.items():
            if k not in DESIGN_TOKEN_WHITELIST:
                continue
            if not isinstance(val, str):
                continue
            val = val.strip()
            if not val:
                continue
            if k.startswith("color_") and not (val.startswith("#") and len(val) in (4, 7, 9)):
                continue
            clean_tokens[k] = val

    # color_palette 정리 (자유 라벨 허용 — 단 값은 hex만)
    palette_in = v.get("color_palette") or {}
    clean_palette = {}
    if isinstance(palette_in, dict):
        for label, val in palette_in.items():
            if not isinstance(val, str):
                continue
            val = val.strip()
            if val.startswith("#") and len(val) in (4, 7, 9):
                clean_palette[str(label)[:32]] = val

    # image_prompts 검증
    prompts = v.get("image_prompts") or []
    clean_prompts = []
    if isinstance(prompts, list):
        for p in prompts:
            if isinstance(p, str) and p.strip():
                clean_prompts.append(p.strip()[:500])
    clean_prompts = clean_prompts[:8]   # 너무 많으면 잘라냄

    return {
        "id": v["id"],
        "name": str(v.get("name") or "")[:40] or v["id"],
        "vibe": str(v.get("vibe") or "")[:120],
        "color_palette": clean_palette,
        "html": html.strip(),
        "design_tokens": clean_tokens,
        "image_prompts": clean_prompts,
        "reasoning": str(v.get("reasoning") or "")[:500],
    }


def _parse_response(raw: str) -> dict:
    """모델 출력에서 JSON을 추출."""
    raw = raw.strip()
    if raw.startswith("```"):
        # ```json ... ``` 떼어냄
        body = raw.split("```", 2)[1]
        if body.startswith("json"):
            body = body[4:]
        raw = body.rsplit("```", 1)[0].strip()
    return json.loads(raw)


# ─────────────────────────────────────────────────────────────────────────
# UIDesigner 본체
# ─────────────────────────────────────────────────────────────────────────

class UIDesigner(BaseAgent):
    name = "ui_designer"
    display_name = "UI/UX 디자이너"
    system_prompt = SYSTEM

    def run(self, brief: dict) -> list[AgentResult]:
        target = (brief.get("target") or "hero").strip()
        if target not in {"hero", "home_intro", "footer", "landing_full"}:
            log.warning("unknown target=%s — fallback to 'hero'", target)
            target = "hero"

        purpose = brief.get("purpose") or "(미지정)"
        audience = brief.get("audience") or "(미지정)"
        style_keywords = brief.get("style_keywords") or []
        color_mood = brief.get("color_mood") or "(자유)"
        ref_urls = brief.get("reference_urls") or []
        screenshot_paths = brief.get("screenshot_paths") or []
        extra = brief.get("additional_context") or ""

        # URL refs 요약
        ref_summaries = []
        for u in ref_urls[:5]:    # 최대 5개
            if not isinstance(u, str):
                continue
            s = fetch_url_summary(u)
            if s:
                ref_summaries.append(s)

        ref_block = "\n\n".join(ref_summaries) if ref_summaries else "(없음)"

        # 텍스트 프롬프트 본문
        text_prompt = f"""## 디자인 의뢰

target: **{target}**
purpose: {purpose}
audience: {audience}
style_keywords: {", ".join(style_keywords) if style_keywords else "(자유)"}
color_mood: {color_mood}

## 영감 사이트 (URL fetch 요약)
{ref_block}

## 추가 컨텍스트
{extra or "(없음)"}

위 의뢰를 바탕으로 *서로 의미 있게 다른* 3개의 디자인 변형을 JSON으로
산출하세요. 변형 사이의 차별화는 시스템 규칙 G의 축 중 최소 2개를 따릅니다."""

        # Vision 블록 — 스크린샷이 있으면 image content block으로 추가
        content_blocks: list[dict] = []
        for sp in screenshot_paths[:3]:    # 최대 3장
            if not isinstance(sp, str):
                continue
            blk = build_image_block(Path(sp))
            if blk:
                content_blocks.append(blk)

        # 마지막에 텍스트 프롬프트
        content_blocks.append({"type": "text", "text": text_prompt})

        log.info(
            "[ui_designer] target=%s refs=%d screenshots=%d",
            target, len(ref_summaries), sum(1 for b in content_blocks if b.get("type") == "image"),
        )

        # 직접 messages.create 호출 (Vision 블록을 위해 BaseAgent.call 우회)
        msg = self.client.messages.create(
            model=self.model,
            max_tokens=8000,
            system=self.system_prompt,
            messages=[{"role": "user", "content": content_blocks}],
        )
        raw = "".join(b.text for b in msg.content if getattr(b, "type", None) == "text")

        try:
            parsed = _parse_response(raw)
        except Exception as e:
            log.exception("response parse failed: %s\nraw[:500]=%s", e, raw[:500])
            raise RuntimeError(f"ui_designer 응답 JSON 파싱 실패: {e}")

        variants_raw = parsed.get("variants") or []
        if not isinstance(variants_raw, list) or not variants_raw:
            raise RuntimeError("ui_designer 응답에 variants 배열이 없음")

        clean_variants = []
        for v in variants_raw:
            cv = _sanitize_variant(v)
            if cv:
                clean_variants.append(cv)

        # variant id 유니크 — v1/v2/v3 우선
        seen = set()
        deduped = []
        for cv in clean_variants:
            if cv["id"] in seen:
                continue
            seen.add(cv["id"])
            deduped.append(cv)
        clean_variants = deduped

        if not clean_variants:
            raise RuntimeError("ui_designer 응답에서 유효한 variant가 0개")

        # body_md — 텔레그램 카드/사이트 미리보기 텍스트
        body_md = self._render_body(target, parsed.get("summary", ""), clean_variants)
        summary_line = (parsed.get("summary") or "").strip()[:120] or f"디자인 변형 {len(clean_variants)}개 (target={target})"

        result = AgentResult.new(
            agent=self.name,
            kind="design_variants",
            title=f"[디자인 시안] {target} — {len(clean_variants)}개 변형",
            body_md=body_md,
            summary=summary_line,
            course_id="",
            meta={
                "target": target,
                "variants": clean_variants,
                "brief_echo": {
                    "purpose": purpose,
                    "audience": audience,
                    "style_keywords": style_keywords,
                    "color_mood": color_mood,
                    "reference_urls": ref_urls,
                },
            },
        )
        return [result]

    @staticmethod
    def _render_body(target: str, summary: str, variants: list[dict]) -> str:
        lines = [f"## {target} — 변형 {len(variants)}개", ""]
        if summary:
            lines += [summary, ""]
        for v in variants:
            lines += [
                f"### {v['id'].upper()} · {v['name']}",
                f"_{v['vibe']}_",
                "",
                f"**팔레트**: " + ", ".join(f"{k}={c}" for k, c in v["color_palette"].items()),
                "",
                f"**이유**: {v['reasoning']}",
                "",
                f"**이미지 프롬프트** ({len(v['image_prompts'])}개):",
            ]
            for p in v["image_prompts"][:5]:
                lines.append(f"- {p}")
            lines.append("")
        return "\n".join(lines)
