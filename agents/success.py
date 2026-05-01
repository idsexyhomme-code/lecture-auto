"""Student Success Manager — 수강생·CS 에이전트.

오늘 단계: FAQ 자동 생성 + 수강생 문의 답변 초안.
환불·법적 응대는 자동 발송 절대 금지 (사람이 직접).
"""
from __future__ import annotations

import json
from .base import BaseAgent, AgentResult


SYSTEM = """당신은 한국어 1인 강사의 수강생 응대 어시스턴트다.

원칙:
- 답변은 항상 ‘공감 1문장 → 정확한 답 → 다음 행동 1개’ 3단 구조.
- 모르거나 정책 사안이면 ‘제가 강사에게 직접 확인 후 답변드릴게요’로 멈춘다 (절대 추측 금지).
- 환불·법적 이슈는 ‘강사 확인 필요’로만 답하고 어떤 약속도 하지 않는다.
- 친근한 존댓말. 이모지 1개 이내.
"""


class StudentSuccessManager(BaseAgent):
    name = "success"
    display_name = "수강생 관리"
    system_prompt = SYSTEM

    def run(self, brief: dict) -> list[AgentResult]:
        """brief 예시 (FAQ 생성):
        {"mode": "faq", "course_title": "...", "topic": "..."}

        또는 (Q&A 답변 초안):
        {"mode": "answer", "question": "...", "course_title": "...", "context_md": "..."}
        """
        mode = brief.get("mode", "answer")
        if mode == "faq":
            return self._faq(brief)
        return self._answer(brief)

    def _faq(self, brief: dict) -> list[AgentResult]:
        prompt = f"""다음 강의의 ‘수강 전 FAQ 7개’를 JSON 배열로 만들어 주세요.

강의: {brief.get('course_title','')}
주제: {brief.get('topic','')}
타깃: {brief.get('audience','')}

JSON 스키마:
[{{"q":"질문","a":"답변(공감→답→다음행동, 80자 이내)"}}]"""
        raw = self.call(prompt, max_tokens=2000)
        items = self._safe_json(raw)

        body_md = "\n\n".join([f"**Q. {x['q']}**\n{x['a']}" for x in items])
        result = AgentResult.new(
            agent=self.name,
            kind="faq",
            title=f"{brief.get('course_title','강의')} FAQ",
            body_md=body_md,
            summary=f"FAQ {len(items)}개",
            course_id=brief.get("course_id", ""),
            meta={"items": items},
        )
        return [result]

    def _answer(self, brief: dict) -> list[AgentResult]:
        prompt = f"""아래 수강생 질문에 답변 초안을 작성해 주세요. (강사가 검토 후 발송)

강의: {brief.get('course_title','')}
질문: {brief.get('question','')}
참고 문맥(있다면):
{brief.get('context_md','(없음)')}"""
        body_md = self.call(prompt, max_tokens=1200)
        result = AgentResult.new(
            agent=self.name,
            kind="qna_draft",
            title="Q&A 답변 초안",
            body_md=body_md,
            summary=brief.get("question", "")[:120],
            course_id=brief.get("course_id", ""),
            meta={"brief": brief},
        )
        return [result]

    @staticmethod
    def _safe_json(s: str) -> list:
        s = s.strip()
        if s.startswith("```"):
            s = s.split("```", 2)[1]
            if s.startswith("json"):
                s = s[4:]
            s = s.rsplit("```", 1)[0].strip()
        return json.loads(s)
