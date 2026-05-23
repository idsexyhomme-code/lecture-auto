#!/usr/bin/env python3
"""
6 LLM 멀티 검증 시스템 테스트 스크립트.

사용법:
    cd /Users/seohyeongmin/Desktop/강의 홈페이지 제작
    python3 scripts/test_multi_llm.py status   # 활성화된 LLM 확인 (호출 X)
    python3 scripts/test_multi_llm.py ping     # 짧은 프롬프트로 모든 LLM 실측 호출
    python3 scripts/test_multi_llm.py demo     # Core Compass 진단 1건 실측 생성
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

# 프로젝트 루트 import
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# .env 자동 로드
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
except ImportError:
    pass

from agents.multi_llm import MultiLLMValidator, check_status


def cmd_status():
    print("=" * 60)
    print(" Multi-LLM 활성화 상태 ")
    print("=" * 60)
    status = check_status()
    print(f"\n총 어댑터: {status['total']}개")
    print(f"활성화 (API key 있음): {status['enabled']}개")
    print(f"비활성화 (API key 필요): {status['disabled']}개\n")

    print("✅ 활성화된 LLM:")
    for name in status["enabled_llms"]:
        print(f"   - {name}")

    if status["disabled_llms"]:
        print("\n⚠️  비활성화된 LLM (활성화하려면 .env에 추가):")
        for item in status["disabled_llms"]:
            print(f"   - {item['llm']:12s} → {item['needs']}")

    print()


async def cmd_ping():
    print("=" * 60)
    print(" Multi-LLM 실측 ping — 짧은 프롬프트로 모든 LLM 호출 ")
    print("=" * 60)
    validator = MultiLLMValidator()
    try:
        result = await validator.run(
            prompt="안녕하세요. 자신을 1문장으로 소개해주세요.",
            system="당신은 한국어 AI 어시스턴트입니다.",
            max_tokens=200,
            require_min_success=1,
            build_consensus=False,
        )
    except Exception as e:
        print(f"\n❌ 호출 실패: {e}")
        return

    print(f"\n총 비용: ${result.total_cost_usd:.6f}")
    print(f"소요 시간: {result.elapsed_ms}ms")
    print(f"성공: {result.success_count}개 / 실패: {result.fail_count}개")
    print(f"응답 합의도: {result.agreement:.3f}\n")

    for r in result.responses:
        status_icon = "✅" if r.success else "❌"
        print(f"{status_icon} {r.llm:12s} ({r.model})")
        if r.success:
            print(f"   {r.latency_ms}ms · ${r.cost_usd:.6f} · "
                  f"in={r.input_tokens} out={r.output_tokens}")
            print(f"   응답: {r.text.strip()[:150]}")
        else:
            print(f"   error: {r.error}")
        print()


async def cmd_demo():
    print("=" * 60)
    print(" Core Compass 1인 사업 진단 — 6 LLM 실측 생성 ")
    print("=" * 60)
    validator = MultiLLMValidator()
    try:
        result = await validator.run(
            prompt=(
                "30대 1인 사업가, 콘텐츠 마케팅 분야 3년차, "
                "월매출 200만원, 번아웃 직전, 자동화에 관심. "
                "이 사람의 사업 강점 3가지·약점 2가지·"
                "다음 90일 액션 5개를 짧게 정리해주세요."
            ),
            system=(
                "당신은 1인 사업가 전문 진단 컨설턴트입니다. "
                "실행 가능한 액션 중심으로, 추상적 조언은 피하세요."
            ),
            max_tokens=1500,
            require_min_success=2,
            build_consensus=True,
        )
    except Exception as e:
        print(f"\n❌ 호출 실패: {e}")
        return

    print(f"\n총 비용: ${result.total_cost_usd:.6f}")
    print(f"소요 시간: {result.elapsed_ms}ms")
    print(f"성공: {result.success_count}개 / 비활성화: {len(result.disabled_llms)}개")
    print(f"합의도: {result.agreement:.3f}\n")

    print("=" * 60)
    print(" Consensus (Claude가 통합한 최종 응답) ")
    print("=" * 60)
    print(result.consensus)
    print()

    # 개별 응답은 파일로 저장
    out = Path(__file__).resolve().parents[1] / "content" / "state" / "multi_llm_demo.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2),
                   encoding="utf-8")
    print(f"개별 응답·비용 상세: {out}")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"

    if cmd == "status":
        cmd_status()
    elif cmd == "ping":
        asyncio.run(cmd_ping())
    elif cmd == "demo":
        asyncio.run(cmd_demo())
    else:
        print(f"알 수 없는 명령: {cmd}")
        print("사용법: status | ping | demo")
        sys.exit(1)


if __name__ == "__main__":
    main()
