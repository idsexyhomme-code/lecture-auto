#!/usr/bin/env python3
"""
숲사주 결과 1건 생성 — 3 AI 다중 검증 + 결과 페이지 자동 오픈.

흐름:
1. 인터랙티브로 이름·성별·생년월일·태어난 시간 입력
2. multi_llm.py (Claude + ChatGPT + Gemini) 호출
3. AI가 JSON으로 8 카드 본문 생성
4. result-template.html에 {{변수}} 치환
5. site/forest-saju/results/{token}.html 저장
6. 브라우저 자동 오픈

사용:
    python3 scripts/forest_saju.py
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import sys
import uuid
import webbrowser
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(REPO_ROOT / ".env")
except ImportError:
    pass

from agents.multi_llm import MultiLLMValidator


SAJU_SYSTEM_PROMPT = """당신은 "숲사주"의 따뜻한 AI 사주 컨설턴트입니다.

# 톤
- 다정한 친구 톤. 따뜻하고 부드러움.
- 숲·새싹·잎·나무·햇살·구름 같은 자연 메타포 활용.
- 한자·전문 명리 용어 금지. 쉬운 한국어.
- 한 문장이 너무 길지 않게, 호흡 있게.

# 절대 금지 (단정 표현)
- "운명을 예측합니다" / "100% 맞습니다" / "확실히" / "분명히"
- "월수익 N만원 보장" / "결혼 성공 보장" / "투자 추천"
- "병이 낫는다" / "건강 회복 보장"
- 약속·단정·미래 확언

# 권장 표현
- "흐름이 있어요" / "패턴이 보여요" / "결이 있어요"
- "참고할 수 있도록" / "한 번 더 살펴주세요"
- "마음이 향하는 쪽으로" / "내일 다시 봐도 같은 마음이면"

# 출력 형식 — 반드시 JSON만 (마크다운 블록 X)
{
  "title_emoji": "🐰 또는 🦊 🐱 🐰 🐻 🦌 🐰 🐶 등 사용자에게 어울리는 1개",
  "season": "2026년 봄/여름/가을/겨울 — 현재 계절",
  "poem": "4줄 짧은 시. 사용자 이름 자연스럽게 포함. 숲 메타포.",
  "cards": {
    "01": {
      "title": "기본 성향 — 메타포 한 줄 (예: 봄에 자라난 어린 새싹)",
      "body_1": "사용자의 기본 결을 따뜻하게. 2~3 문장.",
      "body_2": "단점·약점 영역을 부드럽게 짚되 비난 X. 2~3 문장.",
      "highlight": "🌿 이번 봄 한 줄 가이드"
    },
    "02": {
      "title": "연애운 메타포 (예: 두근거리는 잎의 흐름)",
      "body_1": "연애 패턴·결을 다정하게. 2~3 문장.",
      "body_2": "다가올 흐름 또는 만남 패턴. 단정 X. 2~3 문장.",
      "highlight": "💗 연애 한 줄 가이드"
    },
    "03": {
      "title": "결혼·동반자 메타포 (예: 함께 자라는 두 그루)",
      "body_1": "맞는 동반자의 결. 2~3 문장.",
      "body_2": "결혼 시기/마음의 준비. 단정 X. 2~3 문장.",
      "highlight": "💍 결혼 한 줄 가이드"
    },
    "04": {
      "title": "재물운 메타포 (예: 햇살 받는 작은 열매)",
      "body_1": "돈 다루는 성향·패턴. 2~3 문장.",
      "body_2": "재물 흐름. 투자 추천 X. 참고용 표현. 2~3 문장.",
      "highlight": "🪙 재물 한 줄 가이드"
    },
    "05": {
      "title": "일·사업운 메타포 (예: 햇살로 자라는 가지)",
      "body_1": "일의 결·잘 맞는 작업 방식. 2~3 문장.",
      "body_2": "다가오는 흐름·집중할 영역. 2~3 문장.",
      "highlight": "🌳 일 한 줄 가이드"
    },
    "06": {
      "title": "인간관계운 메타포 (예: 숲 속 친구들)",
      "body_1": "관계의 결·패턴. 2~3 문장.",
      "body_2": "한 번쯤 다시 살펴볼 관계. 2~3 문장.",
      "highlight": "🤝 관계 한 줄 가이드"
    },
    "07": {
      "title": "조심할 흐름 메타포 (예: 피해야 할 작은 비)",
      "body_1": "조심할 패턴·반복 실수. 2~3 문장.",
      "body_2": "구체적 회피 방법. 2~3 문장.",
      "highlight": "🌂 조심할 한 줄"
    },
    "08": {
      "title": "이번 달 한 줄 조언 — 카드 제목 한 줄",
      "highlight": "🌿 한 줄 조언 (이번 달 가장 중요한 한 문장. 30~50자.)"
    }
  },
  "forest_name": "사주 숲 별명 (예: '봄의 작은 숲', '햇살 깊은 숲', '구름 위 정원')",
  "forest_visual": "이모지 5개 조합 (예: 🌳🍄🐰🌱☁️)",
  "forest_desc": "숲 분위기 한 줄 묘사 (40~60자)"
}

# 핵심
- 모든 카피는 사용자 1명을 위한 맞춤 톤
- 사용자 이름을 자연스럽게 1~2회 언급
- 8 카드 다 채울 것. 빠진 항목 없이.
- JSON 외의 텍스트 출력 금지 (코드 블록도 금지)
"""


def cli_input(prompt: str, default: str = "") -> str:
    p = f"  {prompt}" + (f" [기본: {default}]" if default else "") + ": "
    val = input(p).strip()
    return val or default


def collect_personal_info() -> dict:
    print("\n" + "=" * 56)
    print("  🌿 숲사주 — 나만의 사주 숲이 열립니다 🌿")
    print("=" * 56)
    print("\n  생년월일 기반 AI 사주 리포트")
    print("  Claude + ChatGPT + Gemini 3 AI가 함께 봐드려요.\n")

    info = {}
    info["name"] = cli_input("이름 (또는 별명)", "토끼")
    info["gender"] = cli_input("성별 (남성/여성/기타)", "여성")
    info["birth_date"] = cli_input("생년월일 (YYYY.MM.DD)", "1995.04.12")
    info["birth_time"] = cli_input("태어난 시간 (예: 오전 9시 22분 / 모름)", "모름")
    info["concern"] = cli_input("요즘 가장 큰 고민 (선택, 없으면 엔터)", "")

    return info


def build_prompt(info: dict) -> str:
    today = datetime.now()
    parts = [f"## 사용자 정보\n- 이름: {info['name']}",
             f"- 성별: {info['gender']}",
             f"- 생년월일: {info['birth_date']}",
             f"- 태어난 시간: {info['birth_time']}"]
    if info.get("concern"):
        parts.append(f"- 요즘 고민: {info['concern']}")
    parts.append(f"\n## 오늘 날짜\n{today.strftime('%Y년 %m월 %d일')}")
    parts.append(
        f"\n## 요청\n"
        f"위 정보로 '{info['name']}'님의 숲사주 8 카드 리포트를 JSON으로 만들어주세요.\n"
        f"system prompt의 형식·금기·톤을 100% 지켜주세요."
    )
    return "\n".join(parts)


def extract_json(text: str) -> dict | None:
    """AI가 markdown 코드블록을 둘러도 JSON만 추출."""
    text = text.strip()
    # ```json ... ``` 블록 처리
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        text = m.group(1)
    # 중괄호 첫 시작 ~ 마지막 끝
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        return None
    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError as e:
        print(f"  ⚠️  JSON 파싱 실패: {e}")
        return None


async def run_diagnosis(info: dict) -> dict | None:
    print("\n  " + "-" * 52)
    print("  🌳 3 AI가 숲사주를 그리는 중... (1~3분 소요)")
    print("  " + "-" * 52 + "\n")

    validator = MultiLLMValidator(tier="basic")
    status = validator.status()
    print(f"  활성화 AI: {status['enabled']}/{status['total']}개 ({', '.join(status['enabled_llms'])})")
    if status['disabled']:
        for d in status['disabled_llms']:
            print(f"    ⏸  {d['llm']:12s} (skip — {d['needs']} 미설정)")
    print()

    prompt = build_prompt(info)
    try:
        result = await validator.run(
            prompt=prompt,
            system=SAJU_SYSTEM_PROMPT,
            max_tokens=4000,
            require_min_success=1,   # 1개라도 성공하면 OK
            build_consensus=True,
        )
    except Exception as e:
        print(f"\n  ❌ 진단 실패: {e}")
        return None

    print(f"  ✅ 완료 — 비용 ${result.total_cost_usd:.4f} · 시간 {result.elapsed_ms}ms · 합의도 {result.agreement:.2f}\n")

    # consensus 텍스트에서 JSON 추출
    data = extract_json(result.consensus)
    if data is None:
        # 개별 응답에서 다시 시도
        for r in result.responses:
            if r.success and r.text:
                data = extract_json(r.text)
                if data:
                    print(f"  💡 {r.llm} 응답에서 JSON 추출 성공")
                    break

    if data is None:
        print("\n  ❌ 모든 응답에서 JSON 추출 실패")
        print("\n  consensus 미리보기 (디버깅용):")
        print(result.consensus[:500])
        return None

    return {"data": data, "meta": result.to_dict(), "info": info}


def render_template(data: dict, info: dict) -> str:
    """result-template.html을 읽어 {{변수}} 치환."""
    tpl_path = REPO_ROOT / "site" / "forest-saju" / "result-template.html"
    html = tpl_path.read_text(encoding="utf-8")

    cards = data.get("cards", {})

    replacements = {
        "{{NAME}}":         f"{info['name']}님",
        "{{BIRTH_DATE}}":   info["birth_date"],
        "{{BIRTH_TIME}}":   info["birth_time"],
        "{{GENDER}}":       info["gender"],
        "{{SEASON}}":       data.get("season", ""),
        "{{POEM}}":         data.get("poem", "").replace("\n", "<br>"),
        "{{TITLE_EMOJI}}":  data.get("title_emoji", "🌿"),
        "{{FOREST_NAME}}":  data.get("forest_name", "고요한 숲"),
        "{{FOREST_VISUAL}}":data.get("forest_visual", "🌳🌱🍃🌿🍄"),
        "{{FOREST_DESC}}":  data.get("forest_desc", ""),
    }

    for n in range(1, 9):
        key = f"{n:02d}"
        c = cards.get(key, {})
        replacements[f"{{{{CARD_{key}_TITLE}}}}"]     = c.get("title", "")
        replacements[f"{{{{CARD_{key}_BODY_1}}}}"]    = c.get("body_1", "")
        replacements[f"{{{{CARD_{key}_BODY_2}}}}"]    = c.get("body_2", "")
        replacements[f"{{{{CARD_{key}_HIGHLIGHT}}}}"] = c.get("highlight", "")

    for placeholder, value in replacements.items():
        html = html.replace(placeholder, str(value))

    return html


def save_result(html: str, info: dict, raw: dict) -> Path:
    results_dir = REPO_ROOT / "site" / "forest-saju" / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    token = uuid.uuid4().hex[:10]
    name_slug = re.sub(r"[^a-zA-Z0-9가-힣]", "", info["name"])[:10]
    fname = f"{token}-{name_slug}.html"
    out_path = results_dir / fname
    out_path.write_text(html, encoding="utf-8")

    # 원본 데이터·meta도 같이 저장 (디버깅·재활용)
    meta_path = results_dir / f"{token}-{name_slug}.json"
    meta_path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")

    return out_path


def main():
    info = collect_personal_info()

    print("\n  " + "-" * 52)
    print("  📋 입력 확인")
    print("  " + "-" * 52)
    for k, v in info.items():
        if v:
            print(f"    {k:12s} : {v}")
    print()
    yn = input("  이 정보로 숲사주 생성할까요? (Y/n): ").strip().lower()
    if yn == "n":
        print("\n  취소했어요. 🌿")
        return

    result = asyncio.run(run_diagnosis(info))
    if not result:
        print("\n  진단 생성에 실패했어요. .env API key 상태 확인해주세요.")
        return

    print("  🎨 결과 페이지 생성 중...")
    html = render_template(result["data"], info)
    out_path = save_result(html, info, {"data": result["data"], "meta": result["meta"]})

    print("\n" + "=" * 56)
    print(f"  ✨ 완료! 결과 페이지: {out_path.name}")
    print("=" * 56)
    print(f"\n  📁 파일 위치:\n     {out_path}\n")
    print("  🌳 브라우저에서 자동으로 열어드릴게요...\n")

    # 자동 오픈
    webbrowser.open(f"file://{out_path}")


if __name__ == "__main__":
    main()
