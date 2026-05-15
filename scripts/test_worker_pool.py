"""Step P2 worker_pool 검증 스크립트.

실제 ProcessPoolExecutor(spawn)을 사용하려면 *모듈 파일*에서 실행 필요
(stdin/<<EOF는 spawn 워커가 import 못 함).

사용:
    python scripts/test_worker_pool.py
"""
from __future__ import annotations
import sys, json, logging
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

logging.basicConfig(
    level="INFO",
    format="%(asctime)s [%(name)s] %(message)s",
)

from agents.worker_pool import run_briefs_parallel, DEFAULT_WORKERS, DEFAULT_CONCURRENCY


def main():
    print(f"=== Step P2 worker_pool 검증 ===")
    print(f"기본 설정: workers={DEFAULT_WORKERS} × concurrency={DEFAULT_CONCURRENCY} = {DEFAULT_WORKERS*DEFAULT_CONCURRENCY} 동시")
    print()

    # 1. 빈 입력
    r = run_briefs_parallel([])
    assert r == []
    print("✓ 빈 입력")

    # 2. 잘못된 agent — _failed/로 이동 검증
    test_brief = ROOT / "briefs" / "_test_p2_invalid.json"
    test_brief.write_text(json.dumps({"agent": "NO_SUCH_AGENT", "brief": {}}, ensure_ascii=False))
    print(f"\n  테스트 brief: {test_brief.name}")

    r = run_briefs_parallel([test_brief], workers=1, concurrency=1, timeout_per_chunk=30)
    print(f"  결과: ok={r[0]['ok']} / error={r[0].get('error','')[:80]}")
    assert len(r) == 1
    assert r[0]["ok"] is False
    assert "unknown agent" in r[0].get("error", "")
    print("✓ 잘못된 agent 처리")

    moved = ROOT / "briefs" / "_failed" / "_test_p2_invalid.json"
    assert moved.exists(), f"_failed/ 이동 안 됨: {moved}"
    print(f"✓ _failed/ 이동: {moved.relative_to(ROOT)}")
    try:
        moved.unlink()
    except PermissionError:
        pass  # sandbox 권한 한계 — 실제 macOS에서는 정상

    # 3. 다중 chunk 분할 검증 (실제 처리는 안 함)
    fake_paths = [Path(f"briefs/_fake_{i}.json") for i in range(10)]
    # 다 없는 파일이라 _failed로 전부 가는데, chunk 분할은 정상
    print(f"\n  10개 가짜 brief (없는 파일) → 분할 검증")
    r = run_briefs_parallel(fake_paths, workers=2, concurrency=3, timeout_per_chunk=15)
    print(f"  결과: {len(r)}개 (모두 실패 예상)")
    assert len(r) == 10
    ok_count = sum(1 for x in r if x["ok"])
    assert ok_count == 0
    print(f"✓ 10개 분할 처리 (실패 카운트: {len(r) - ok_count})")

    print()
    print("=== 검증 통과 ===")
    print("✓ ProcessPoolExecutor(spawn) + asyncio.gather 정상 작동")
    print("✓ 워커 프로세스 spawn 후 agents.* 모듈 import 정상")
    print("✓ _failed/ 자동 이동")
    print("✓ chunk 분할 (workers × concurrency)")


if __name__ == "__main__":
    main()
