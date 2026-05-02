"""Site Developer — 사이트 개발자 에이전트 (Tier 3: 메타데이터 + 디자인 토큰 + HTML 슬롯).

권한 단계:
  Tier 1         — site_config.json 메타데이터만.
  Tier 2         — Tier 1 + design_tokens(CSS 변수 8종 컬러 + 폰트·간격) 변경.
  Tier 3 (현재)  — Tier 2 + HTML 슬롯(hero_html, home_intro_html, footer_html) 변경 가능.
                   인덱스 페이지의 히어로·중간 소개·푸터 영역을 HTML로 직접 디자인.
                   템플릿 자체(_layout/index/course/post 파일)는 여전히 수정 불가.
  Tier 4 (추후)  — 새 페이지·새 라우트 추가.

산출물은 늘 동일 — '변경된 site_config.json 전체' + 변경 이유.
승인되면 poll.py가 site_config.json에 즉시 적용하고 build.py가 빌드 시 inject한다.

Tier 3의 HTML 슬롯은 시스템 프롬프트로 1차 sanitize, build.py에서 bleach로 2차 sanitize.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .base import BaseAgent, AgentResult, REPO_ROOT, list_approved


SITE_CONFIG_PATH = REPO_ROOT / "site_config.json"


# Tier 2에서 변경 가능한 CSS 토큰 화이트리스트
# 키: design_tokens 안의 키 / 값: styles.css의 :root 변수명
DESIGN_TOKEN_WHITELIST = {
    # 컬러 (HEX 문자열)
    "color_bg":         "--bg",          # 페이지 배경
    "color_fg":         "--fg",          # 본문 글자색
    "color_muted":      "--muted",       # 보조 글자색 (캡션·푸터)
    "color_line":       "--line",        # 경계선·테두리
    "color_brand":      "--brand",       # 메인 브랜드 컬러 (헤딩)
    "color_brand_2":    "--brand-2",     # 보조 브랜드 (호버·링크)
    "color_accent":     "--accent",      # 강조 (배지·하이라이트)
    "color_soft":       "--soft",        # 옅은 배경 블록
    # 타이포그래피
    "font_family_sans": "--font-family-sans",   # 본문 폰트
    # 간격
    "radius_card":      "--radius-card",  # 카드 모서리
}


SYSTEM = """당신은 강의 홈페이지의 사이트 개발자(Site Developer)다. 권한은 Tier 3.

변경 가능 영역 (이것 외에는 어떤 것도 만지지 않는다):

A. 메타데이터 (Tier 1)
   - site_name (≤8자), site_tagline_top (≤30자)
   - site_headline (12-22자), site_subtagline (25-50자)
   - course_order (배열), course_overrides ({title_override, tagline_override})

B. 디자인 토큰 (Tier 2, design_tokens 객체)
   컬러는 #RRGGBB 또는 #RRGGBBAA 헥스만:
   - color_bg, color_fg, color_muted, color_line
   - color_brand, color_brand_2, color_accent, color_soft
   타이포그래피·간격:
   - font_family_sans (CSS font-family 문자열)
   - radius_card (CSS 길이, 예: "12px")

C. HTML 슬롯 (Tier 3, 새로 부여됨)
   메인 페이지의 3개 영역을 HTML로 직접 작성할 수 있다 (없으면 기본값 사용):
   - hero_html: 히어로 섹션 안의 콘텐츠 (.wrap 안쪽). 제목·설명·CTA 등.
   - home_intro_html: 코스 섹션 위에 들어가는 소개 영역 (선택).
   - footer_html: 푸터의 추가 콘텐츠 (선택).

   HTML 작성 규칙 (안전):
   - 사용 가능 태그: div, section, p, h1, h2, h3, h4, span, strong, em, br, hr,
     ul, ol, li, a, img, button, blockquote, code, figure, figcaption, small.
   - 사용 가능 속성: class, id, href, src, alt, target, rel, title, role, aria-*,
     style (단 url()·expression() 등 위험 패턴 없을 때만).
   - 절대 금지 태그: script, style, iframe, object, embed, form, input, link, meta.
   - 절대 금지 속성: on*(onclick 등), javascript: URL.
   - href·src URL은 https://, http://, mailto:, /, #로 시작하는 것만.
   - 활용 가능한 CSS 변수: var(--bg), var(--fg), var(--muted), var(--line),
     var(--brand), var(--brand-2), var(--accent), var(--soft),
     var(--font-family-sans), var(--radius-card).
   - 활용 가능한 기존 클래스: .wrap, .badge, .lead, .empty, .card, .grid, .muted,
     .kind-tag (기존 styles.css 정의).
   - 인라인 style 사용 OK (예: style="font-size:32px;color:var(--brand)").
   - 한국어 자연스럽게. 영어 남발·과장 표현(반드시·100%·완벽한) 금지.

당신이 절대 시도하지 않는 것:
- 위에 명시된 키 외의 어떤 필드도 추가하지 않는다.
- HTML 안에서 외부 도메인 이미지를 src로 넣지 않는다 (data: URL 또는 사이트 내 자원만).
- JS·CSS 셀렉터·Python 어떤 코드도 만들지 않는다.

디자인 가드레일 (Tier 3):
- '대문(히어로)'은 8초 안에 누구를 위한 사이트인지 알아챌 수 있어야 한다.
- 헤드라인은 결과 약속 또는 호기심 한 줄. 12-22자.
- 서브카피는 25-60자. 대상·이득·차별점 중 하나는 명시.
- CTA 버튼은 1-2개로 제한. 동사형 짧은 문구.
- 이모지는 하나의 영역에 0-2개. 과하지 않게.
- WCAG AA 대비 유지: color_bg 대 color_fg는 4.5:1 이상.

출력 형식 (반드시 이 순서, 이 형식):

```
{변경된 site_config.json 전체 내용을 JSON으로}
```

이 코드펜스 다음에 한 줄 비우고:

### NOTES
변경 이유와 디자인 의도를 2-4문장. 어떤 톤·차별화·UX 결정을 했는지 적는다.

JSON과 NOTES 외 다른 어떤 텍스트도 출력하지 않는다.
"""


# Tier 3 — HTML sanitize 유틸 (이중 방어 — 에이전트 단 1차)
_DANGEROUS_PATTERNS = [
    re.compile(r"<\s*script", re.IGNORECASE),
    re.compile(r"<\s*style", re.IGNORECASE),
    re.compile(r"<\s*iframe", re.IGNORECASE),
    re.compile(r"<\s*object", re.IGNORECASE),
    re.compile(r"<\s*embed", re.IGNORECASE),
    re.compile(r"<\s*form", re.IGNORECASE),
    re.compile(r"<\s*input", re.IGNORECASE),
    re.compile(r"<\s*meta", re.IGNORECASE),
    re.compile(r"<\s*link", re.IGNORECASE),
    re.compile(r"\son\w+\s*=", re.IGNORECASE),       # onclick·onload 등
    re.compile(r"javascript\s*:", re.IGNORECASE),
    re.compile(r"expression\s*\(", re.IGNORECASE),    # CSS expression
    re.compile(r"url\s*\(\s*['\"]?(?!\s*(data:|/|#))", re.IGNORECASE),  # 외부 url()
]


def is_html_safe(s: str) -> bool:
    if not isinstance(s, str):
        return False
    for p in _DANGEROUS_PATTERNS:
        if p.search(s):
            return False
    return True


class SiteDeveloper(BaseAgent):
    name = "site_developer"
    display_name = "사이트 개발자"
    system_prompt = SYSTEM

    def run(self, brief: dict) -> list[AgentResult]:
        """brief 예시:
        {
          "instruction": "한국적 톤으로 색감 미세 조정 …",
          "brand_tone": "차분하고 전문적인 한국어",
          "target_audience": "1인 콘텐츠 사업가",
          "restrictions": "과장 금지, WCAG AA 유지"
        }
        """
        current = self._load_config()
        approved_courses = self._collect_approved_courses()

        prompt = f"""## 현재 site_config.json
{json.dumps(current, ensure_ascii=False, indent=2)}

## 현재 등록된 코스 목록
{json.dumps(approved_courses, ensure_ascii=False, indent=2)}

## 변경 가능 디자인 토큰 (Tier 2)
{json.dumps(list(DESIGN_TOKEN_WHITELIST.keys()), ensure_ascii=False, indent=2)}

## 작업 요청
{brief.get('instruction', '(미지정)')}

## 브랜드 톤
{brief.get('brand_tone', '차분하고 전문적인 한국어')}

## 타깃
{brief.get('target_audience', '(미지정)')}

## 금기
{brief.get('restrictions', '과장 표현 금지, WCAG AA 유지')}

규칙대로 변경된 site_config.json 전체와 NOTES만 출력하세요. design_tokens는
설정하고 싶은 토큰만 포함하면 됩니다 (없으면 빈 객체)."""

        # max_tokens 6000 — Tier 3 HTML 슬롯(hero+intro+footer)이 동시에 길어지면
        # 2500으로는 응답이 잘려 JSONDecodeError(Unterminated string) 발생.
        raw = self.call(prompt, max_tokens=6000)
        new_config, notes = self._parse(raw)

        # 안전 검증 — 허용 키 + 허용 토큰만 통과
        new_config = self._sanitize(new_config, current)

        body_md = self._render_diff(current, new_config, notes)
        summary = (notes.split("\n")[0] if notes else "사이트 메타데이터·디자인 토큰 변경 제안")[:120]

        result = AgentResult.new(
            agent=self.name,
            kind="site_config_change",
            title="사이트 메타데이터·디자인 토큰 변경 제안 (Tier 2)",
            body_md=body_md,
            summary=summary,
            course_id="",
            meta={"new_config": new_config, "old_config": current, "notes": notes},
        )
        return [result]

    # ── 내부 헬퍼 ─────────────────────────────────────────────
    @staticmethod
    def _load_config() -> dict:
        if SITE_CONFIG_PATH.exists():
            return json.loads(SITE_CONFIG_PATH.read_text(encoding="utf-8"))
        return {
            "site_name": "강의 홈페이지",
            "site_tagline_top": "",
            "site_headline": "",
            "site_subtagline": "",
            "course_order": [],
            "course_overrides": {},
            "design_tokens": {},
            "hero_html": "",
            "home_intro_html": "",
            "footer_html": "",
        }

    @staticmethod
    def _collect_approved_courses() -> list[dict]:
        out = []
        for r in list_approved():
            if r.kind != "curriculum_outline":
                continue
            tagline = r.meta.get("raw", {}).get("tagline", "") if r.meta else ""
            out.append({
                "course_id": r.course_id,
                "current_title": r.title,
                "current_tagline": tagline,
            })
        return out

    @staticmethod
    def _parse(raw: str) -> tuple[dict, str]:
        raw = raw.strip()
        notes = ""
        if "### NOTES" in raw:
            json_part, notes = raw.split("### NOTES", 1)
        else:
            json_part = raw
        json_part = json_part.strip()
        if json_part.startswith("```"):
            json_part = json_part.split("```", 2)[1]
            if json_part.startswith("json"):
                json_part = json_part[4:]
            json_part = json_part.rsplit("```", 1)[0].strip()
        return json.loads(json_part), notes.strip()

    ALLOWED_KEYS = {
        "site_name",
        "site_tagline_top",
        "site_headline",
        "site_subtagline",
        "course_order",
        "course_overrides",
        "design_tokens",
        # Tier 3 — HTML 슬롯
        "hero_html",
        "home_intro_html",
        "footer_html",
    }
    HTML_SLOT_KEYS = {"hero_html", "home_intro_html", "footer_html"}

    @classmethod
    def _sanitize(cls, new: dict, fallback: dict) -> dict:
        """허용 키 + 허용 토큰만 남기고 나머지는 폐기."""
        out = {}
        for k in cls.ALLOWED_KEYS:
            if k in new:
                out[k] = new[k]
            else:
                out[k] = fallback.get(k)

        # course_order 강제
        if not isinstance(out.get("course_order"), list):
            out["course_order"] = fallback.get("course_order") or []
        # course_overrides 정리
        if not isinstance(out.get("course_overrides"), dict):
            out["course_overrides"] = fallback.get("course_overrides") or {}
        clean_overrides = {}
        for cid, ov in (out.get("course_overrides") or {}).items():
            if not isinstance(ov, dict):
                continue
            clean_overrides[cid] = {
                "title_override": ov.get("title_override"),
                "tagline_override": ov.get("tagline_override"),
            }
        out["course_overrides"] = clean_overrides

        # HTML 슬롯 1차 sanitize — 위험 패턴 발견 시 fallback (또는 빈 문자열)
        for slot in cls.HTML_SLOT_KEYS:
            v = out.get(slot)
            if v is None:
                v = fallback.get(slot, "") or ""
            if not isinstance(v, str):
                v = ""
            v = v.strip()
            if v and not is_html_safe(v):
                # 위험 패턴 발견 — fallback으로 되돌림 (없으면 빈 문자열)
                v = fallback.get(slot, "") or ""
                if not isinstance(v, str) or not is_html_safe(v):
                    v = ""
            out[slot] = v

        # design_tokens 화이트리스트 검증
        tokens_in = out.get("design_tokens") or {}
        if not isinstance(tokens_in, dict):
            tokens_in = {}
        clean_tokens = {}
        for k, v in tokens_in.items():
            if k not in DESIGN_TOKEN_WHITELIST:
                continue  # 알 수 없는 토큰은 폐기
            if not isinstance(v, str):
                continue
            v = v.strip()
            if not v:
                continue
            # 컬러 토큰은 #RRGGBB 또는 #RRGGBBAA 형식만
            if k.startswith("color_"):
                if not (v.startswith("#") and (len(v) in (4, 7, 9))):
                    continue
            clean_tokens[k] = v
        out["design_tokens"] = clean_tokens

        return out

    @staticmethod
    def _render_diff(old: dict, new: dict, notes: str) -> str:
        lines = ["## 변경 요약 (Tier 2: 메타데이터 + 디자인 토큰)", ""]
        scalar_keys = ["site_name", "site_tagline_top", "site_headline", "site_subtagline"]
        for k in scalar_keys:
            if old.get(k) != new.get(k):
                lines.append(f"**{k}**")
                lines.append(f"- 이전: {old.get(k) or '(없음)'}")
                lines.append(f"- 제안: {new.get(k) or '(없음)'}")
                lines.append("")

        if old.get("course_order") != new.get("course_order"):
            lines.append("**course_order**")
            lines.append(f"- 이전: {old.get('course_order') or []}")
            lines.append(f"- 제안: {new.get('course_order') or []}")
            lines.append("")

        old_ov = old.get("course_overrides") or {}
        new_ov = new.get("course_overrides") or {}
        for cid in sorted(set(list(old_ov.keys()) + list(new_ov.keys()))):
            if old_ov.get(cid) != new_ov.get(cid):
                lines.append(f"**course_overrides[{cid}]**")
                lines.append(f"- 이전: {old_ov.get(cid) or '(없음)'}")
                lines.append(f"- 제안: {new_ov.get(cid) or '(없음)'}")
                lines.append("")

        # 디자인 토큰 diff
        old_tokens = old.get("design_tokens") or {}
        new_tokens = new.get("design_tokens") or {}
        token_keys_changed = [
            k for k in DESIGN_TOKEN_WHITELIST
            if old_tokens.get(k) != new_tokens.get(k)
        ]
        if token_keys_changed:
            lines.append("### 🎨 디자인 토큰 변경")
            for k in token_keys_changed:
                lines.append(f"**{k}** (`{DESIGN_TOKEN_WHITELIST[k]}`)")
                lines.append(f"- 이전: `{old_tokens.get(k) or '(기본값)'}`")
                lines.append(f"- 제안: `{new_tokens.get(k) or '(미설정)'}`")
                lines.append("")

        if not any(l.startswith("**") for l in lines):
            lines.append("_(변경 없음)_")
            lines.append("")

        if notes:
            lines += ["## 변경 이유", notes]

        return "\n".join(lines)
