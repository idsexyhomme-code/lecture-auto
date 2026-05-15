"""병렬 처리 워커 풀 — multiprocessing 4 워커 × asyncio 4 동시 = 16 동시.

[설계 — 회원 결정 2026-05-15]
- A+B 하이브리드: ProcessPoolExecutor + 각 worker 안에서 asyncio.gather
- 맥미니 CPU 코어 활용 (눈에 보이는 자원 사용) + Anthropic IO 작업 효율 (asyncio)
- P3 락 시스템 / P4 dependency 그래프 / P5 데몬 통합과 함께 완성됨

[안전 원칙 — CEO 헌법 §6 영향 없음]
- 회원 승인 게이트는 *결과물 검토 단계*에 있고, 본 워커 풀은 *생성 단계만*
- CEO 산출물 (ceo_*) 자동 승인 X — 그대로 pending에서 회원 ✅ 대기
- site_config_change AUTO 차단 — 그대로 유지
- 본 풀은 *직렬 큐 → 병렬 실행*만. 큐 자체는 단일 데몬이 직렬 픽업해 안전.

사용 예 (P5 데몬 통합 후):
    from agents.worker_pool import run_briefs_parallel
    from pathlib import Path
    briefs = list(Path("briefs").glob("*.json"))
    results = run_briefs_parallel(briefs, workers=4, concurrency=4)
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import get_context
from pathlib import Path

# 워커 프로세스가 spawn으로 시작될 때 import 경로 보장
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

log = logging.getLogger("worker_pool")

# 기본값 — 회원 결정값. .env 또는 worker_pool 호출 시 override 가능.
DEFAULT_WORKERS = int(os.environ.get("CC_WORKER_POOL_WORKERS", "4"))
DEFAULT_CONCURRENCY = int(os.environ.get("CC_WORKER_POOL_CONCURRENCY", "4"))


# ── 워커 프로세스 안에서 실행되는 함수 ─────────────────────────
# ProcessPoolExecutor가 pickle해서 워커로 보내므로 *top-level 함수*여야 함

def _run_async_batch(brief_paths: list[str]) -> list[dict]:
    """워커 프로세스 1개에서 실행. brief_paths를 asyncio.gather로 동시 처리.

    각 worker는 자기 asyncio 이벤트 루프를 가짐. concurrency개 brief을 한 번에.

    Returns:
        list of {"path", "ok", "saved" (성공 시) | "error" (실패 시), "elapsed"}
    """
    # 워커 시작 시 import (spawn context — main의 import가 따라오지 않을 수 있음)
    from dotenv import load_dotenv
    load_dotenv(REPO_ROOT / ".env")

    from agents.base import PENDING_DIR
    from agents.conductor import AGENTS

    BRIEFS_DIR = REPO_ROOT / "briefs"
    PROCESSED_DIR = BRIEFS_DIR / "_processed"
    FAILED_DIR = BRIEFS_DIR / "_failed"

    async def _process_one(path_str: str) -> dict:
        path = Path(path_str)
        t0 = time.time()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            agent_key = data.get("agent")
            brief_data = data.get("brief") or {}

            if agent_key not in AGENTS:
                # unknown agent도 _failed/로 이동 (재시도 또는 분석 위해)
                FAILED_DIR.mkdir(parents=True, exist_ok=True)
                try:
                    path.rename(FAILED_DIR / path.name)
                except (FileNotFoundError, OSError):
                    pass
                return {
                    "path": str(path),
                    "ok": False,
                    "error": f"unknown agent: {agent_key}",
                    "elapsed": time.time() - t0,
                }

            agent = AGENTS[agent_key]()
            # arun() 사용 — BaseAgent에서 async 지원 (P1)
            # arun을 override한 에이전트면 진짜 비동기, 아니면 thread pool fallback
            results = await agent.arun(brief_data)
            saved = []
            for r in results:
                p = r.save(PENDING_DIR)
                saved.append(str(p))

            # 처리된 brief을 _processed/로 이동
            PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
            processed_path = PROCESSED_DIR / path.name
            try:
                path.rename(processed_path)
            except FileNotFoundError:
                pass  # 다른 worker가 이미 처리했을 수도 (race) — 무해

            return {
                "path": str(path),
                "ok": True,
                "agent": agent_key,
                "saved": saved,
                "elapsed": time.time() - t0,
            }
        except Exception as e:
            # 실패한 brief은 _failed/로
            FAILED_DIR.mkdir(parents=True, exist_ok=True)
            try:
                path.rename(FAILED_DIR / path.name)
            except (FileNotFoundError, OSError):
                pass
            return {
                "path": str(path),
                "ok": False,
                "error": f"{type(e).__name__}: {e}",
                "elapsed": time.time() - t0,
            }

    async def _gather_all() -> list[dict]:
        return await asyncio.gather(
            *[_process_one(p) for p in brief_paths],
            return_exceptions=False,
        )

    # 워커 프로세스의 메인 — asyncio 이벤트 루프 1회 실행
    return asyncio.run(_gather_all())


# ── 메인 프로세스에서 부르는 진입점 ───────────────────────────

def run_briefs_parallel(
    briefs: list[Path] | list[str],
    *,
    workers: int = DEFAULT_WORKERS,
    concurrency: int = DEFAULT_CONCURRENCY,
    timeout_per_chunk: int = 900,
) -> list[dict]:
    """병렬 처리 진입점.

    Args:
        briefs: brief 파일 경로 리스트
        workers: 워커 프로세스 수 (기본 4) — 맥미니 CPU 코어 활용
        concurrency: 워커당 asyncio 동시 처리 수 (기본 4) — IO 효율
        timeout_per_chunk: 한 chunk(=workers개 brief 묶음) 최대 처리 시간(초)

    Returns:
        모든 brief의 처리 결과 리스트. 각 항목: {path, ok, [error|saved], elapsed}
    """
    if not briefs:
        return []

    brief_strs = [str(p) for p in briefs]

    # concurrency개씩 chunk로 나눔. 워커 1개가 chunk 1개 처리.
    chunks = [
        brief_strs[i : i + concurrency]
        for i in range(0, len(brief_strs), concurrency)
    ]

    total = len(brief_strs)
    log.info(
        "[worker_pool] %d brief → workers=%d × concurrency=%d → chunks=%d",
        total, workers, concurrency, len(chunks),
    )

    all_results: list[dict] = []
    # macOS는 spawn이 안전 (fork는 자식 프로세스 데드락 가능성)
    ctx = get_context("spawn")

    t0 = time.time()
    with ProcessPoolExecutor(max_workers=workers, mp_context=ctx) as ex:
        futures = {ex.submit(_run_async_batch, chunk): chunk for chunk in chunks}
        for f in as_completed(futures):
            try:
                results = f.result(timeout=timeout_per_chunk)
                all_results.extend(results)
            except Exception as e:
                log.exception("[worker_pool] chunk 실패: %s", e)
                # 실패한 chunk의 brief들도 결과에 기록 (재시도 위해)
                chunk = futures[f]
                for p in chunk:
                    all_results.append({
                        "path": p,
                        "ok": False,
                        "error": f"chunk failure: {type(e).__name__}: {e}",
                        "elapsed": -1,
                    })

    elapsed = time.time() - t0
    ok_count = sum(1 for r in all_results if r.get("ok"))
    avg = sum(r.get("elapsed", 0) for r in all_results if r.get("elapsed", 0) > 0)
    avg = avg / max(1, ok_count) if ok_count else 0

    log.info(
        "[worker_pool] 완료: %d/%d 성공 · 전체 %.1fs · 평균 brief당 %.1fs",
        ok_count, total, elapsed, avg,
    )
    return all_results


# ── CLI / 디버그용 ────────────────────────────────────────────

def main():
    """CLI 진입점 — briefs/ 의 모든 *.json 을 병렬 처리.

    사용: python -m agents.worker_pool [--workers N] [--concurrency M] [--dry-run]
    """
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY)
    parser.add_argument("--dry-run", action="store_true",
                        help="briefs 발견만 보고하고 실행 X")
    args = parser.parse_args()

    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s [%(name)s] %(message)s",
    )

    briefs = sorted(Path("briefs").glob("*.json"))
    if not briefs:
        print("briefs/ 에 처리할 *.json 없음.")
        return

    print(f"발견: {len(briefs)}개 brief")
    if args.dry_run:
        for b in briefs:
            print(f"  - {b.name}")
        return

    results = run_briefs_parallel(
        briefs, workers=args.workers, concurrency=args.concurrency
    )

    print(f"\n=== 결과 ===")
    for r in results:
        flag = "✓" if r["ok"] else "✗"
        path = Path(r["path"]).name
        if r["ok"]:
            print(f"  {flag} {path}  ({r.get('agent','?')}, {r.get('elapsed',0):.1f}s, {len(r.get('saved',[]))}개 산출물)")
        else:
            print(f"  {flag} {path}  ERROR: {r.get('error','?')}")


if __name__ == "__main__":
    main()
