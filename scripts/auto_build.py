"""Auto-build hook — site_config_change·landing_copy·curriculum_outline 승인 직후
site_builder/build.py를 즉시 실행하고, 결과를 텔레그램으로 보고.

설계:
- 산출물 승인 → site_config.json 또는 코스 페이지 갱신 → 빌드 → 다음 long_poll 사이클에서 자동 git push
- 빌드 결과를 텔레그램에 카드로 전송 (성공/실패 + 변경 파일 수 + 빌드 시간)
- 실패 시 회원에게 즉시 알림 → 데몬 재시작 등 조치 가능

호출 지점: telegram_bot/poll.py의 callback handler (approve action) 직후
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BUILD_SCRIPT = REPO_ROOT / "site_builder" / "build.py"
SITE_DIR = REPO_ROOT / "site"
STATE_DIR = REPO_ROOT / "content" / "state"
LAST_BUILD_LOG = STATE_DIR / "last_build.json"

log = logging.getLogger("auto_build")

# 빌드 트리거 대상 kind
BUILD_TRIGGER_KINDS = {
    "site_config_change",  # 메타데이터 직접 변경
    "landing_copy",         # 코스 랜딩 카피 갱신
    "curriculum_outline",   # 커리큘럼 변경 → 코스 페이지 영향
    "lecture_script",       # 차시 영상 스크립트 → posts 페이지
    "design_variants",      # 디자인 시스템 변경
}

# 빌드 후 스크린샷·Lighthouse를 자동 발송할 kind (시각적 영향 큰 것만)
SNAPSHOT_TRIGGER_KINDS = {
    "site_config_change",
    "design_variants",
}


def should_trigger_build(kind: str) -> bool:
    """이 kind가 빌드를 트리거해야 하는지."""
    return kind in BUILD_TRIGGER_KINDS


def should_trigger_snapshot(kind: str) -> bool:
    """이 kind가 빌드 후 스냅샷 발송까지 가야 하는지 (시각 영향 큰 것만)."""
    return kind in SNAPSHOT_TRIGGER_KINDS


def trigger_snapshot_async(kind: str, title: str) -> bool:
    """빌드 직후 사이트 스냅샷 + Lighthouse를 백그라운드로 발송.

    Returns: 시도 성공 여부 (실제 캡처는 비동기로 진행 가능).
    """
    try:
        from scripts.site_snapshot import capture_and_report
        # 로컬 빌드 결과를 즉시 캡처 (라이브 URL은 git push 후 1~3분 지나야 반영)
        capture_and_report(
            trigger_label=f"{kind} — {title[:50]}",
            use_live=False,
            mobile_too=False,
        )
        return True
    except Exception as e:
        log.warning("[snapshot] trigger failed: %s", e)
        return False


def run_build(timeout: int = 120) -> dict:
    """site_builder/build.py 즉시 실행.

    Returns:
        {
            "ok": bool,
            "duration_sec": float,
            "stdout_tail": str (마지막 500자),
            "stderr_tail": str,
            "files_changed": int (site/ 안 변경된 파일 수),
            "error": str | None,
        }
    """
    if not BUILD_SCRIPT.exists():
        return {
            "ok": False,
            "duration_sec": 0.0,
            "stdout_tail": "",
            "stderr_tail": "",
            "files_changed": 0,
            "error": f"build.py not found at {BUILD_SCRIPT}",
        }

    # 빌드 전 site/ 파일 mtime 스냅샷
    before_mtimes = _snapshot_site_mtimes()
    start = time.time()

    try:
        # .venv가 있으면 그쪽 python 사용
        py = _resolve_python()
        env = os.environ.copy()
        # GITHUB_REPOSITORY가 .env에서 로드 안 됐을 가능성 대비
        if "GITHUB_REPOSITORY" not in env:
            env["GITHUB_REPOSITORY"] = "idsexyhomme-code/lecture-auto"

        proc = subprocess.run(
            [py, str(BUILD_SCRIPT)],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        duration = time.time() - start
        files_changed = _count_changed_since(before_mtimes)

        result = {
            "ok": proc.returncode == 0,
            "duration_sec": round(duration, 2),
            "stdout_tail": (proc.stdout or "")[-500:],
            "stderr_tail": (proc.stderr or "")[-500:],
            "files_changed": files_changed,
            "error": None if proc.returncode == 0 else f"exit {proc.returncode}",
        }
    except subprocess.TimeoutExpired:
        result = {
            "ok": False,
            "duration_sec": float(timeout),
            "stdout_tail": "",
            "stderr_tail": "",
            "files_changed": 0,
            "error": f"timeout after {timeout}s",
        }
    except Exception as e:
        result = {
            "ok": False,
            "duration_sec": time.time() - start,
            "stdout_tail": "",
            "stderr_tail": "",
            "files_changed": 0,
            "error": f"exception: {type(e).__name__}: {e}",
        }

    # 상태 기록 (대시보드·CEO 일일 보고에서 활용)
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        LAST_BUILD_LOG.write_text(
            json.dumps({**result, "ts": time.time()}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception:
        pass

    return result


def format_telegram_card(result: dict, trigger_kind: str, trigger_title: str) -> str:
    """텔레그램 빌드 결과 카드."""
    if result.get("ok"):
        emoji = "🛠"
        head = "*빌드 성공* — 사이트에 반영됨"
        body = (
            f"⏱ {result.get('duration_sec', 0):.1f}초\n"
            f"📂 변경 파일: *{result.get('files_changed', 0)}개*\n"
            f"🔗 다음 git push 사이클(~3분)에 GitHub Pages 자동 배포"
        )
    else:
        emoji = "❌"
        head = "*빌드 실패* — 사이트 미반영"
        body = (
            f"오류: `{result.get('error', 'unknown')}`\n"
            f"⏱ {result.get('duration_sec', 0):.1f}초\n\n"
            f"stderr 마지막 줄:\n```\n{(result.get('stderr_tail') or '')[-300:]}\n```"
        )

    return (
        f"{emoji} {head}\n\n"
        f"트리거: `{trigger_kind}` — {trigger_title[:60]}\n\n"
        f"{body}"
    )


def _resolve_python() -> str:
    """프로젝트 venv가 있으면 그 python, 없으면 sys.executable."""
    venv_py = REPO_ROOT / ".venv" / "bin" / "python3"
    if venv_py.exists():
        return str(venv_py)
    venv_py2 = REPO_ROOT / ".venv" / "bin" / "python"
    if venv_py2.exists():
        return str(venv_py2)
    return sys.executable or "python3"


def _snapshot_site_mtimes() -> dict[str, float]:
    """site/ 폴더의 파일별 mtime 스냅샷."""
    out: dict[str, float] = {}
    if not SITE_DIR.exists():
        return out
    for p in SITE_DIR.rglob("*"):
        if p.is_file():
            try:
                out[str(p)] = p.stat().st_mtime
            except OSError:
                continue
    return out


def _count_changed_since(before: dict[str, float]) -> int:
    """스냅샷 이후 mtime 변경된 site/ 파일 수."""
    if not SITE_DIR.exists():
        return 0
    count = 0
    for p in SITE_DIR.rglob("*"):
        if not p.is_file():
            continue
        try:
            mt = p.stat().st_mtime
        except OSError:
            continue
        prev = before.get(str(p))
        if prev is None or mt > prev + 0.001:
            count += 1
    return count


def main():
    """CLI: python3 scripts/auto_build.py — 수동 빌드 + 결과 출력."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")
    print("════════════════════════════════════════════════════════════")
    print("  🛠  Auto-build — site_builder/build.py 직접 실행")
    print("════════════════════════════════════════════════════════════")
    print()
    result = run_build()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print()
    if result.get("ok"):
        print("✓ 빌드 성공 — site/ 폴더 갱신됨")
        print(f"  변경 파일: {result.get('files_changed', 0)}개")
        return 0
    else:
        print(f"❌ 빌드 실패: {result.get('error')}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
