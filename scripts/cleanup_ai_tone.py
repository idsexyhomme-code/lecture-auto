"""사이트 카피의 AI 티 단어 일괄 치환.

원본 JSON(`content/approved/*.json`) 의 marketing/curriculum/lecture_script body 안
AI 티 단어를 사람 톤으로 치환. 그 후 빌드 시 코스 페이지에 반영됨.

사용:
    python scripts/cleanup_ai_tone.py            # dry-run (변경 미리보기만)
    python scripts/cleanup_ai_tone.py --apply    # 실제 적용
"""
from __future__ import annotations
import argparse, json, re, glob
from pathlib import Path
from collections import Counter

REPO = Path(__file__).resolve().parent.parent

# ───────────────────────────────────────────────────────
# 단어 치환 룰표 — AI 티 단어 → 사람 톤
# 길이 긴 패턴부터 (긴 것이 짧은 것을 포함하면 긴 것 먼저)
# ───────────────────────────────────────────────────────
RULES = [
    # 합성어 먼저 (긴 것)
    ("자동화 시스템", "자동 처리"),
    ("자동화 워크플로우", "자동 처리 방법"),
    ("자동화 워크플로", "자동 처리 방법"),
    ("AI 워크플로우", "Claude 쓰는 방법"),
    ("AI 워크플로", "Claude 쓰는 방법"),
    ("개인 워크플로우", "내 일 처리 방법"),
    ("워크플로우", "방법"),
    ("워크플로", "방법"),
    ("AI 활용", "Claude 사용"),
    ("AI를 활용", "Claude를 사용"),
    ("AI에게", "Claude에게"),
    ("바쁜 일상 속에서도", "하루가 정신없어도"),
    ("한 차원 높은", "더 좋은"),
    ("한 단계 높은", "더 좋은"),
    ("한 차원", "한 단계"),
    ("고민이 있으신가요", "고민이라면"),
    ("주목할 점", "이 부분"),
    ("쉽고 빠르게", "쉽게"),
    ("효과적인", "통하는"),
    ("효과적", "통하는"),
    # 단어
    ("솔루션", "방법"),
    ("프로세스", "순서"),
    ("효율적인", "빠른"),
    ("효율적", "빠른"),
    ("체계적인", "정리된"),
    ("체계적", "정해진"),
    ("최적화", "정리"),
    ("핵심 일", "진짜 일"),
    ("핵심에", "진짜에"),
    ("핵심 업무", "진짜 일"),
    ("핵심 개념", "중요 개념"),
    ("핵심을", "중요한 것을"),
    ("전략적", "맞춰"),
    ("전략", "방법"),
    ("혁신적인", "다른"),
    ("혁신", "변화"),
    ("극대화", "최대한 키우기"),
    ("최대화", "최대한"),
    ("고도화", "다듬기"),
    ("역량", "실력"),
    ("잠재력", "가능성"),
    ("경쟁력", "차별점"),
    ("시너지", "효과"),
    ("패러다임", "방식"),
    ("퀀텀점프", "큰 도약"),
    ("여러분", "회원님"),
    ("손쉽게", "쉽게"),
    ("간편하게", "간단히"),
    ("완벽한", "깔끔한"),
    ("획기적인", "확실히 다른"),
    ("획기적", "확실히 다른"),
    ("단숨에", "한 번에"),
    # '핵심'·'활용'은 마지막에 (포괄적)
    ("핵심", "중요한"),
    ("활용해", "써서"),
    ("활용한", "사용한"),
    ("활용하", "사용하"),
    ("활용", "사용"),
    # 산출물·딱딱한 학술어
    ("실습 산출물", "직접 만들 결과물"),
    ("최종 산출물", "최종 결과물"),
    ("산출물", "결과물"),
]


def transform_text(text: str) -> tuple[str, Counter]:
    """치환 적용 + 어떤 룰이 몇 번 적용됐는지 카운트."""
    counter = Counter()
    for old, new in RULES:
        if old in text:
            cnt = text.count(old)
            counter[old] = cnt
            text = text.replace(old, new)
    return text, counter


def transform_obj(obj):
    """dict/list/str 재귀적으로 치환."""
    counter = Counter()
    if isinstance(obj, str):
        new, c = transform_text(obj)
        counter.update(c)
        return new, counter
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            nv, c = transform_obj(v)
            out[k] = nv
            counter.update(c)
        return out, counter
    if isinstance(obj, list):
        out = []
        for x in obj:
            nx, c = transform_obj(x)
            out.append(nx)
            counter.update(c)
        return out, counter
    return obj, counter


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="실제 파일 변경 (없으면 dry-run)")
    ap.add_argument("--kinds", default="landing_copy,curriculum_outline,lecture_script,faq", help="처리할 kind 콤마")
    args = ap.parse_args()

    target_kinds = set(args.kinds.split(","))
    approved = REPO / "content" / "approved"
    files = sorted(approved.glob("*.json"))

    total_counter = Counter()
    files_changed = 0
    for f in files:
        try:
            d = json.load(open(f))
        except Exception:
            continue
        if d.get("kind") not in target_kinds:
            continue
        new_obj, counter = transform_obj(d)
        if not counter:
            continue
        files_changed += 1
        total_counter.update(counter)
        if args.apply:
            f.write_text(json.dumps(new_obj, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"=== 처리 결과 {'(APPLIED)' if args.apply else '(DRY-RUN)'} ===")
    print(f"  대상 파일: {files_changed} 개 변경")
    print(f"  치환 횟수: {sum(total_counter.values()):,}")
    print()
    print("=== 룰별 적용 횟수 (높은 순) ===")
    for word, cnt in total_counter.most_common(30):
        print(f"  {cnt:5}회  '{word}'")
    if not args.apply:
        print()
        print("→ --apply 플래그로 실제 적용")


if __name__ == "__main__":
    main()
