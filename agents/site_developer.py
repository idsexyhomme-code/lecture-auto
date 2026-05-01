"""Site Developer — 사이트 개발자 에이전트 (Tier 1: 메타데이터만).

권한 단계:
  Tier 1 (현재) — site_config.json 한 파일만 변경 가능.
                   사이트 이름·헤드라인·코스 정렬·코스 표시 오버라이드.
  Tier 2 (추후)  — CSS 토큰 변경 권한 추가 (PR 기반).
  Tier 3 (추후)  — HTML 템플릿 변경 권한.
  Tier 4 (추후)  — 새 페이지·새 기능.

이 단계에서는 코드(HTML/CSS/Python) 일체를 절대 수정하지 않는다.
산출물은 ‘변경된 site_config.json’ 한 덩어리 + 변경 이유 한 단락.
승인되면 poll.py가 site_config.json 파일에 즉시 적용한다.
"""
from __future__ import annotations

import json
from pathlib import Path

from .base import BaseAgent, AgentResult, REPO_ROOT, list_approved


SITE_CONFIG_PATH = REPO_ROOT / "site_config.json"


SYSTEM = """당신은 강의 홈페이지의 메타데이터 관리자(Site Developer)다.

권한은 다음 한 파일의 변경만으로 한정된다: site_config.json
이 파일은 정확히 다음 6개 필드만 가진다.

- site_name (문자열): 헤더에 표시되는 사이트 이름. 한국어 8자 이내 권장.
- site_tagline_top (문자열): 메인 페이지 히어로 위 작은 배지. 30자 이내.
- site_headline (문자열): 메인 페이지 큰 제목. 12-22자.
- site_subtagline (문자열): 헤드라인 아래 서브 카피. 25-50자.
- course_order (배열): 코스 표시 순서. course_id의 배열.
- course_overrides (객체): { course_id: { title_override, tagline_override } }

당신이 절대 시도하지 않는 것:
- 다른 어떤 파일도 손대지 않는다 (HTML/CSS/Python 일체 금지).
- 새 필드를 발명하지 않는다 (위 6개만).
- 코드처럼 보이는 어떤 것도 만들지 않는다.
- 과장 표현(반드시·100%·최고·완벽한) 금지.
- 영어 남발 금지 (브랜드 한 단어 정도 OK).

작성 원칙:
- 헤드라인은 ‘문제 + 결과 약속’ 또는 ‘호기심 한 줄’.
- 서브태그라인은 ‘누구에게/무엇을’ 명확히.
- 코스 오버라이드는 원본보다 짧고 검색 친화적이며 한국어 자연스럽게.
- course_order는 입력된 코스 목록 안에 있는 ID만 사용.

출력 형식 (반드시 이 순서, 이 형식):

```
{변경된 site_config.json 전체 내용을 JSON으로}
```

이 코드펜스 다음에 한 줄 비우고:

### NOTES
변경 이유를 2-3문장으로 한 단락. 어떤 톤·맥락 의도로 다듬었는지 적는다.

JSON과 NOTES 외 다른 어떤 텍스트도 출력하지 않는다.
"""


class SiteDeveloper(BaseAgent):
    name = "site_developer"
    display_name = "사이트 개발자"
    system_prompt = SYSTEM

    def run(self, brief: dict) -> list[AgentResult]:
        """brief 예시:
        {
          "instruction": "사이트 이름과 헤드라인을 …하게 다듬어 줘",
          "brand_tone": "차분하고 전문적인 한국어",
          "target_audience": "1인 콘텐츠 사업가",
          "restrictions": "과장 금지"
        }
        """
        current = self._load_config()
        approved_courses = self._collect_approved_courses()

        prompt = f"""## 현재 site_config.json
{json.dumps(current, ensure_ascii=False, indent=2)}

## 현재 등록된 코스 목록 (course_order 후보)
{json.dumps(approved_courses, ensure_ascii=False, indent=2)}

## 작업 요청
{brief.get('instruction', '(미지정)')}

## 브랜드 톤
{brief.get('brand_tone', '차분하고 전문적인 한국어')}

## 타깃
{brief.get('target_audience', '(미지정)')}

## 금기
{brief.get('restrictions', '과장 표현 금지')}

규칙대로 변경된 site_config.json 전체와 NOTES만 출력하세요."""

        raw = self.call(prompt, max_tokens=2000)
        new_config, notes = self._parse(raw)

        # 안전 검증 — 허용 키만 통과
        new_config = self._sanitize(new_config, current)

        body_md = self._render_diff(current, new_config, notes)
        summary = (notes.split("\n")[0] if notes else "사이트 메타데이터 변경 제안")[:120]

        result = AgentResult.new(
            agent=self.name,
            kind="site_config_change",
            title="사이트 메타데이터 변경 제안",
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
    }

    @classmethod
    def _sanitize(cls, new: dict, fallback: dict) -> dict:
        """허용 키만 남기고 그 외는 폐기. 누락된 키는 fallback에서 채움."""
        out = {}
        for k in cls.ALLOWED_KEYS:
            if k in new:
                out[k] = new[k]
            else:
                out[k] = fallback.get(k)
        # course_overrides는 dict, course_order는 list 강제
        if not isinstance(out.get("course_order"), list):
            out["course_order"] = fallback.get("course_order") or []
        if not isinstance(out.get("course_overrides"), dict):
            out["course_overrides"] = fallback.get("course_overrides") or {}
        # 각 override도 허용 서브키만 남기기
        clean_overrides = {}
        for cid, ov in (out.get("course_overrides") or {}).items():
            if not isinstance(ov, dict):
                continue
            clean_overrides[cid] = {
                "title_override": ov.get("title_override"),
                "tagline_override": ov.get("tagline_override"),
            }
        out["course_overrides"] = clean_overrides
        return out

    @staticmethod
    def _render_diff(old: dict, new: dict, notes: str) -> str:
        lines = ["## 변경 요약 (Tier 1: 메타데이터)", ""]
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
        all_cids = set(list(old_ov.keys()) + list(new_ov.keys()))
        for cid in sorted(all_cids):
            if old_ov.get(cid) != new_ov.get(cid):
                lines.append(f"**course_overrides[{cid}]**")
                lines.append(f"- 이전: {old_ov.get(cid) or '(없음)'}")
                lines.append(f"- 제안: {new_ov.get(cid) or '(없음)'}")
                lines.append("")

        if not any(line.startswith("**") for line in lines):
            lines.append("_(변경 없음)_")
            lines.append("")

        if notes:
            lines += ["## 변경 이유", notes]

        return "\n".join(lines)
