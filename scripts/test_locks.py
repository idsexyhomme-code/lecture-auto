"""Step P3 locks 검증.

3가지 시나리오:
1. 단일 프로세스 — 락 획득·해제
2. 같은 락 두 컨텍스트 — timeout 검증 (예외 발생)
3. 두 프로세스 동시 — 한 쪽이 대기·순차 실행

사용: python scripts/test_locks.py
"""
from __future__ import annotations
import sys, time, logging
from pathlib import Path
from multiprocessing import Process, Queue, get_context

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

logging.basicConfig(level="INFO", format="%(asctime)s [%(name)s] %(message)s")

from agents.locks import (
    file_lock, git_lock, tistory_lock, telegram_lock, site_config_lock,
    lock_holder, is_locked, LOCKS_DIR,
)


def worker_holds_then_releases(name: str, hold_seconds: float, q: Queue):
    """spawn 워커: 락 잡고 N초 보유 후 해제."""
    # spawn은 import 다시 함
    import sys, time
    from pathlib import Path as _P
    _ROOT = _P(__file__).resolve().parent.parent
    sys.path.insert(0, str(_ROOT))
    from agents.locks import file_lock
    t0 = time.time()
    with file_lock(name, timeout=5.0):
        q.put(("acquired", time.time() - t0))
        time.sleep(hold_seconds)
        q.put(("released", time.time() - t0))


def worker_tries_acquire(name: str, timeout: float, q: Queue):
    """spawn 워커: 락 획득 시도 (timeout 안에 잡으면 OK, 못 잡으면 TimeoutError)."""
    import sys, time
    from pathlib import Path as _P
    _ROOT = _P(__file__).resolve().parent.parent
    sys.path.insert(0, str(_ROOT))
    from agents.locks import file_lock
    t0 = time.time()
    try:
        with file_lock(name, timeout=timeout):
            q.put(("acquired", time.time() - t0))
    except TimeoutError as e:
        q.put(("timeout", time.time() - t0, str(e)))


def main():
    print("=== Step P3 locks 검증 ===")
    print(f"locks_dir: {LOCKS_DIR.relative_to(ROOT)}")
    print()

    # 1. 단일 프로세스 락
    with file_lock("test_p3_solo", timeout=2.0):
        assert is_locked("test_p3_solo")
        holder = lock_holder("test_p3_solo")
        assert holder and f"pid={__import__('os').getpid()}" in holder
        print(f"✓ 단일 프로세스: holder={holder}")
    # 해제 후
    assert not is_locked("test_p3_solo")
    print("✓ 해제 확인")

    # 2. 명명 락 편의 함수 — 빠른 획득·해제
    for name, fn in [("git", git_lock), ("tistory", tistory_lock),
                     ("telegram", telegram_lock), ("site_config", site_config_lock)]:
        with fn(timeout=2.0):
            pass
    print("✓ 명명 락 4개 (git/tistory/telegram/site_config) 모두 동작")

    # 3. 두 프로세스 동시 — 한 쪽 1초 보유, 다른 쪽 대기 후 획득
    ctx = get_context("spawn")
    q1, q2 = ctx.Queue(), ctx.Queue()
    p1 = ctx.Process(target=worker_holds_then_releases, args=("test_p3_race", 1.0, q1))
    p2 = ctx.Process(target=worker_tries_acquire, args=("test_p3_race", 5.0, q2))

    print("\n  scenario: p1이 1초 잡음, p2가 5초 timeout으로 시도")
    p1.start()
    time.sleep(0.2)  # p1이 먼저 락 잡도록
    p2.start()

    p1.join(timeout=10)
    p2.join(timeout=10)

    # 결과 수집
    msgs_1 = []
    while not q1.empty():
        msgs_1.append(q1.get())
    msgs_2 = []
    while not q2.empty():
        msgs_2.append(q2.get())

    print(f"  p1: {msgs_1}")
    print(f"  p2: {msgs_2}")

    assert any(m[0] == "acquired" for m in msgs_1), "p1 락 획득 실패"
    assert any(m[0] == "released" for m in msgs_1), "p1 락 해제 실패"
    # p2는 p1 해제 후 락 획득 (acquired). 대기 시간이 0.5초 이상이어야 함
    p2_acquired = next((m for m in msgs_2 if m[0] == "acquired"), None)
    assert p2_acquired is not None, "p2 락 획득 실패"
    # p1 해제 시점이 약 1.0초 후. p2는 0.2초 start + ~0.8초 대기 = 약 0.8~1.0초.
    wait_time = p2_acquired[1]
    assert wait_time >= 0.5, f"p2 대기 시간 너무 짧음: {wait_time}s (락이 직렬 안 됐을 가능성)"
    print(f"✓ 두 프로세스 직렬 실행: p2가 {wait_time:.2f}초 대기 후 획득")

    # 4. timeout 시나리오 — p1이 3초 잡음, p2가 1초 timeout
    q1, q2 = ctx.Queue(), ctx.Queue()
    p1 = ctx.Process(target=worker_holds_then_releases, args=("test_p3_timeout", 3.0, q1))
    p2 = ctx.Process(target=worker_tries_acquire, args=("test_p3_timeout", 1.0, q2))

    print("\n  scenario: p1이 3초 잡음, p2가 1초 timeout (실패 예상)")
    p1.start()
    time.sleep(0.2)
    p2.start()

    p1.join(timeout=10)
    p2.join(timeout=10)

    msgs_2 = []
    while not q2.empty():
        msgs_2.append(q2.get())
    print(f"  p2: {msgs_2}")
    assert any(m[0] == "timeout" for m in msgs_2), f"p2 timeout 안 발생: {msgs_2}"
    print("✓ timeout 정상 발생 (TimeoutError)")

    # 정리
    for n in ["test_p3_solo", "test_p3_race", "test_p3_timeout"]:
        f = LOCKS_DIR / f"{n}.lock"
        try:
            f.unlink()
        except (FileNotFoundError, PermissionError):
            pass

    print()
    print("=== 검증 통과 ===")
    print("✓ 단일 프로세스 락")
    print("✓ 명명 락 4개 (git / tistory / telegram / site_config)")
    print("✓ 두 프로세스 직렬 실행 (multiprocess safe)")
    print("✓ timeout 발동")


if __name__ == "__main__":
    main()
