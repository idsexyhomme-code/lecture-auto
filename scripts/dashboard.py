"""Core Campus 실시간 대시보드 — localhost:7878

데몬 상태, KPI, 최근 처리·승인 대기·발행 글을 한 화면에. 30초 자동 갱신.

사용:
    python scripts/dashboard.py                  # localhost:7878 서버 시작
    open http://localhost:7878                   # 브라우저로 열기

또는 open-dashboard.command 더블클릭.
"""
from __future__ import annotations
import http.server, json, os, time, socketserver, glob
from datetime import datetime, timezone, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
KST = timezone(timedelta(hours=9))
PORT = int(os.environ.get("CC_DASHBOARD_PORT", "7878"))


def kst_iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=KST).strftime("%H:%M:%S")


def kst_full(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=KST).strftime("%Y-%m-%d %H:%M:%S")


def load_kpi() -> dict:
    f = REPO / "content" / "state" / "kpi.json"
    if not f.exists():
        return {}
    try:
        return json.load(open(f))
    except Exception:
        return {}


def recent_files(pattern: str, n: int = 5) -> list[dict]:
    files = sorted(glob.glob(str(REPO / pattern)), key=os.path.getmtime, reverse=True)[:n]
    out = []
    for f in files:
        mt = os.path.getmtime(f)
        title = ""
        kind = ""
        try:
            d = json.load(open(f))
            title = (d.get("title") or "")[:80]
            kind = d.get("kind") or ""
        except Exception:
            pass
        out.append({
            "name": os.path.basename(f),
            "mtime": mt,
            "mtime_kst": kst_iso(mt),
            "ago_sec": int(time.time() - mt),
            "title": title,
            "kind": kind,
        })
    return out


def daemon_status() -> dict:
    """데몬이 살아있는지 추정. content/state/* 또는 briefs/_processed/ 최근 활동으로 판단."""
    indicators = []
    for p in ["content/state/kpi.json", "content/state/safety.json", "content/state/telegram_offset.json"]:
        f = REPO / p
        if f.exists():
            indicators.append(f.stat().st_mtime)
    # 가장 최근 _processed brief
    procs = glob.glob(str(REPO / "briefs" / "_processed" / "*.json"))
    if procs:
        indicators.append(max(os.path.getmtime(x) for x in procs))
    if not indicators:
        return {"alive": False, "last": "(never)", "ago_sec": -1}
    last = max(indicators)
    ago = int(time.time() - last)
    return {
        "alive": ago < 600,  # 10분 이내 활동이면 살아있다고 판단
        "last": kst_full(last),
        "ago_sec": ago,
        "ago_human": _human_ago(ago),
    }


def _human_ago(sec: int) -> str:
    if sec < 60: return f"{sec}초 전"
    if sec < 3600: return f"{sec // 60}분 전"
    if sec < 86400: return f"{sec // 3600}시간 전"
    return f"{sec // 86400}일 전"


def blog_status() -> dict:
    """발행/예약/실패 카운트."""
    pub = sched = failed = 0
    last_pub = 0.0
    for f in glob.glob(str(REPO / "content" / "approved" / "*.json")):
        try:
            d = json.load(open(f))
        except Exception:
            continue
        if d.get("kind") != "blog_post":
            continue
        m = d.get("meta") or {}
        st = m.get("tistory_status")
        if st == "scheduled":
            sched += 1
        elif m.get("tistory_url"):
            pub += 1
            mt = os.path.getmtime(f)
            if mt > last_pub: last_pub = mt
        elif st == "failed":
            failed += 1
    return {
        "published": pub,
        "scheduled": sched,
        "failed": failed,
        "last_publish": kst_full(last_pub) if last_pub else "(없음)",
    }


def self_review_stats() -> dict:
    """F1 self_review 결과 통계 — approved 메타에서 집계."""
    sev_counter = {"pass": 0, "warn": 0, "fail": 0, "unknown": 0}
    for f in glob.glob(str(REPO / "content" / "approved" / "*.json")):
        try:
            d = json.load(open(f))
        except Exception:
            continue
        sr = (d.get("meta") or {}).get("self_review") or {}
        sev = sr.get("severity", "unknown")
        sev_counter[sev if sev in sev_counter else "unknown"] += 1
    total = sum(sev_counter.values())
    return {
        "total": total,
        **sev_counter,
        "pass_pct": round(100 * sev_counter["pass"] / total, 1) if total else 0,
    }


def learning_status() -> dict:
    """F3·F5 학습 상태."""
    try:
        sys.path.insert(0, str(REPO))
        from agents.memory import get_status
        return get_status()
    except Exception:
        return {"total_learned_words": 0, "learned_words": [], "stats": {}}


def ab_status() -> dict:
    """F4 A/B 테스트 결과 통계."""
    try:
        sys.path.insert(0, str(REPO))
        from agents.ab_test import get_recent_ab_stats, is_ab_enabled
        return {**get_recent_ab_stats(days=7), "enabled": is_ab_enabled()}
    except Exception:
        return {"enabled": False, "total": 0}


def worker_pool_status() -> dict:
    """P2 워커 풀 상태."""
    return {
        "parallel_enabled": os.environ.get("CC_PARALLEL", "").lower() in ("1", "true", "yes"),
        "workers": int(os.environ.get("CC_WORKER_POOL_WORKERS", "4")),
        "concurrency": int(os.environ.get("CC_WORKER_POOL_CONCURRENCY", "4")),
        "total_capacity": int(os.environ.get("CC_WORKER_POOL_WORKERS", "4"))
                          * int(os.environ.get("CC_WORKER_POOL_CONCURRENCY", "4")),
    }


def budget_status() -> dict:
    """비용 가드레일 상태."""
    try:
        sys.path.insert(0, str(REPO))
        from agents.budget_guard import get_status
        return get_status()
    except Exception:
        return {"current_usd": 0, "cap_usd": 50, "pct": 0}


def dry_run_status() -> dict:
    return {
        "dry_run": os.environ.get("DRY_RUN", "").lower() in ("1", "true", "yes"),
        "instagram_skip": os.environ.get("INSTAGRAM_SKIP", "").lower() in ("1", "true", "yes"),
        "tistory_skip": os.environ.get("TISTORY_SKIP", "").lower() in ("1", "true", "yes"),
    }


def tasks_queue_status() -> dict:
    """§11 디스패치 큐 상태."""
    try:
        sys.path.insert(0, str(REPO))
        from agents.sub_agents import get_queue_status
        return get_queue_status()
    except Exception:
        return {"pending": 0, "in_progress": 0, "completed": 0,
                "review_required": 0, "approved": 0, "rejected": 0}


def snapshot() -> dict:
    kpi = load_kpi()
    latest = kpi.get("latest") or {}
    return {
        "now_kst": datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S"),
        "daemon": daemon_status(),
        "kpi": latest,
        "blog": blog_status(),
        "recent_processed": recent_files("briefs/_processed/*.json", 8),
        "recent_pending": recent_files("content/pending/*.json", 5),
        "recent_approved": recent_files("content/approved/*.json", 5),
        "queued_briefs": recent_files("briefs/*.json", 8),
        # 신규 — Phase 1·2 모니터링
        "worker_pool": worker_pool_status(),
        "self_review": self_review_stats(),
        "learning": learning_status(),
        "ab_test": ab_status(),
        # Phase 5·6 — 비용·DRY_RUN
        "budget": budget_status(),
        "dry_run": dry_run_status(),
        # §11 디스패치 큐
        "tasks_queue": tasks_queue_status(),
    }


HTML = """<!doctype html>
<html lang="ko"><head>
<meta charset="utf-8">
<title>Core Campus — 모니터링</title>
<style>
  :root {
    --bg:#1a1814; --fg:#f5efe0; --muted:#9c8d7a; --brand:#c99756; --soft:#2c2620;
    --green:#5fb56f; --red:#e06363; --yellow:#e4b13c;
  }
  body { font-family: -apple-system,'Pretendard',sans-serif; background:var(--bg); color:var(--fg); margin:0; padding:24px; line-height:1.6; }
  h1 { font-size:22px; margin:0 0 4px; }
  .sub { color:var(--muted); font-size:13px; margin-bottom:24px; }
  .grid { display:grid; grid-template-columns:1fr 1fr; gap:20px; }
  .card { background:var(--soft); border-radius:12px; padding:18px 20px; }
  .card h2 { font-size:13px; color:var(--muted); margin:0 0 12px; text-transform:uppercase; letter-spacing:0.08em; font-weight:600; }
  .stat-row { display:flex; gap:24px; flex-wrap:wrap; }
  .stat { flex:1; min-width:80px; }
  .stat-val { font-size:32px; font-weight:800; color:var(--brand); line-height:1; }
  .stat-lbl { font-size:11px; color:var(--muted); text-transform:uppercase; letter-spacing:0.06em; margin-top:6px; }
  .row { padding:8px 0; border-bottom:1px solid rgba(255,255,255,0.05); }
  .row:last-child { border-bottom:none; }
  .row .when { font-size:11px; color:var(--muted); font-family: 'SF Mono',monospace; }
  .row .name { font-size:13px; color:var(--fg); margin-top:2px; }
  .row .name strong { color:var(--brand); }
  .row .meta { font-size:11px; color:var(--muted); margin-top:2px; }
  .status-pill { display:inline-block; padding:4px 10px; border-radius:99px; font-size:11px; font-weight:700; }
  .status-alive { background:rgba(95,181,111,0.15); color:var(--green); }
  .status-dead { background:rgba(224,99,99,0.15); color:var(--red); }
  .links a { color:var(--brand); text-decoration:none; display:block; padding:6px 0; font-size:13px; }
  .links a:hover { color:var(--fg); }
  .grid3 { grid-column:span 2; display:grid; grid-template-columns:1fr 1fr 1fr; gap:20px; margin-top:0; }
  @media (max-width: 900px) { .grid, .grid3 { grid-template-columns:1fr; } }
</style>
</head>
<body>
  <h1>🎓 Core Campus — 데몬 모니터</h1>
  <div class="sub" id="now">로딩 중…</div>

  <div class="grid3">
    <div class="card">
      <h2>📡 데몬 상태</h2>
      <div id="daemon"></div>
    </div>
    <div class="card">
      <h2>📊 사이트 KPI</h2>
      <div class="stat-row" id="kpi"></div>
    </div>
    <div class="card">
      <h2>📝 블로그 발행</h2>
      <div class="stat-row" id="blog"></div>
    </div>
  </div>

  <div class="grid" style="margin-top:20px">
    <div class="card">
      <h2>⏳ 큐잉된 briefs (대기 중)</h2>
      <div id="queued"></div>
    </div>
    <div class="card">
      <h2>✅ 최근 처리된 briefs</h2>
      <div id="processed"></div>
    </div>
  </div>

  <div class="grid" style="margin-top:20px">
    <div class="card">
      <h2>📨 회원 승인 대기 (pending)</h2>
      <div id="pending"></div>
    </div>
    <div class="card">
      <h2>📦 최근 승인 완료</h2>
      <div id="approved"></div>
    </div>
  </div>

  <div class="grid" style="margin-top:20px">
    <div class="card">
      <h2>⚙️ 워커 풀 (P2)</h2>
      <div id="worker_pool"></div>
    </div>
    <div class="card">
      <h2>🔍 자가 검수 통계 (F1)</h2>
      <div class="stat-row" id="self_review"></div>
    </div>
  </div>

  <div class="grid" style="margin-top:20px">
    <div class="card">
      <h2>🧠 학습된 패턴 (F3+F5)</h2>
      <div id="learning"></div>
    </div>
    <div class="card">
      <h2>🆎 A/B 테스트 결과 (F4)</h2>
      <div id="ab_test"></div>
    </div>
  </div>

  <div class="grid" style="margin-top:20px">
    <div class="card">
      <h2>🔗 빠른 링크</h2>
      <div class="links">
        <a href="https://idsexyhomme-code.github.io/lecture-auto/" target="_blank">🌐 라이브 사이트</a>
        <a href="https://jejumomdad.tistory.com/manage/posts/" target="_blank">📝 티스토리 글 관리</a>
        <a href="https://github.com/idsexyhomme-code/lecture-auto/actions" target="_blank">⚙️ GitHub Actions</a>
        <a href="https://github.com/idsexyhomme-code/lecture-auto/commits/main" target="_blank">📜 최근 커밋</a>
      </div>
    </div>
    <div class="card">
      <h2>🎩 CEO 헌법</h2>
      <div class="links">
        <a href="/charter" target="_blank">헌법 전문 보기 →</a>
        <a href="/kpi-history" target="_blank">KPI 히스토리 (JSON) →</a>
      </div>
      <div class="sub" style="margin-top:12px; font-size:12px;">매일 09:00 KST 자동 일일 보고<br>매 산출물 CEO 게이트 작동 중</div>
    </div>
  </div>

<script>
const fmt = (n) => (typeof n === 'number' ? n.toLocaleString() : (n ?? '—'));
const ago = (sec) => {
  if (sec < 0) return '—';
  if (sec < 60) return sec + '초 전';
  if (sec < 3600) return Math.floor(sec/60) + '분 전';
  if (sec < 86400) return Math.floor(sec/3600) + '시간 전';
  return Math.floor(sec/86400) + '일 전';
};

async function refresh() {
  try {
    const r = await fetch('/api/snapshot?t=' + Date.now());
    const d = await r.json();
    document.getElementById('now').textContent = '현재 ' + d.now_kst + ' · 30초마다 자동 갱신';

    // 데몬
    const dm = d.daemon;
    document.getElementById('daemon').innerHTML = `
      <span class="status-pill ${dm.alive ? 'status-alive' : 'status-dead'}">${dm.alive ? '● 가동 중' : '● 정지 또는 지연'}</span>
      <div class="meta" style="margin-top:8px">마지막 활동: <strong>${dm.ago_human || ago(dm.ago_sec)}</strong></div>
      <div class="meta">${dm.last}</div>
    `;

    // KPI
    const k = d.kpi;
    document.getElementById('kpi').innerHTML = `
      <div class="stat"><div class="stat-val">${fmt(k.courses_total)}</div><div class="stat-lbl">코스</div></div>
      <div class="stat"><div class="stat-val">${fmt(k.posts_total)}</div><div class="stat-lbl">포스트</div></div>
      <div class="stat"><div class="stat-val">${fmt(k.categories_total)}</div><div class="stat-lbl">카테고리</div></div>
      <div class="stat"><div class="stat-val">${fmt(k.pending_count)}</div><div class="stat-lbl">승인 대기</div></div>
    `;

    // Blog
    const b = d.blog;
    document.getElementById('blog').innerHTML = `
      <div class="stat"><div class="stat-val">${fmt(b.published)}</div><div class="stat-lbl">발행</div></div>
      <div class="stat"><div class="stat-val">${fmt(b.scheduled)}</div><div class="stat-lbl">예약</div></div>
      <div class="stat"><div class="stat-val" style="color:var(--red)">${fmt(b.failed)}</div><div class="stat-lbl">실패</div></div>
    `;

    const renderRows = (arr) => arr.length === 0 ? '<div class="sub" style="font-size:12px;color:var(--muted)">(비어 있음)</div>' :
      arr.map(r => `<div class="row">
        <div class="when">${r.mtime_kst} (${ago(r.ago_sec)})</div>
        <div class="name">${r.kind ? '<strong>['+r.kind+']</strong> ' : ''}${r.title || r.name}</div>
      </div>`).join('');

    document.getElementById('queued').innerHTML = renderRows(d.queued_briefs);
    document.getElementById('processed').innerHTML = renderRows(d.recent_processed);
    document.getElementById('pending').innerHTML = renderRows(d.recent_pending);
    document.getElementById('approved').innerHTML = renderRows(d.recent_approved);

    // Worker pool
    const wp = d.worker_pool || {};
    document.getElementById('worker_pool').innerHTML = `
      <span class="status-pill ${wp.parallel_enabled ? 'status-alive' : 'status-dead'}">${wp.parallel_enabled ? '● 병렬 활성' : '● 직렬 모드'}</span>
      <div class="meta" style="margin-top:10px">
        <div>workers × concurrency = <strong>${wp.workers} × ${wp.concurrency} = ${wp.total_capacity} 동시</strong></div>
        <div style="font-size:11px;margin-top:4px;color:var(--muted)">CC_PARALLEL=1 환경변수로 활성</div>
      </div>
    `;

    // Self-review stats
    const sr = d.self_review || {};
    document.getElementById('self_review').innerHTML = `
      <div class="stat"><div class="stat-val" style="color:var(--green)">${fmt(sr.pass)}</div><div class="stat-lbl">pass</div></div>
      <div class="stat"><div class="stat-val" style="color:var(--yellow)">${fmt(sr.warn)}</div><div class="stat-lbl">warn</div></div>
      <div class="stat"><div class="stat-val" style="color:var(--red)">${fmt(sr.fail)}</div><div class="stat-lbl">fail</div></div>
      <div class="stat"><div class="stat-val">${fmt(sr.pass_pct)}%</div><div class="stat-lbl">통과율</div></div>
    `;

    // Learning
    const lr = d.learning || {};
    const learned = (lr.learned_words || []).slice(0, 8);
    const topFail = Object.entries(lr.top_fail_patterns || {}).slice(0, 5);
    document.getElementById('learning').innerHTML = `
      <div class="meta" style="margin-bottom:8px">
        학습된 금기어 <strong>${fmt(lr.total_learned_words)}</strong>개 / 누적 검수 <strong>${fmt((lr.stats||{}).total_reviews)}</strong>건
      </div>
      ${learned.length ? '<div class="meta" style="margin-top:6px"><strong>학습된 단어:</strong> ' + learned.map(w=>`<code>${w}</code>`).join(' · ') + '</div>' : '<div class="sub" style="font-size:12px">아직 학습된 단어 없음</div>'}
      ${topFail.length ? '<div class="meta" style="margin-top:8px;font-size:11px"><strong>fail 패턴:</strong> ' + topFail.map(([w,c])=>`${w}(${c})`).join(' / ') + '</div>' : ''}
    `;

    // A/B test
    const ab = d.ab_test || {};
    document.getElementById('ab_test').innerHTML = `
      <span class="status-pill ${ab.enabled ? 'status-alive' : 'status-dead'}">${ab.enabled ? '● 활성' : '● 비활성'}</span>
      <div class="meta" style="margin-top:10px">
        최근 7일 테스트 <strong>${fmt(ab.total)}</strong>건<br>
        v1 우승 ${fmt(ab.v1_wins)} · v2 우승 ${fmt(ab.v2_wins)}<br>
        평균 차이 (v2-v1): <strong>${(ab.avg_diff||0).toFixed(2)}</strong>
      </div>
      <div style="font-size:11px;margin-top:6px;color:var(--muted)">CC_AB_TEST=1로 활성</div>
    `;
  } catch (e) {
    document.getElementById('now').textContent = '⚠️ 갱신 실패: ' + e.message;
  }
}
refresh();
setInterval(refresh, 30000);
</script>
</body></html>
"""


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/" or self.path.startswith("/?"):
            self._send(200, "text/html; charset=utf-8", HTML)
        elif self.path.startswith("/api/snapshot"):
            data = json.dumps(snapshot(), ensure_ascii=False)
            self._send(200, "application/json; charset=utf-8", data)
        elif self.path == "/charter":
            f = REPO / "data" / "ceo_charter.md"
            if f.exists():
                md = f.read_text(encoding="utf-8")
                # Simple markdown to HTML
                html = "<pre style='font-family:system-ui,sans-serif;white-space:pre-wrap;padding:30px;max-width:800px;margin:0 auto;background:#1a1814;color:#f5efe0'>" + md.replace("<","&lt;") + "</pre>"
                self._send(200, "text/html; charset=utf-8", html)
            else:
                self._send(404, "text/plain", "헌법 파일 없음")
        elif self.path == "/kpi-history":
            f = REPO / "content" / "state" / "kpi.json"
            if f.exists():
                self._send(200, "application/json; charset=utf-8", f.read_text(encoding="utf-8"))
            else:
                self._send(404, "text/plain", "KPI 파일 없음")
        else:
            self._send(404, "text/plain", "Not found")

    def _send(self, code: int, ctype: str, body: str):
        b = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(b)

    def log_message(self, format, *args):
        # 조용히 (터미널 노이즈 줄임)
        if "api/snapshot" not in self.path:
            super().log_message(format, *args)


def main():
    print(f"🎓 Core Campus 대시보드 시작")
    print(f"   주소: http://localhost:{PORT}")
    print(f"   종료: Ctrl+C")
    print()
    with socketserver.TCPServer(("127.0.0.1", PORT), Handler) as srv:
        srv.allow_reuse_address = True
        srv.serve_forever()


if __name__ == "__main__":
    main()
