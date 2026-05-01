"""Content Producer — 콘텐츠 제작 에이전트.

승인된 커리큘럼(또는 단일 차시)을 받아서 영상 스크립트, 슬라이드 개요, 교안 핵심 요약을 만든다.
오늘 단계에서는 영상 스크립트 1차시 생성에 집중하고 슬라이드/PDF는 후속에서 확장한다.
"""
from __future__ import annotations

from .base import BaseAgent, AgentResult


SYSTEM = """당신은 한국어 1인 강사를 위한 영상 강의 스크립트 작가다.

다음 5단 구조로만 작성한다.

1. **HOOK (45초)** — 수강생의 ‘오늘의 고통’을 한 문장으로 정확히 짚고, 강의가 그것을 어떻게 끝내줄지 약속.
2. **PROMISE (30초)** — 이 차시가 끝나면 수강생이 무엇을 할 수 있게 되는지 1문장.
3. **CORE (8–10분)** — 핵심 개념 3개를 ‘설명 → 예시 → 반례 → 정리’ 구조로 전개. 각 개념은 ‘메모리 페그(이미지·은유·숫자)’로 기억에 박히게.
4. **EXERCISE (3–4분)** — 수강생이 영상 일시정지하고 직접 만들 산출물을 단계별로 안내.
5. **CTA (30초)** — 다음 차시 예고 + 행동 요청 (댓글, 공유, 다음 영상 시청 중 1개만).

표현 규칙:
- 구어체로 작성하되 군더더기(어, 음, 그) 없이 깔끔하게.
- 한 문장은 30자 이내를 지향.
- 숫자·고유명사는 정확하게.
- 과장·확정형(‘반드시’, ‘100%’) 금지. 대신 ‘대부분의 경우’, ‘제 경험상’.
- 마크다운으로 각 섹션은 ## 헤더로 명시.
- 끝에 ‘예상 분량: N분’ 한 줄 추가.
"""


class ContentProducer(BaseAgent):
    name = "producer"
    display_name = "콘텐츠 제작"
    system_prompt = SYSTEM

    def run(self, brief: dict) -> list[AgentResult]:
        """brief 예시:
        {
          "course_id": "...",
          "course_title": "...",
          "lesson_no": 1,
          "lesson_title": "...",
          "objective": "...",
          "key_concepts": ["...", "..."],
          "exercise": "...",
          "duration_min": 15
        }
        """
        prompt = f"""아래 차시의 영상 스크립트를 5단 구조(HOOK/PROMISE/CORE/EXERCISE/CTA)로 작성해 주세요.

코스: {brief.get('course_title','')}
차시 #{brief.get('lesson_no','?')}: {brief.get('lesson_title','')}
학습목표: {brief.get('objective','')}
핵심개념: {", ".join(brief.get('key_concepts', []))}
실습: {brief.get('exercise','')}
목표 분량: {brief.get('duration_min',15)}분

마크다운으로만 답하세요. 코드펜스는 붙이지 말고."""
        body_md = self.call(prompt, max_tokens=4000)

        title = f"#{brief.get('lesson_no','?')} {brief.get('lesson_title','(차시)')}"
        summary = brief.get("objective", "")[:120]

        result = AgentResult.new(
            agent=self.name,
            kind="lecture_script",
            title=title,
            body_md=body_md,
            summary=summary,
            course_id=brief.get("course_id", ""),
            meta={"brief": brief},
        )
        return [result]
