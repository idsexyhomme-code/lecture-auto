"""Idea Intake — 회원님의 자유 텍스트 아이디어를 명확화 대화로 풀어 brief으로 변환.

도메인 에이전트가 아니라 *메타 에이전트*. brief을 만들기 전 대화 단계만 책임진다.

흐름:
  1. 회원님이 자유 텍스트로 아이디어 던짐
  2. propose(history) 호출 → LLM이 ASK(질문) 또는 READY(brief 완성) 반환
  3. ASK면 history에 응답 추가하고 회원님 답변 받아 다시 propose() 반복
  4. READY면 brief 객체를 시스템에 던질 준비 완료

이 단계에서는 텔레그램·파일 시스템 통합 없음. 순수 두뇌 함수.
Step 2에서 Telegram poll.py가 이 함수를 호출하는 형태로 통합.
"""
from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

from .base import BaseAgent, REPO_ROOT, list_approved

log = logging.getLogger("idea_intake")


# ── 결과 타입 ────────────────────────────────────────────────
@dataclass
class IntakeResult:
    """propose() 한 턴의 결과."""
    action: str  # "ASK" 또는 "READY"
    message: str  # 회원님께 보여줄 메시지 (한국어)
    brief: Optional[dict] = None  # READY일 때만 — 시스템에 던질 brief
    raw: str = ""  # 디버그용 원본 LLM 응답


# ── 시스템 프롬프트 ──────────────────────────────────────────
SYSTEM = """당신은 '코어 캠퍼스'의 Idea Intake 어시스턴트다.

회원님(서형)이 자유롭게 던진 아이디어를 받아, 시스템의 도메인 에이전트
하나에 정확히 매핑되는 brief JSON으로 변환하는 게 당신의 역할이다.

## 코어 캠퍼스의 도메인 에이전트 (이 중 하나를 선택)

1. **curriculum** — 새 코스의 차시 구조(커리큘럼) 설계
2. **producer** — 특정 코스의 한 차시 영상 스크립트 작성
3. **marketing** — 코스 랜딩 페이지 카피 + (옵션) SNS·이메일
4. **success** — FAQ 7개 또는 수강생 Q&A 답변 초안
5. **site_developer** — 사이트 메타데이터·디자인 토큰·HTML 슬롯 변경 (실제 적용)
6. **ui_designer** — 디자인 *시안 3변형* 생성 (시니어 디자이너). 사이트 리디자인,
   대문(히어로) 새로 만들기, 톤 전환, '구글 Stitch처럼 시안 좀 뽑아줘' 류는 모두 여기.
   *시안 단계*만 책임 — 승인된 시안은 site_developer가 받아서 실제 적용함.

## 라우팅 가이드 — site_developer vs ui_designer

- **시각·레이아웃·톤·구도를 *새로 디자인*해 달라는 요청 → ui_designer**
  ("대문 새로 만들어줘", "다른 느낌으로 리디자인", "스티치처럼 시안", "히어로 다시")
- **이미 정해진 톤 안에서 텍스트·색·정렬만 바꿔달라는 요청 → site_developer**
  ("제목을 X로 바꿔줘", "메인 컬러를 더 따뜻하게", "코스 순서 바꿔줘")
- 모호하면 ui_designer로 보내는 게 안전 (시안 3개 보고 회원님이 고름).

## 행동 규칙

매 턴 두 가지 중 정확히 하나를 한다.

**[ASK]** 의도가 모호하거나 필수 정보가 빠졌으면 짧은 질문 1-3개를 던진다.
- 한 메시지에 1-3개 질문만 (3개 넘기면 회원님이 부담)
- 가능하면 객관식 옵션 제시 (예: "8차시 / 12차시 / 직접 입력 — 어느 게 좋을까요?")
- 명백히 추론 가능한 건 묻지 않는다 (현재 컨텍스트의 기존 코스·브랜드 톤 활용)
- 한국어 친근한 존댓말. 군더더기 없이.

**[READY]** 충분히 명확해지면 brief JSON을 만들고 회원님 확인을 요청한다.
- 모든 필수 필드가 채워졌고 추측이 50% 이상 들어간 항목이 없을 때만 READY
- READY일 때 message에는 brief 요약과 "이대로 진행해도 될까요?" 같은 확인 요청

## 각 agent의 필수 필드

curriculum:
  agent: "curriculum"
  brief: {
    course_id: 슬러그(예: "claude-video"). 한국어 주제면 영문으로 자동 변환
    topic: 코스 주제 한 줄
    audience: 타깃 (한 문장. 회원님 기존 타깃과 일관성 권장)
    duration_weeks: 4 / 6 / 8 등 정수
    lesson_count: 8 / 12 / 16 등 정수
    format: "video" | "pdf" | "lms"
  }

producer:
  agent: "producer"
  brief: {
    course_id: 기존 코스의 ID
    course_title: 기존 코스 제목
    lesson_no: 정수 (몇 차시인지)
    lesson_title, objective, key_concepts(배열), exercise, duration_min
  }

marketing:
  agent: "marketing"
  brief: {
    course_id: 기존 코스 ID
    curriculum: { title, tagline, target_audience, promises(배열), lessons(배열) }
    price_hint: "30~50만원대" 같은 가격 힌트
  }

success:
  agent: "success"
  brief: {
    mode: "faq" | "answer"
    course_id, course_title, topic, audience
  }

site_developer:
  agent: "site_developer"
  brief: {
    instruction: 무엇을 다듬을지 자연어 한 단락
    brand_tone: "차분하고 단단한 한국어..."
    target_audience: 한 줄
    restrictions: "WCAG AA 유지, 과장 금지" 등
  }

ui_designer:
  agent: "ui_designer"
  brief: {
    target: "hero" | "home_intro" | "footer" | "landing_full"
    purpose: 한 줄 — 이 디자인이 해결해야 할 핵심 사용자 문제
    audience: 한 줄 — 타깃 사용자 묘사
    style_keywords: [배열, 예: ["미니멀","따뜻한 톤","학술적"]]
    color_mood: "warm" | "cool" | "monochrome" | "vibrant" | null
    reference_urls: [URL 배열, 옵션 — 영감 받을 사이트 1-3개]
    additional_context: 자유 텍스트 (옵션)
  }
  주의: ui_designer는 *시안*만 만든다. brief 단계에서는 reference_urls가
  비어있어도 OK — color_mood와 style_keywords가 충분하면 진행 가능.

## 출력 형식 — 반드시 이 JSON만 (다른 텍스트 일체 금지)

```
{
  "action": "ASK" | "READY",
  "message": "회원님께 보낼 메시지 (한국어, 마크다운 OK, 100-300자)",
  "brief": null 또는 { "agent": "...", "brief": { ... } }
}
```

코드펜스(```)도 붙이지 말고 순수 JSON만 출력한다.

## 회원님 시간을 아끼는 원칙

- 3턴 이내로 READY에 도달하는 게 이상적 (회원님이 첫 메시지로 충분히 명확하게 줄 수도 있음)
- 복합 요청("커리큘럼 + 1차시 스크립트 + 랜딩카피 한 번에")이면 첫 작업(curriculum)으로 좁혀
  brief을 만들고, READY message에 "이게 끝나면 다음 작업도 이어서 진행할까요?"로 안내
- 회원님의 톤 — 차분하고 단단한 한국어. 과장 금지.
"""


class IdeaIntake(BaseAgent):
    name = "idea_intake"
    display_name = "아이디어 안내자"
    system_prompt = SYSTEM

    def propose(self, history: list[dict], context: Optional[dict] = None) -> IntakeResult:
        """대화 한 턴 처리.

        history: [{"role": "user"|"assistant", "content": "..."}]
        context: 선택. 없으면 _build_context()로 자동 수집 (등록 코스 등).
        """
        if context is None:
            context = self._build_context()

        sys_with_ctx = (
            self.system_prompt
            + "\n\n## 현재 컨텍스트 (참고)\n"
            + json.dumps(context, ensure_ascii=False, indent=2)
        )

        log.info("[idea_intake] propose — history len=%d", len(history))
        msg = self.client.messages.create(
            model=self.model,
            max_tokens=2000,
            system=sys_with_ctx,
            messages=history,
        )
        raw = "".join(b.text for b in msg.content if getattr(b, "type", None) == "text")

        parsed = self._parse_json(raw)

        action = parsed.get("action", "ASK")
        if action not in ("ASK", "READY"):
            action = "ASK"

        return IntakeResult(
            action=action,
            message=parsed.get("message", "(빈 응답)"),
            brief=parsed.get("brief") if action == "READY" else None,
            raw=raw,
        )

    # ── 내부 헬퍼 ───────────────────────────────────────────
    @staticmethod
    def _parse_json(raw: str) -> dict:
        s = raw.strip()
        if s.startswith("```"):
            s = s.split("```", 2)[1]
            if s.startswith("json"):
                s = s[4:]
            s = s.rsplit("```", 1)[0].strip()
        # 가끔 LLM이 앞뒤 텍스트 붙이는 경우 — { 부터 } 까지 추출
        if not s.startswith("{"):
            i = s.find("{")
            j = s.rfind("}")
            if i >= 0 and j > i:
                s = s[i:j + 1]
        try:
            return json.loads(s)
        except json.JSONDecodeError as e:
            log.error("[idea_intake] JSON parse failed: %s\nRAW: %s", e, raw[:500])
            # fallback — 원본 텍스트를 그대로 message로
            return {"action": "ASK", "message": raw.strip(), "brief": None}

    @staticmethod
    def _build_context() -> dict:
        """현재 등록된 코스 목록·사이트 메타 등 컨텍스트 자동 수집."""
        courses = []
        for r in list_approved():
            if r.kind != "curriculum_outline":
                continue
            tagline = (r.meta.get("raw", {}) or {}).get("tagline", "") if r.meta else ""
            courses.append({
                "course_id": r.course_id,
                "title": r.title,
                "tagline": tagline,
            })

        site_brand = ""
        cfg_path = REPO_ROOT / "site_config.json"
        if cfg_path.exists():
            try:
                cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
                site_brand = cfg.get("site_name", "") + " — " + cfg.get("site_subtagline", "")
            except Exception:
                pass

        return {
            "site_brand": site_brand,
            "registered_courses": courses,
        }


# ── CLI 진입점 ──────────────────────────────────────────────
def _cli():
    """단발 또는 대화 모드. ANTHROPIC_API_KEY 필요.

    단발:    python -m agents.idea_intake "Claude SOP 시리즈 3 만들어줘"
    대화:    python -m agents.idea_intake     (인자 없이)
    """
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "WARNING"),
        format="%(asctime)s [%(name)s] %(message)s",
    )

    intake = IdeaIntake()

    args = sys.argv[1:]
    if args:
        first_msg = " ".join(args)
        history = [{"role": "user", "content": first_msg}]
        result = intake.propose(history)
        print(f"\n👤 입력: {first_msg}\n")
        print(f"🤖 [{result.action}] {result.message}\n")
        if result.brief:
            print("📝 brief:")
            print(json.dumps(result.brief, ensure_ascii=False, indent=2))
        return

    # 대화 모드
    print("코어 캠퍼스 — Idea Intake 대화 모드")
    print("(/quit 또는 빈 입력으로 종료)\n")
    history: list[dict] = []
    while True:
        try:
            msg = input("👤 > ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not msg or msg.lower() in ("/quit", "/exit", "/q"):
            break
        history.append({"role": "user", "content": msg})
        try:
            result = intake.propose(history)
        except Exception as e:
            print(f"⚠️ 오류: {e}")
            continue
        # assistant 응답을 history에 추가 (다음 턴 컨텍스트용)
        history.append({
            "role": "assistant",
            "content": json.dumps({
                "action": result.action,
                "message": result.message,
                "brief": result.brief,
            }, ensure_ascii=False),
        })
        print(f"\n🤖 [{result.action}] {result.message}\n")
        if result.action == "READY":
            print("📝 brief 준비됨:")
            print(json.dumps(result.brief, ensure_ascii=False, indent=2))
            print("\n(Step 1 검증 — 실제 시스템에 던지지는 않음. Step 2~3에서 통합)")
            break


if __name__ == "__main__":
    _cli()
