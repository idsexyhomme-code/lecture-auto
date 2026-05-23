"""Core Compass 7섹션 진단 생성 — Claude API.

사용자 입력 (성향·관심·시간 등) 기반 7섹션 리포트 생성.
result.html 템플릿 채워서 개인 URL 위치에 저장.

호출:
    from scripts.generate_diagnosis import generate_full_diagnosis
    result = generate_full_diagnosis(
        order_id="order_abc",
        email="user@example.com",
        user_name="홍길동",
        form_data={
            "available_hours_per_week": 10,
            "interests": ["AI 자동화", "콘텐츠"],
            "current_stage": "아이디어 검증",
            ...
        },
    )
"""
from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from scripts.compass_token import generate_token

log = logging.getLogger(__name__)

KST = timezone(timedelta(hours=9))
RESULT_TPL = ROOT / "site/landing/core-compass/v4/result.html"
OUTPUT_BASE = ROOT / "site/landing/core-compass/r"


SYSTEM_PROMPT = """\
당신은 Core Compass의 진단 작성자입니다. 한국어 1인 사업가에게 1페이지 진단 리포트를 작성합니다.

원칙 (헌법 §4):
- 운명·사주·100% 보장 카피 절대 금지
- "정리합니다", "제안합니다", "참고합니다" 사용
- 구체적·실행 가능한 행동
- 90일 안 시작 가능한 단위

출력 형식 (JSON):
{
  "user_persona": "실행형 솔로" | "아이디어형" | "전문가형" | "서비스형" | "콘텐츠형",
  "one_line_insight": "한 줄 핵심 (15자 안)",
  "sections": [
    {"num": 1, "title": "당신의 일하는 성향", "body": "2~3문장 (한글 키프할)"},
    {"num": 2, "title": "지금 가장 잘 맞는 사업 방향", "body": "3개 추천"},
    {"num": 3, "title": "피해야 할 수익모델", "body": "2~3개 이유"},
    {"num": 4, "title": "90일 우선순위 매트릭스", "body": "1주~12주 시간순"},
    {"num": 5, "title": "첫 상품/서비스 아이디어", "body": "9,900~29,000원 3개"},
    {"num": 6, "title": "90일 실행 로드맵", "body": "주 단위 체크리스트"},
    {"num": 7, "title": "이번 주 바로 할 일 3가지", "body": "오늘·이번주·7일 안 3가지"}
  ],
  "recommended_courses": [
    {"slug": "claude-launchpad", "reason": "..."},
    {"slug": "claude-autowork", "reason": "..."}
  ]
}
"""


def call_claude_api(form_data: dict, user_name: str) -> dict:
    """Claude API 호출 — 진단 생성."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        # Fallback — 가상 데이터 반환 (개발용)
        log.warning("ANTHROPIC_API_KEY missing — fallback diagnosis")
        return _fallback_diagnosis(user_name, form_data)

    try:
        import anthropic
    except ImportError:
        log.error("anthropic SDK not installed")
        return _fallback_diagnosis(user_name, form_data)

    client = anthropic.Anthropic(api_key=api_key)
    user_msg = (
        f"사용자 이름: {user_name}\n"
        f"입력 폼 데이터: {json.dumps(form_data, ensure_ascii=False)}\n\n"
        "위 정보로 Core Compass 1페이지 진단을 작성하세요. JSON 형식만 출력."
    )

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        )
        text = response.content[0].text
        # JSON 추출
        if text.startswith("```"):
            text = text.split("```", 2)[1].lstrip("json").strip()
        return json.loads(text)
    except Exception as e:
        log.error("Claude API error: %s", e)
        return _fallback_diagnosis(user_name, form_data)


def _fallback_diagnosis(user_name: str, form_data: dict) -> dict:
    """API 실패 시 기본 진단."""
    return {
        "user_persona": "실행형 솔로",
        "one_line_insight": "작게 만들고 빠르게 검증.",
        "sections": [
            {"num": 1, "title": "당신의 일하는 성향", "body": f"{user_name}님은 '실행형 솔로'에 가깝습니다. 작게 만들고 빠르게 반응을 확인할 때 성과가 나는 타입입니다."},
            {"num": 2, "title": "지금 가장 잘 맞는 사업 방향", "body": "디지털 자료(PDF·노션 템플릿), 짧은 라이브 코칭, AI 활용 미니 코스 3가지를 시도해볼 수 있습니다."},
            {"num": 3, "title": "피해야 할 수익모델", "body": "실물 상품(재고 부담)·다인 운영형 서비스·고비용 광고 의존은 당분간 미루시길 추천합니다."},
            {"num": 4, "title": "90일 우선순위 매트릭스", "body": "1~30일: 시장 검증·MVP / 31~60일: 트래픽 확보 / 61~90일: 첫 결제 시도."},
            {"num": 5, "title": "첫 상품 아이디어", "body": "① 9,900원 PDF 가이드 ② 49,000원 30분 코칭 ③ 19,000원 7일 챌린지."},
            {"num": 6, "title": "90일 실행 로드맵", "body": "주 단위 체크포인트 — 1주: 1줄 정의 / 2~3주: MVP / 4주: 결제 셋업 / 5~12주: 콘텐츠 발행."},
            {"num": 7, "title": "이번 주 바로 할 일 3가지", "body": "오늘: 카톡 친구 3명에게 메시지. 이번 주: 노션 페이지 1장. 7일 안: 무료 베타 3명."},
        ],
        "recommended_courses": [
            {"slug": "claude-launchpad", "reason": "MVP 만들기 단계에 가장 잘 맞아요."},
            {"slug": "claude-autowork", "reason": "반복 업무 줄이는 자동화로 본업 시간 확보."},
        ],
    }


def render_result_html(diagnosis: dict, user_name: str) -> str:
    """진단 결과 → result.html 채우기."""
    if not RESULT_TPL.exists():
        raise FileNotFoundError(f"Template not found: {RESULT_TPL}")
    html = RESULT_TPL.read_text(encoding="utf-8")

    html = html.replace("{{USER_NAME}}", user_name)
    # 7섹션 채우기 (template variables {{SECTION_N_TITLE/BODY}})
    for sec in diagnosis.get("sections", []):
        n = sec["num"]
        html = html.replace(f"{{{{SECTION_{n}_TITLE}}}}", sec.get("title", ""))
        html = html.replace(f"{{{{SECTION_{n}_BODY}}}}", sec.get("body", ""))

    # 코스 추천 ({{TOPIC}})
    persona = diagnosis.get("user_persona", "")
    html = html.replace("{{TOPIC}}", persona)

    return html


def generate_full_diagnosis(
    *,
    order_id: str,
    email: str,
    user_name: str,
    form_data: dict | None = None,
) -> dict:
    """결제 후 진단 전체 흐름.

    1. Claude API로 7섹션 생성
    2. result.html 채우기
    3. 토큰 발급 + 개인 URL 생성
    4. /site/landing/core-compass/r/{token}/index.html 저장

    Returns:
        {"ok": bool, "result_url": str, "token": str, "one_line_insight": str}
    """
    form_data = form_data or {}

    # 1. 진단 생성
    diagnosis = call_claude_api(form_data, user_name)

    # 2. result.html 채우기
    try:
        html = render_result_html(diagnosis, user_name)
    except Exception as e:
        return {"ok": False, "error": str(e)}

    # 3. 토큰 발급
    token_rec = generate_token(order_id=order_id, email=email)
    token = token_rec["token"]

    # 4. 저장
    output_dir = OUTPUT_BASE / token
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "index.html").write_text(html, encoding="utf-8")

    base_url = os.environ.get("SITE_BASE_URL", "https://corecampus.kr")
    result_url = f"{base_url}/site/landing/core-compass/r/{token}/"

    log.info("Diagnosis generated: %s → %s", order_id, result_url)
    return {
        "ok": True,
        "token": token,
        "result_url": result_url,
        "one_line_insight": diagnosis.get("one_line_insight", ""),
        "user_persona": diagnosis.get("user_persona", ""),
    }


if __name__ == "__main__":
    # 테스트
    result = generate_full_diagnosis(
        order_id="test_order_001",
        email="test@example.com",
        user_name="테스트",
        form_data={"interests": ["AI 자동화"], "available_hours_per_week": 10},
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
