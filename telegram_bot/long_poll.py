"""맥미니 long-polling 데몬.

회원님 맥미니에서 24시간 떠있으면서 텔레그램 메시지·콜백을 *즉시* 처리한다.
GitHub Actions cron(5분 백업)과 듀얼 구조 — 둘 다 같은 telegram offset을 사용해
중복 처리는 거의 발생하지 않는다.

흐름:
  1. while True:
  2.   updates = get_updates(offset, timeout=30)   # long polling
  3.   for u in updates:
  4.     handle_message 또는 handle_callback (poll.py 함수 재사용)
  5.   변경 사항 있으면 git commit + push
  6.   새 brief이 생겼으면 workflow_dispatch (GitHub Actions가 빌드·배포)

실행: 회원님 맥미니에서
  cd ~/Desktop/"강의 홈페이지 제작"
  source .venv/bin/activate           # 처음만 만들기
  pip install -r requirements.txt
  cp .env.example .env                # 키 채우기
  python -m telegram_bot.long_poll

종료: Ctrl+C (graceful)
"""
from __future__ import annotations

import json
import logging
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

# repo root 추가
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from telegram_bot import client as tg
from telegram_bot import poll
from agents.base import REPO_ROOT, STATE_DIR

# .env 자동 로드 (있을 때만)
try:
    from dotenv import load_dotenv
    load_dotenv(REPO_ROOT / ".env")
except ImportError:
    pass

OFFSET_FILE = STATE_DIR / "telegram_offset.json"
LONG_POLL_TIMEOUT = 5       # getUpdates timeout (초) — 짧게 잡아 brief 빠르게 점검
RETRY_BACKOFF_BASE = 5      # 네트워크 오류 시 backoff 초기값
GIT_COMMIT_AUTHOR_NAME = "long-poll-bot"
GIT_COMMIT_AUTHOR_EMAIL = "long-poll@local"

log = logging.getLogger("long_poll")
_should_stop = False


def _signal_handler(signum, frame):
    global _should_stop
    log.info("종료 신호 수신 (signal=%d) — 다음 루프에서 정리합니다", signum)
    _should_stop = True


def _load_offset() -> int | None:
    if not OFFSET_FILE.exists():
        return None
    try:
        return int(json.loads(OFFSET_FILE.read_text(encoding="utf-8")).get("offset", 0)) or None
    except Exception:
        return None


def _save_offset(offset: int):
    OFFSET_FILE.parent.mkdir(parents=True, exist_ok=True)
    OFFSET_FILE.write_text(
        json.dumps({"offset": offset}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _git(*args: str) -> tuple[int, str]:
    """git 명령 실행. (returncode, output)."""
    try:
        r = subprocess.run(
            ["git", *args],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=30,
        )
        return r.returncode, (r.stdout + r.stderr).strip()
    except Exception as e:
        return -1, str(e)


def _ensure_on_main() -> bool:
    """detached HEAD 상태이면 main 브랜치로 자동 복구.

    rebase가 충돌나거나 force-with-lease 경합으로 detached HEAD에 빠지는 경우 자동 정상화.
    """
    rc, out = _git("symbolic-ref", "--short", "HEAD")
    if rc == 0 and out.strip() == "main":
        return True
    log.warning("[git] detached HEAD 감지 — main으로 복구 시도")
    # rebase 진행 중이면 abort
    _git("rebase", "--abort")
    _git("merge", "--abort")
    # 현재 commit hash 저장
    rc, current_sha = _git("rev-parse", "HEAD")
    # main으로 강제 이동 + 커밋 데이터 보존 (cherry-pick 등은 push에서 처리)
    _git("checkout", "-B", "main")
    log.info("[git] main 브랜치로 복구 완료 (was %s)", current_sha[:8] if current_sha else "?")
    return True


def _git_sync_changes() -> bool:
    """변경 사항이 있으면 commit + push. 성공 여부 반환."""
    # ★ detached HEAD 자동 복구
    _ensure_on_main()

    # 현재 변경 사항 확인
    rc, out = _git("status", "--porcelain")
    if rc != 0 or not out.strip():
        return False  # 변경 없음

    # add
    _git("add", "-A")

    # commit (skip ci로 push trigger 방지 — workflow_dispatch만 사용)
    msg = f"long-poll: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} [skip ci]"
    rc, out = _git(
        "-c", f"user.name={GIT_COMMIT_AUTHOR_NAME}",
        "-c", f"user.email={GIT_COMMIT_AUTHOR_EMAIL}",
        "commit", "-m", msg,
    )
    if rc != 0:
        log.warning("git commit 실패: %s", out[:200])
        return False

    # pull --rebase로 충돌 방지 — 충돌 시 ours 전략 (데몬은 자기 변경을 우선)
    rc_pull, _ = _git("pull", "--rebase", "-X", "ours", "origin", "main")
    if rc_pull != 0:
        log.warning("[git] pull 실패 — rebase 정리 후 재시도")
        _git("rebase", "--abort")
        _ensure_on_main()

    # push — HEAD를 명시적으로 origin/main으로 (detached 상태도 안전)
    rc, out = _git("push", "origin", "HEAD:main")
    if rc != 0:
        log.warning("git push 실패: %s — main 강제 복구 후 재시도", out[:200])
        _ensure_on_main()
        rc, out = _git("push", "origin", "HEAD:main")
        if rc != 0:
            log.error("git push 재시도 실패: %s", out[:200])
            return False

    log.info("✓ 변경 사항 push 완료")
    return True


def _has_new_brief_in_dir() -> bool:
    """briefs/ 폴더에 새 .json 파일이 있으면 True (workflow_dispatch 필요 신호)."""
    briefs_dir = REPO_ROOT / "briefs"
    if not briefs_dir.exists():
        return False
    for p in briefs_dir.glob("*.json"):
        return True
    return False


def _run_local_pipeline():
    """로컬에서 conductor → notify → build 풀 파이프라인 실행.

    cron이 작동 안 해도 데몬이 24시간 돌면 이 함수가 모든 brief을 처리한다.
    각 단계 실패해도 다음 단계는 계속 시도.
    """
    # ★ Roadmap 자동 펌프 — N시간마다 신규 코스 brief 자동 발주
    # should_pump_now() 내부에서 interval(6h) + 일일 한도 체크하므로 매 사이클 호출 무해
    try:
        from agents.roadmap_pump import pump_next
        new_brief = pump_next()
        if new_brief:
            log.info("[long_poll] 🚀 roadmap 자동 펌프 — 새 코스 brief: %s", new_brief.name)
    except Exception as e:
        log.warning("[long_poll] roadmap_pump 실패 (무해): %s", e)

    briefs_dir = REPO_ROOT / "briefs"
    pending_dir = REPO_ROOT / "content" / "pending"

    queued_briefs = list(briefs_dir.glob("*.json")) if briefs_dir.exists() else []
    pending_results = list(pending_dir.glob("*.json")) if pending_dir.exists() else []

    # 할 일이 없으면 빠르게 종료
    if not queued_briefs and not pending_results:
        return

    log.info("[local-pipeline] briefs=%d pending=%d", len(queued_briefs), len(pending_results))

    # venv의 python 사용 (subprocess가 시스템 python을 잡으면 의존성 안 맞음)
    venv_python = REPO_ROOT / ".venv" / "bin" / "python"
    if venv_python.exists():
        py = str(venv_python)
    else:
        py = sys.executable

    def _run_module(module: str, timeout: int = 600):
        try:
            r = subprocess.run(
                [py, "-m", module],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                timeout=timeout,
                env={**os.environ},  # API 키·설정 모두 전달
            )
            if r.returncode == 0:
                log.info("[local-pipeline] ✓ %s", module)
                if r.stdout.strip():
                    for line in r.stdout.strip().split("\n")[-3:]:
                        log.info("    %s", line)
            else:
                log.warning("[local-pipeline] ✗ %s (rc=%d)", module, r.returncode)
                err = (r.stderr or r.stdout or "").strip().split("\n")[-3:]
                for line in err:
                    log.warning("    %s", line)
        except Exception as e:
            log.exception("[local-pipeline] %s 예외: %s", module, e)

    # 1) Conductor — briefs/ 처리 → pending/ 생성
    if queued_briefs:
        _run_module("agents.conductor")

    # 2) Notify — pending/ 항목 발송 (AUTO 모드면 자동 승인 + 캐스케이드)
    _run_module("telegram_bot.notify", timeout=180)

    # 3) Build — site/ 재생성
    _run_module("site_builder.build", timeout=180)


def _trigger_build():
    """새 brief이 생겼으면 GitHub Actions를 dispatch로 깨움."""
    ok = poll._dispatch_agent_loop()
    if ok:
        log.info("⚡ workflow_dispatch 트리거 — GitHub Actions가 빌드합니다")
    else:
        log.info("workflow_dispatch 실패 또는 GH_PAT 없음 — cron 대기")


def run_loop():
    """메인 루프. 종료 신호 받을 때까지 무한 반복."""
    log.info("=" * 60)
    log.info("코어 캠퍼스 — long-poll 데몬 시작")
    log.info("repo: %s", REPO_ROOT)
    log.info("Ctrl+C로 종료")
    log.info("=" * 60)

    backoff = RETRY_BACKOFF_BASE
    last_pipeline_check = 0
    PIPELINE_INTERVAL = 5   # 5초마다 큐 점검 — 새 brief 즉시 잡음

    while not _should_stop:
        try:
            offset = _load_offset()
            next_offset = offset + 1 if offset is not None else None

            updates = tg.get_updates(offset=next_offset, timeout=LONG_POLL_TIMEOUT)

            # ★ 메시지 없어도 60초마다 큐 점검 (24/7 자동화 핵심)
            now = time.time()
            if not updates:
                if now - last_pipeline_check >= PIPELINE_INTERVAL:
                    last_pipeline_check = now
                    try:
                        # origin pull (다른 사이트에서 새 brief 가져왔을 수 있음)
                        rc, out = _git("pull", "--ff-only", "origin", "main")
                        if rc == 0 and out.strip() and "Already up to date" not in out:
                            log.info("✓ origin pull (정기 동기화)")
                    except Exception as e:
                        log.warning("정기 pull 실패: %s", e)

                    try:
                        _run_local_pipeline()
                    except Exception as e:
                        log.exception("정기 파이프라인 에러: %s", e)

                    pushed = _git_sync_changes()
                    if pushed:
                        _trigger_build()
                continue

            log.info("📨 %d개 update 수신", len(updates))
            last_pipeline_check = now  # 메시지 처리도 파이프라인 활동으로 카운트

            # ★ Phase A4 — callback 처리 *전* origin에서 fast-forward pull.
            # 클라우드(GitHub Actions)에서 만든 새 pending 파일이 로컬에 없으면
            # design-pick 같은 콜백이 _find_pending에서 무반응으로 끝난다.
            # ff-only면 충돌 없을 때만 pull, 안전.
            try:
                rc, out = _git("pull", "--ff-only", "origin", "main")
                if rc == 0 and out.strip() and "Already up to date" not in out:
                    log.info("✓ origin pull 적용 (사전 동기화)")
            except Exception as e:
                log.warning("pre-callback pull 실패 (무시): %s", e)

            last_id = offset or 0
            had_callback = False
            had_brief_creation = False

            for u in updates:
                last_id = max(last_id, u["update_id"])
                try:
                    if "callback_query" in u:
                        had_callback = True
                        # callback에서 brief이 생성될 수 있음 (intake-approve)
                        before = _list_briefs()
                        poll.handle_callback(u["callback_query"])
                        after = _list_briefs()
                        if len(after) > len(before):
                            had_brief_creation = True
                    elif "message" in u:
                        poll.handle_message(u["message"])
                except Exception as e:
                    log.exception("update %s 처리 실패: %s", u.get("update_id"), e)

            _save_offset(last_id)

            # 변경 사항 있으면 git push
            pushed = _git_sync_changes()

            # ★ 로컬 파이프라인 실행 — cron 의존성 제거.
            # briefs/에 파일 있거나 pending/에 미발송이 있으면 로컬에서 처리.
            # 클라우드 워크플로우가 어떤 이유로 안 돌아도 이 데몬이 일을 끝까지 한다.
            try:
                _run_local_pipeline()
            except Exception as e:
                log.exception("로컬 파이프라인 에러 (무시하고 계속): %s", e)

            # 로컬 파이프라인이 만든 변경 다시 push
            pushed_after = _git_sync_changes()

            # 빌드 트리거 (Pages 배포)
            should_trigger = (
                had_brief_creation
                or (had_callback and pushed)
                or pushed_after
            )
            if should_trigger:
                _trigger_build()

            backoff = RETRY_BACKOFF_BASE  # 정상 한 사이클 — backoff 리셋

        except KeyboardInterrupt:
            log.info("KeyboardInterrupt — 종료")
            break
        except Exception as e:
            log.exception("루프 에러: %s — %d초 후 재시도", e, backoff)
            time.sleep(backoff)
            backoff = min(backoff * 2, 120)  # 최대 2분

    log.info("=" * 60)
    log.info("long-poll 데몬 정상 종료")
    log.info("=" * 60)


def _list_briefs() -> list[Path]:
    p = REPO_ROOT / "briefs"
    if not p.exists():
        return []
    return list(p.glob("*.json"))


if __name__ == "__main__":
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s [%(name)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)
    run_loop()
