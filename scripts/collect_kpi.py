"""KPI 일일 스냅샷 수집 — content/state/kpi.json

수집 항목 (모두 *로컬 파일 기반* — 외부 API 호출 없음):

- courses_total       : 사이트 빌드된 코스 수
- posts_total         : 블로그 글 수 (site/posts/*.html)
- categories_total    : 카테고리 수 (site_config.json)
- blog_published_today: 오늘 tistory에 성공 발행된 글 수
- blog_failed_today   : 오늘 발행 실패 수
- approved_count      : content/approved/*.json 누적
- pending_count       : content/pending/*.json (회원 승인 대기)
- last_brief_ts       : 마지막 처리된 brief 타임스탬프
- last_blog_publish   : 마지막 성공 발행 시각

사용:
    python scripts/collect_kpi.py                 # 스냅샷 1회 + kpi.json 갱신
    python scripts/collect_kpi.py --json          # JSON으로 stdout
"""
from __future__ import annotations
import argparse, json, glob, os, time
from datetime import datetime, timezone, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
STATE = REPO / "content" / "state"
STATE.mkdir(parents=True, exist_ok=True)
KPI_FILE = STATE / "kpi.json"

KST = timezone(timedelta(hours=9))


def today_kst() -> str:
    return datetime.now(KST).strftime("%Y-%m-%d")


def count_files(pattern: str) -> int:
    return len(glob.glob(str(REPO / pattern)))


def latest_mtime(pattern: str) -> str:
    files = glob.glob(str(REPO / pattern))
    if not files:
        return ""
    latest = max(files, key=os.path.getmtime)
    return datetime.fromtimestamp(os.path.getmtime(latest), tz=KST).isoformat()


def categories_count() -> int:
    try:
        cfg = json.load(open(REPO / "site_config.json"))
        return len(cfg.get("categories") or [])
    except Exception:
        return 0


def blog_stats():
    """오늘 KST 기준 발행/실패/예약 카운트."""
    today = today_kst()
    published = failed = scheduled = 0
    last_publish = ""
    for f in glob.glob(str(REPO / "content" / "approved" / "*.json")):
        try:
            d = json.load(open(f))
        except Exception:
            continue
        if d.get("kind") != "blog_post":
            continue
        m = d.get("meta") or {}
        st = m.get("tistory_status")
        created = d.get("created_at", "")
        is_today = today in created
        if st == "scheduled":
            scheduled += 1
        elif st in ("published",) or m.get("tistory_url"):
            if is_today:
                published += 1
            mtime = os.path.getmtime(f)
            ts_iso = datetime.fromtimestamp(mtime, tz=KST).isoformat()
            if ts_iso > last_publish:
                last_publish = ts_iso
        elif st == "failed":
            if is_today:
                failed += 1
    return {
        "blog_published_today": published,
        "blog_failed_today": failed,
        "blog_scheduled_total": scheduled,
        "last_blog_publish": last_publish,
    }


def collect() -> dict:
    snap = {
        "date_kst": today_kst(),
        "captured_at": datetime.now(KST).isoformat(),
        "courses_total": count_files("site/courses/*.html"),
        "posts_total": count_files("site/posts/*.html"),
        "categories_total": categories_count(),
        "approved_count": count_files("content/approved/*.json"),
        "pending_count": count_files("content/pending/*.json"),
        "rejected_count": count_files("content/rejected/*.json"),
        "last_brief_processed": latest_mtime("briefs/_processed/*.json"),
    }
    snap.update(blog_stats())
    return snap


def update_history(snap: dict):
    """기존 kpi.json에 history 누적. 같은 날짜는 덮어씀."""
    if KPI_FILE.exists():
        try:
            data = json.load(open(KPI_FILE))
        except Exception:
            data = {}
    else:
        data = {}
    history = data.get("history") or {}
    history[snap["date_kst"]] = snap
    # latest 별도 보관
    data["latest"] = snap
    data["history"] = history
    # 최근 90일만 유지
    if len(history) > 90:
        sorted_dates = sorted(history.keys(), reverse=True)
        keep = sorted_dates[:90]
        data["history"] = {k: history[k] for k in keep}
    KPI_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true", help="stdout에 JSON으로만 출력 (kpi.json 갱신 안 함)")
    args = ap.parse_args()

    snap = collect()
    if args.json:
        print(json.dumps(snap, ensure_ascii=False, indent=2))
        return

    update_history(snap)
    print(f"=== KPI 스냅샷 — {snap['date_kst']} ===")
    for k, v in snap.items():
        print(f"  {k}: {v}")
    print(f"\n저장: {KPI_FILE.relative_to(REPO)}")


if __name__ == "__main__":
    main()
