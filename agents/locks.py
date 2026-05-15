"""Cross-process file lock — multiprocess·multi-worker 안전.

POSIX fcntl.flock 기반. Linux·macOS 표준 (Windows X — Mac mini 사용이라 OK).

회원 결정 (P3 도입): 병렬 처리 시 *공유 자원 충돌 방지*가 핵심.

[락 대상 4개]
- git_lock         : git pull/commit/push 직렬화. 동시 push 충돌 방지.
- tistory_lock     : Tistory 발행 (Playwright 브라우저 세션 1개). 동시 발행 금지.
- telegram_lock    : Telegram API rate limit (초당 30개 메시지 한도) 보호.
- site_config_lock : site_config.json read-modify-write race 방지.

[사용 예]
    from agents.locks import git_lock, tistory_lock, telegram_lock, site_config_lock

    # git push 동안 다른 프로세스 push 차단
    with git_lock():
        subprocess.run(["git", "push"])

    # Tistory 발행은 한 번에 하나만 — 다른 워커는 대기
    with tistory_lock():
        publish_to_tistory(...)

    # site_config 수정은 read-modify-write 패턴이라 락 필수
    with site_config_lock():
        cfg = json.load(open("site_config.json"))
        cfg["foo"] = "bar"
        json.dump(cfg, open("site_config.json", "w"))

[안전 보장]
- fcntl.LOCK_EX (exclusive) — 동시 1개 프로세스만 진입
- LOCK_NB + sleep polling — 진짜 데드락 방지 (timeout)
- finally 블록 — 예외·에러 시에도 락 해제 보장
- 락 파일에 PID/timestamp 기록 — 디버깅용

[CEO 헌법 §6 영향 X]
회원 승인 게이트와 무관. 회원 ✅ 결정 권한은 그대로.
"""
from __future__ import annotations

import contextlib
import fcntl
import logging
import os
import time
from pathlib import Path

from .base import REPO_ROOT

log = logging.getLogger("locks")

LOCKS_DIR = REPO_ROOT / "content" / "state" / "locks"
LOCKS_DIR.mkdir(parents=True, exist_ok=True)


@contextlib.contextmanager
def file_lock(name: str, timeout: float = 60.0, poll_interval: float = 0.1):
    """POSIX 파일 락 컨텍스트 매니저.

    Args:
        name: 락 식별자 (파일명: content/state/locks/{name}.lock)
        timeout: 락 획득 대기 최대 초 (기본 60)
        poll_interval: 대기 중 poll 간격 (기본 0.1초)

    Raises:
        TimeoutError: timeout 초 안에 락 획득 못 함

    Note:
        같은 프로세스 안에서 *동일 이름 락 중첩*은 데드락 위험.
        다른 이름이면 안전.
    """
    lock_path = LOCKS_DIR / f"{name}.lock"
    fd = os.open(str(lock_path), os.O_RDWR | os.O_CREAT, 0o644)
    start = time.time()
    acquired = False

    try:
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                acquired = True
                # PID·timestamp 기록 (디버깅)
                try:
                    os.lseek(fd, 0, 0)
                    os.ftruncate(fd, 0)
                    info = f"pid={os.getpid()} acquired_at={time.time():.3f}\n"
                    os.write(fd, info.encode("utf-8"))
                except Exception:
                    pass  # 기록 실패해도 락은 잡힘
                log.debug("[lock] acquired '%s' (waited %.3fs)", name, time.time() - start)
                break
            except BlockingIOError:
                elapsed = time.time() - start
                if elapsed > timeout:
                    # 누가 락 잡고 있는지 확인 시도
                    try:
                        os.lseek(fd, 0, 0)
                        holder = os.read(fd, 256).decode("utf-8", errors="ignore").strip()
                    except Exception:
                        holder = "(unknown)"
                    raise TimeoutError(
                        f"file_lock '{name}' timeout after {timeout}s. Holder: {holder}"
                    )
                time.sleep(poll_interval)

        yield  # 락 보유 상태에서 사용자 코드 실행

    finally:
        if acquired:
            try:
                fcntl.flock(fd, fcntl.LOCK_UN)
                log.debug("[lock] released '%s'", name)
            except Exception as e:
                log.warning("[lock] release failed for '%s': %s", name, e)
        try:
            os.close(fd)
        except Exception:
            pass


# ── 명명 락 편의 함수 (timeout 조정) ─────────────────────────────

def git_lock(timeout: float = 60.0):
    """git pull/commit/push 동안 다른 프로세스의 git 작업 차단."""
    return file_lock("git", timeout=timeout)


def tistory_lock(timeout: float = 600.0):
    """Tistory 발행 (브라우저 세션 1개). 발행은 1~3분 걸리므로 timeout 길게."""
    return file_lock("tistory", timeout=timeout)


def telegram_lock(timeout: float = 30.0):
    """Telegram 카드 발송 rate limit 보호. 카드 발송은 <1초."""
    return file_lock("telegram", timeout=timeout)


def site_config_lock(timeout: float = 10.0):
    """site_config.json read-modify-write race 방지. read+write 합쳐 <1초."""
    return file_lock("site_config", timeout=timeout)


# ── 헬퍼: 누가 락 잡고 있는지 확인 ──────────────────────────────

def lock_holder(name: str) -> str | None:
    """락 파일을 *읽기 전용*으로 열어 holder 정보 반환. 락 안 잡음.

    Returns:
        "pid=12345 acquired_at=1234567890.123" 또는 None
    """
    lock_path = LOCKS_DIR / f"{name}.lock"
    if not lock_path.exists():
        return None
    try:
        info = lock_path.read_text(encoding="utf-8").strip()
        return info or None
    except Exception:
        return None


def is_locked(name: str) -> bool:
    """락이 현재 누군가에게 잡혀있는지 non-blocking 확인.

    Returns:
        True if 다른 프로세스가 락 보유 중
    """
    lock_path = LOCKS_DIR / f"{name}.lock"
    fd = os.open(str(lock_path), os.O_RDWR | os.O_CREAT, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        # 잡혔으니까 곧바로 풀고 False 반환
        fcntl.flock(fd, fcntl.LOCK_UN)
        return False
    except BlockingIOError:
        return True
    finally:
        try:
            os.close(fd)
        except Exception:
            pass
