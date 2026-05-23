#!/usr/bin/env python3
"""
8 에이전트 SYSTEM 업그레이드 — 1건 테스트 brief 발주.

흐름:
1. briefs/test-new-agents-{ts}.json 생성 (curriculum 시작)
2. conductor.run_brief() 호출 → 새 SYSTEM(Amazon Working Backwards)으로 산출물 생성
3. F1 self_review + F2 CEO 게이트 → 텔레그램 승인 카드 발송
4. 회원이 ✅ 승인하면 cascade로 producer·marketing·success 자동 실행
5. 각각 새 SYSTEM 톤 (Pixar·옴니채널·CX) 확인 가능

검증 포인트:
- 산출물 톤이 이전(평범한 AI 분석)과 다른가? (DRI·계량적·동사 위주인가)
- 텔레그램 카드에 CEO V2 한 줄 의견이 나오는가?
- HARD ban 0건 / SOFT ban 적정량인가?
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(REPO_ROOT / ".env")
except ImportError:
    pass


def make_test_brief(course_id: str, topic: str, audience: str, transformation: str) -> dict:
    """curriculum 에이전트용 brief 생성. 새 Amazon Working Backwards SYSTEM 호출."""
    return {
        "agent": "curriculum",
        "brief": {
            "course_id": course_id,
            "topic": topic,
            "target_audience": audience,
            "before_state": "AI 도구는 알지만 실제 매출로 연결 안 됨. 콘텐츠 만들기에 시간 소진",
            "after_state": transformation,
            "duration_weeks": 4,
            "duration_minutes_per_lesson": 18,
            "tone": "단호하고 결과 지향. 동사형. 측정 가능",
        },
    }


def main():
    print("=" * 60)
    print("  🧪 8 에이전트 SYSTEM 업그레이드 — 1건 테스트")
    print("=" * 60)
    print()
    print("  curriculum 1건 발주 → cascade로 4개 에이전트 자동 실행")
    print("  - 📚 curriculum (Amazon Working Backwards · DRI)")
    print("  - 🎬 producer (Pixar Showrunner)")
    print("  - 📣 marketing (옴니채널 퍼널)")
    print("  - 🎓 success (CX Automation)")
    print()

    # 테스트 brief — 회원 본업과 가까운 주제
    brief = make_test_brief(
        course_id=f"test-1tier-upgrade-{int(time.time())}",
        topic="AI 콘텐츠 자동화로 월 500만 원 1인 사업 만들기",
        audience="N잡 직장인·1인 사업 초기(3개월 이내) — 콘텐츠 만드는 시간이 너무 오래 걸려서 손익이 안 맞는 사람",
        transformation="ChatGPT·Claude로 블로그 글 1편을 30분 안에 완성하고, 그것을 인스타·뉴스레터로 자동 재생산하는 시스템 구축",
    )

    briefs_dir = REPO_ROOT / "briefs"
    briefs_dir.mkdir(exist_ok=True)
    ts = int(time.time())
    brief_path = briefs_dir / f"test-new-agents-{ts}.json"
    brief_path.write_text(
        json.dumps(brief, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"  ✓ Brief 생성: {brief_path.name}")
    print()

    yn = input("  Conductor 실행할까요? (Y/n): ").strip().lower()
    if yn == "n":
        print("\n  취소했어요. brief 파일은 그대로 남아있어요.")
        print(f"  📁 {brief_path}")
        return

    print()
    print("  🔨 conductor 실행 중...")
    print("  텔레그램으로 진행 알림이 갑니다.")
    print()

    from agents.conductor import run_brief
    try:
        saved = run_brief(brief_path)
    except Exception as e:
        print(f"\n  ❌ 실행 실패: {e}")
        print(f"  brief 파일은 _failed/ 로 이동될 수 있습니다.")
        return

    print()
    print("  " + "=" * 56)
    print(f"  ✅ 완료 — {len(saved)}개 산출물 생성")
    print("  " + "=" * 56)
    print()
    for p in saved:
        print(f"    📄 {p.relative_to(REPO_ROOT)}")
    print()
    print("  📱 텔레그램 확인:")
    print("    1) 'CEO 의견 + 산출물 카드' 발송됨")
    print("    2) ✅ 누르면 cascade로 producer·marketing·success 자동 실행")
    print("    3) 4개 산출물 톤 비교해서 새 SYSTEM 적용 여부 확인")
    print()


if __name__ == "__main__":
    main()
