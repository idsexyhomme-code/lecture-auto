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
LONG_POLL_TIMEOUT = 30      # getUpdates timeout (초)
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


def _git_sync_changes() -> bool:
    """변경 사항이 있으면 commit + push. 성공 여부 반환."""
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

    # pull --rebase로 충돌 방지 (agent-bot이 자동 push했을 수 있음)
    _git("pull", "--rebase")

    # push
    rc, out = _git("push")
    if rc != 0:
        log.warning("git push 실패: %s", out[:200])
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

    while not _should_stop:
        try:
            offset = _load_offset()
            next_offset = offset + 1 if offset is not None else None

            updates = tg.get_updates(offset=next_offset, timeout=LONG_POLL_TIMEOUT)

            if not updates:
                # timeout 도달했는데 update 없음 — 정상. 다음 루프.
                continue

            log.info("📨 %d개 update 수신", len(updates))

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

            # 빌드 트리거 정책 (즉각 반응 위해 광범위하게)
            #   1. 새 brief 생성 → 무조건 트리거 (다음 작업 즉시 시작)
            #   2. callback이 있었고 git push가 있었다 → 트리거
            #      (승인·반영 결과 즉시 빌드)
            should_trigger = had_brief_creation or (had_callback and pushed)
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
