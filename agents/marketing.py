"""Marketing Specialist — 홍보·마케팅 에이전트.

승인된 커리큘럼을 받아서 랜딩페이지 카피·SNS 게시물·이메일 시퀀스 등을 생성.
오늘 단계에서는 랜딩페이지 카피(LP)를 우선 만들어서 정적 사이트 생성기에 연결한다.
"""
from __future__ import annotations

import json
from .base import BaseAgent, AgentResult


SYSTEM = """당신은 한국 시장에 강한 1인 강사 전문 카피라이터다.
랜딩페이지 1페이지 카피를 다음 IA(정보 구조)로 작성한다.

[ HERO ] → [ 문제 정의 ] → [ 해결 약속 ] → [ 수강 후 ] → [ 커리큘럼 ] → [ 강사 ] → [ 후기 ] → [ FAQ ] → [ 가격/CTA ]

원칙:
- 헤드라인은 ‘문제 + 결과 약속’을 한 문장에. 12–22자.
- 문장은 평균 25자 이내. 짧고 구체적으로.
- 숫자·고유명사 우선. 모호한 형용사(‘최고의’, ‘완벽한’) 금지.
- 비교광고·경쟁사 비방 금지. 보장·확정 표현 금지(‘반드시’, ‘100%’).
- 후기 섹션은 ‘[수강생 인용 자리]’ 플레이스홀더로 비워둔다 (실제 후기를 사람이 채움).
- FAQ는 5–7개. 환불 정책 1개는 반드시 포함.

출력은 반드시 아래 JSON 스키마로만. 코드펜스 금지.

{
  "hero": {"headline": "", "subhead": "", "cta_label": "지금 사전등록하기"},
  "problem": ["문제 1", "문제 2", "문제 3"],
  "solution": ["해결 약속 1", "해결 약속 2", "해결 약속 3"],
  "outcomes": ["수강 후 결과 1", "결과 2", "결과 3"],
  "curriculum_intro": "커리큘럼 섹션 한 줄 소개",
  "instructor_pitch": "강사 한 문단 소개 (3문장 이내)",
  "testimonials_placeholder": "[실제 수강생 후기 자리 — 수기 입력]",
  "faq": [{"q": "질문", "a": "답변"}],
  "pricing": {"label": "얼리버드 가격", "price_text": "₩가격 (얼리버드 N월 N일까지)", "cta_label": "지금 결제"}
}
"""


class MarketingSpecialist(BaseAgent):
    name = "marketing"
    display_name = "홍보·마케팅"
    system_prompt = SYSTEM

    def run(self, brief: dict) -> list[AgentResult]:
        """brief 예시 — 커리큘럼 결과(meta.raw)를 그대로 넣어줌."""
        curr = brief.get("curriculum") or {}
        prompt = f"""아래 커리큘럼을 바탕으로 랜딩페이지 1페이지 카피를 JSON으로 작성해 주세요.

코스 제목: {curr.get('title','')}
태그라인: {curr.get('tagline','')}
타깃: {curr.get('target_audience','')}
약속: {curr.get('promises', [])}
차시 수: {len(curr.get('lessons', []))}
가격대 힌트: {brief.get('price_hint','30~70만원대')}

JSON으로만 답하세요."""
        raw = self.call(prompt, max_tokens=4000)
        data = self._safe_json(raw)
        body_md = self._render_md(data)
        course_id = brief.get("course_id", "")

        result = AgentResult.new(
            agent=self.name,
            kind="landing_copy",
            title=f"{curr.get('title','코스')} — 랜딩 카피",
            body_md=body_md,
            summary=data.get("hero", {}).get("headline", "")[:120],
            course_id=course_id,
            meta={"raw": data, "brief": brief},
        )
        return [result]

    @staticmethod
    def _safe_json(s: str) -> dict:
        s = s.strip()
        if s.startswith("```"):
            s = s.split("```", 2)[1]
            if s.startswith("json"):
                s = s[4:]
            s = s.rsplit("```", 1)[0].strip()
        return json.loads(s)

    @staticmethod
    def _render_md(d: dict) -> str:
        h = d.get("hero", {})
        out = [f"# {h.get('headline','')}", "", f"> {h.get('subhead','')}", ""]
        out.append(f"**CTA:** {h.get('cta_label','신청하기')}")
        out += ["", "## 이런 문제, 한 번쯤 겪으셨죠"]
        for p in d.get("problem", []):
            out.append(f"- {p}")
        out += ["", "## 이 코스는 이렇게 해결합니다"]
        for s in d.get("solution", []):
            out.append(f"- {s}")
        out += ["", "## 수강 후"]
        for o in d.get("outcomes", []):
            out.append(f"- {o}")
        out += ["", "## 커리큘럼", d.get("curriculum_intro", ""), ""]
        out += ["## 강사 소개", d.get("instructor_pitch", ""), ""]
        out += ["## 후기", d.get("testimonials_placeholder", "[수강생 후기 자리]"), ""]
        out += ["## FAQ"]
        for f in d.get("faq", []):
            out += [f"**Q. {f.get('q','')}**", f.get("a", ""), ""]
        pr = d.get("pricing", {})
        out += ["## 가격", f"{pr.get('label','')}: {pr.get('price_text','')}",
                f"**CTA:** {pr.get('cta_label','지금 결제')}"]
        return "\n".join(out)
