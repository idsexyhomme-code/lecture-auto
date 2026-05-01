"""Curriculum Architect — 강의 기획 에이전트."""
from __future__ import annotations

import json
from .base import BaseAgent, AgentResult


SYSTEM = """당신은 성인 학습자 대상 마이크로러닝 설계 전문가다.
입력된 주제와 타깃을 받으면 다음 원칙으로 커리큘럼을 설계한다.

1. **80/20 원칙**: 결과 약속 3개를 먼저 정의한다 (수강 후 학습자가 무엇을 할 수 있게 되는가).
2. **Bloom Taxonomy**: 차시는 이해 → 적용 → 분석 → 창조 순으로 배열한다.
3. **단일 학습목표**: 각 차시는 15분 안에 끝낼 수 있는 1개의 측정 가능한 학습목표만 갖는다.
   - 모호한 동사(이해한다, 안다) 금지. 항상 측정 가능한 동사 사용 (만든다, 비교한다, 분류한다, 설명한다).
4. **실습 산출물**: 각 차시는 학습자가 직접 만들어내는 1개의 산출물(워크시트·코드·문서)을 가진다.

출력은 반드시 아래 JSON 스키마로만 답한다. 코드펜스(```)도 붙이지 마라.

{
  "title": "코스 제목 (≤30자)",
  "tagline": "한 줄 가치제안 (≤45자)",
  "promises": ["수강 후 약속 1", "약속 2", "약속 3"],
  "target_audience": "타깃 한 줄 정의",
  "prerequisites": ["선수지식 1", "선수지식 2"],
  "lessons": [
    {
      "no": 1,
      "title": "차시 제목",
      "objective": "측정 가능한 학습목표 한 문장",
      "key_concepts": ["핵심개념 1", "핵심개념 2", "핵심개념 3"],
      "exercise": "수강생이 직접 만들 산출물 1개",
      "duration_min": 15
    }
  ],
  "assessment": "최종 평가/완주 인증 방식"
}
"""


class CurriculumArchitect(BaseAgent):
    name = "curriculum"
    display_name = "강의 기획"
    system_prompt = SYSTEM

    def run(self, brief: dict) -> list[AgentResult]:
        """brief 예시:
        {
          "topic": "ChatGPT로 자동화하는 1인 사업가 워크플로우",
          "audience": "초중급, 1인 콘텐츠 사업가",
          "duration_weeks": 4,
          "lesson_count": 12,
          "format": "video"  # video | pdf | lms
        }
        """
        prompt = f"""다음 강의의 커리큘럼을 설계해 주세요.

주제: {brief.get('topic','(미정)')}
타깃: {brief.get('audience','(미정)')}
총 길이: {brief.get('duration_weeks','?')}주, 차시 수 약 {brief.get('lesson_count','?')}개
최종 산출물 형태: {brief.get('format','video')}

JSON으로만 답하세요."""
        raw = self.call(prompt, max_tokens=4000)
        data = self._safe_json(raw)

        body_md = self._render_md(data)
        course_id = brief.get("course_id") or self._slugify(data.get("title", "course"))

        result = AgentResult.new(
            agent=self.name,
            kind="curriculum_outline",
            title=data.get("title", "(제목 없음)"),
            body_md=body_md,
            summary=data.get("tagline", "")[:120],
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
        lines = [f"# {d.get('title','')}", "", f"> {d.get('tagline','')}", ""]
        lines.append("## 결과 약속")
        for p in d.get("promises", []):
            lines.append(f"- {p}")
        lines += ["", f"**타깃:** {d.get('target_audience','')}", ""]
        if d.get("prerequisites"):
            lines.append("**선수지식:** " + ", ".join(d["prerequisites"]))
            lines.append("")
        lines.append("## 차시별 커리큘럼")
        lines.append("| # | 제목 | 학습목표 | 실습 | 분 |")
        lines.append("|---|---|---|---|---|")
        for l in d.get("lessons", []):
            lines.append(
                f"| {l['no']} | {l['title']} | {l['objective']} | {l['exercise']} | {l.get('duration_min',15)} |"
            )
        if d.get("assessment"):
            lines += ["", "## 평가", d["assessment"]]
        return "\n".join(lines)

    @staticmethod
    def _slugify(s: str) -> str:
        import re
        s = re.sub(r"\s+", "-", s.strip())
        s = re.sub(r"[^0-9A-Za-z\-가-힣]", "", s)
        return s[:40] or "course"
