#!/usr/bin/env python3
"""
회원님 개인 진단 1건 생성 — 3 AI 다중 검증 (basic tier)

대화형으로 정보를 받아 Core Compass 진단을 생성합니다.
사용:
    python3 scripts/my_diagnosis.py
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
except ImportError:
    pass

from agents.multi_llm import MultiLLMValidator


DIAGNOSIS_SYSTEM_PROMPT = """당신은 1인 사업가 전문 진단 컨설턴트 Core Compass입니다.

## 절대 규칙
- "운명", "사주", "100%", "보장", "확실히" 같은 단정적 표현 금지
- 데이터 기반 분석 + 실행 가능한 액션만 제시
- 추상적 조언 금지, 구체적 다음 행동 위주
- 회원의 사업가로서의 강점·약점·기회를 정직하게 짚되 따뜻하게

## 진단 출력 형식 (마크다운)
### 1. 사업가 강점 3가지 (각 2-3문장)
### 2. 주의할 약점 2가지 (각 2-3문장)
### 3. 90일 실행 액션 5개 (각 액션은 30일 단위 마일스톤 포함)
### 4. 첫 90일 우선순위 1가지 (가장 시급한 액션)

총 분량 1,500~2,500자."""


def cli_input(prompt: str, default: str = "") -> str:
    """인터랙티브 입력 — default 있으면 빈 입력 시 사용."""
    p = f"{prompt}" + (f" [기본: {default}]" if default else "") + ": "
    val = input(p).strip()
    return val or default


def collect_personal_info() -> dict:
    print("=" * 60)
    print(" Core Compass — 회원님 개인 진단 (3 AI 다중 검증)")
    print("=" * 60)
    print()
    print("아래 정보를 입력해주세요. 정확할수록 진단이 정확해집니다.")
    print("(엔터로 기본값 사용 가능, 비밀번호·결제정보는 묻지 않습니다)")
    print()

    info = {}
    info["name"] = cli_input("1. 이름 (또는 닉네임)", "서형")
    info["age_range"] = cli_input("2. 연령대 (20대/30대/40대...)", "30대")
    info["industry"] = cli_input("3. 현재 사업/관심 분야",
                                  "AI 콘텐츠·자동화 시스템 (Core Campus 운영)")
    info["stage"] = cli_input(
        "4. 사업 단계 (예비창업/1년차/3년차+)", "운영 중"
    )
    info["monthly_revenue"] = cli_input(
        "5. 현재 월매출 (만원 단위, 없으면 0)", "0"
    )
    info["main_pain"] = cli_input(
        "6. 지금 가장 막힌 영역 (예: 고객 확보·콘텐츠 지속·자동화...)",
        "1인 사업 자기이해 진단 시장 진입 + 첫 매출 확보"
    )
    info["main_goal"] = cli_input(
        "7. 다음 90일 안에 이루고 싶은 것",
        "Core Compass 출시 → 첫 100건 결제 확보"
    )
    info["resources"] = cli_input(
        "8. 보유 자원 (시간/돈/팀/도구 등 자유롭게)",
        "주 30시간, 자본 100만원, 1인, Claude·ChatGPT·Gemini API + Mac mini"
    )
    info["tried_before"] = cli_input(
        "9. 이미 시도해본 것·실패한 것 (선택)",
        "지난 8개월 v1~v6 랜딩 빌드, 19개 코스, 블로그 자동화 시스템 구축"
    )

    return info


def build_prompt(info: dict) -> str:
    return f"""다음 1인 사업가에 대해 진단해주세요.

## 기본 정보
- 이름: {info['name']}
- 연령대: {info['age_range']}
- 현재 분야: {info['industry']}
- 사업 단계: {info['stage']}
- 월매출: {info['monthly_revenue']}만원

## 현재 상황
- 가장 막힌 영역: {info['main_pain']}
- 다음 90일 목표: {info['main_goal']}
- 보유 자원: {info['resources']}
- 이미 시도/실패: {info['tried_before']}

위 정보를 바탕으로 강점·약점·90일 액션 진단을 작성하세요."""


async def run_diagnosis(info: dict) -> dict:
    print()
    print("=" * 60)
    print(" 3 AI 다중 검증 진단 생성 중 (1~2분 소요)")
    print("=" * 60)
    print()

    validator = MultiLLMValidator(tier="basic")
    status = validator.status()
    print(f"  활성화 LLM: {status['enabled']}/{status['total']} ({', '.join(status['enabled_llms'])})")
    if status['disabled']:
        for d in status['disabled_llms']:
            print(f"  ⏸  {d['llm']:12s} (skip — {d['needs']} 미설정)")
    print()
    print("  [Step 1] 각 AI 독립 분석 (병렬)...")

    prompt = build_prompt(info)
    try:
        result = await validator.run(
            prompt=prompt,
            system=DIAGNOSIS_SYSTEM_PROMPT,
            max_tokens=2500,
            require_min_success=2,
            build_consensus=True,
        )
    except Exception as e:
        print(f"\n❌ 진단 실패: {e}")
        return {}

    print(f"  [Step 2] Claude가 {result.success_count}개 응답 통합 중...")
    print()
    print(f"✅ 완료 — 비용 ${result.total_cost_usd:.4f} · 시간 {result.elapsed_ms}ms · 합의도 {result.agreement:.2f}")
    print()

    return {
        "info": info,
        "result": result.to_dict(),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }


def save_and_show(data: dict) -> None:
    out_dir = Path(__file__).resolve().parents[1] / "content" / "my_diagnosis"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    name_slug = data["info"]["name"].replace(" ", "_")[:20]
    out_path = out_dir / f"{ts}-{name_slug}.json"
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    md_path = out_dir / f"{ts}-{name_slug}.md"
    md = f"""# Core Compass 진단 — {data['info']['name']}

> 생성일: {data['generated_at']}
> 3 AI 다중 검증 — {', '.join(data['result']['enabled_llms'])}
> 합의도: {data['result']['agreement']:.2f} · 비용: ${data['result']['total_cost_usd']:.4f}

---

## 통합 진단 (Claude가 3 AI 응답을 종합)

{data['result']['consensus']}

---

## 개별 AI 응답 (참고)

"""
    for r in data['result']['responses']:
        if r['success'] and r['text']:
            md += f"\n### {r['llm']} ({r['model']})\n\n{r['text']}\n\n---\n"

    md_path.write_text(md, encoding="utf-8")

    print("=" * 60)
    print(" 🎯 통합 진단 결과")
    print("=" * 60)
    print()
    print(data['result']['consensus'])
    print()
    print("=" * 60)
    print(f" 📁 저장 위치:")
    print(f"    {md_path}")
    print(f"    {out_path}")
    print("=" * 60)


def main():
    info = collect_personal_info()

    print()
    print("=" * 60)
    print(" 입력 요약")
    print("=" * 60)
    for k, v in info.items():
        print(f"  {k:18s}: {v[:60]}")
    print()
    yn = input("이 정보로 진단 생성할까요? (Y/n): ").strip().lower()
    if yn == "n":
        print("취소됨.")
        return

    data = asyncio.run(run_diagnosis(info))
    if data:
        save_and_show(data)


if __name__ == "__main__":
    main()
