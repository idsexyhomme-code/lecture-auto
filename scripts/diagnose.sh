#!/bin/bash
# 코어 캠퍼스 시스템 전체 진단 — 어디가 막혔는지 한눈에.
# 각 레이어를 아래에서 위로 체크. 빨간 X 나오는 줄에서 막힘.

cd "$(dirname "$0")/.."
REPO_ROOT="$(pwd)"

echo "════════════════════════════════════════════════"
echo "  코어 캠퍼스 시스템 진단 — $(date '+%Y-%m-%d %H:%M:%S')"
echo "════════════════════════════════════════════════"
echo ""

# ─── 1. 기본 환경 ──────────────────────────────────────
echo "▶ [1] 기본 환경"
echo -n "  - repo dir 접근:       "
[ -d "$REPO_ROOT" ] && echo "✅ $REPO_ROOT" || echo "❌"

echo -n "  - .env 파일:           "
[ -f .env ] && echo "✅" || echo "❌ MISSING"

echo -n "  - .venv 존재:          "
[ -d .venv ] && echo "✅" || echo "❌ MISSING"

echo -n "  - .venv python:        "
if [ -x .venv/bin/python ]; then
    .venv/bin/python --version
else
    echo "❌ MISSING"
fi

echo -n "  - 의존성 (anthropic):  "
.venv/bin/python -c "import anthropic" 2>/dev/null && echo "✅" || echo "❌ pip install -r requirements.txt 필요"

echo -n "  - 의존성 (jinja2):     "
.venv/bin/python -c "import jinja2" 2>/dev/null && echo "✅" || echo "❌"

echo -n "  - 의존성 (bleach):     "
.venv/bin/python -c "import bleach" 2>/dev/null && echo "✅" || echo "❌"

echo ""

# ─── 2. 환경 변수 ──────────────────────────────────────
echo "▶ [2] 환경 변수 (.env)"
for key in ANTHROPIC_API_KEY TELEGRAM_BOT_TOKEN TELEGRAM_CHAT_ID GH_PAT GITHUB_REPOSITORY; do
    val=$(grep "^${key}=" .env 2>/dev/null | head -1 | cut -d= -f2-)
    if [ -z "$val" ]; then
        echo "  - $key: ❌ MISSING"
    else
        # 길이만 출력 (키 노출 방지)
        len=${#val}
        echo "  - $key: ✅ (${len}자)"
    fi
done
echo ""

# ─── 3. 데몬 상태 ──────────────────────────────────────
echo "▶ [3] launchd 데몬"
if launchctl list | grep -q com.corecampus.longpoll; then
    line=$(launchctl list | grep com.corecampus.longpoll)
    pid=$(echo "$line" | awk '{print $1}')
    rc=$(echo "$line" | awk '{print $2}')
    echo "  - 등록됨:              ✅ PID=$pid rc=$rc"
    if [ "$pid" = "-" ] || [ "$pid" = "0" ]; then
        echo "  - 실행 중:             ❌ 프로세스 없음 (rc=$rc 이전 종료 코드)"
    else
        echo "  - 실행 중:             ✅"
    fi
else
    echo "  - 등록됨:              ❌ — bash launchd/install.sh install 필요"
fi

# 로그 파일
LOG="$HOME/Library/Logs/corecampus-longpoll.log"
ELOG="$HOME/Library/Logs/corecampus-longpoll.err.log"
echo -n "  - stdout 로그:         "
[ -f "$LOG" ] && echo "✅ ($(wc -l < "$LOG" | tr -d ' ')줄, $(stat -f '%Sm' "$LOG"))" || echo "❌"
echo -n "  - stderr 로그:         "
[ -f "$ELOG" ] && echo "✅ ($(wc -l < "$ELOG" | tr -d ' ')줄, $(stat -f '%Sm' "$ELOG"))" || echo "❌"

# 최근 stderr 마지막 5줄
if [ -f "$ELOG" ]; then
    echo "  - stderr 마지막 5줄:"
    tail -5 "$ELOG" | sed 's/^/      /'
fi
echo ""

# ─── 4. Git 상태 ──────────────────────────────────────
echo "▶ [4] Git 상태"
echo -n "  - 현재 브랜치:         "
git branch --show-current 2>/dev/null || echo "❌"

echo -n "  - working tree:        "
if git diff --quiet 2>/dev/null && git diff --cached --quiet 2>/dev/null; then
    echo "✅ clean"
else
    chg=$(git status --porcelain | wc -l | tr -d ' ')
    echo "⚠️  $chg개 변경"
fi

echo -n "  - origin sync:         "
git fetch origin main 2>/dev/null
local=$(git rev-parse main 2>/dev/null)
remote=$(git rev-parse origin/main 2>/dev/null)
if [ "$local" = "$remote" ]; then
    echo "✅ up to date"
else
    behind=$(git rev-list --count HEAD..origin/main 2>/dev/null)
    ahead=$(git rev-list --count origin/main..HEAD 2>/dev/null)
    echo "⚠️  ahead=$ahead behind=$behind"
fi

echo -n "  - .git/index.lock:     "
[ -f .git/index.lock ] && echo "❌ 존재 — 데몬·다른 git 작업 멈춤 신호" || echo "✅ 없음"

echo "  - 최근 commit 5개:"
git log --oneline -5 2>/dev/null | sed 's/^/      /'
echo ""

# ─── 5. 큐·산출물 상태 ────────────────────────────────
echo "▶ [5] 작업 큐"
brief_n=$(ls briefs/*.json 2>/dev/null | wc -l | tr -d ' ')
brief_failed=$(ls briefs/_failed/*.json 2>/dev/null | wc -l | tr -d ' ')
brief_processed=$(ls briefs/_processed/*.json 2>/dev/null | wc -l | tr -d ' ')
pending_n=$(ls content/pending/*.json 2>/dev/null | wc -l | tr -d ' ')
approved_n=$(ls content/approved/*.json 2>/dev/null | wc -l | tr -d ' ')
rejected_n=$(ls content/rejected/*.json 2>/dev/null | wc -l | tr -d ' ')

echo "  - briefs/ 대기:        $brief_n건"
echo "  - briefs/_failed/:     $brief_failed건 (격리됨)"
echo "  - briefs/_processed/:  $brief_processed건 (완료)"
echo "  - content/pending/:    $pending_n건 (승인 대기)"
echo "  - content/approved/:   $approved_n건 (사이트 반영됨)"
echo "  - content/rejected/:   $rejected_n건"

# 가장 최근 brief
if [ "$brief_n" -gt 0 ]; then
    echo "  - 가장 최근 brief:"
    ls -t briefs/*.json 2>/dev/null | head -1 | sed 's/^/      /'
fi
echo ""

# ─── 6. AUTO 모드 / 안전 ──────────────────────────────
echo "▶ [6] AUTO 모드 + 안전장치"
if [ -f content/state/safety.json ]; then
    auto=$(.venv/bin/python -c "import json;d=json.load(open('content/state/safety.json'));print(d.get('auto_mode',False))" 2>/dev/null)
    paused=$(.venv/bin/python -c "import json;d=json.load(open('content/state/safety.json'));print(d.get('paused',False))" 2>/dev/null)
    daily=$(.venv/bin/python -c "import json;d=json.load(open('content/state/safety.json'));print(d.get('daily_brief_count',0))" 2>/dev/null)
    cost=$(.venv/bin/python -c "import json;d=json.load(open('content/state/safety.json'));print(d.get('daily_estimated_cost_usd',0))" 2>/dev/null)
    echo "  - auto_mode:           $auto"
    echo "  - paused:              $paused"
    echo "  - 오늘 brief:          $daily/50"
    echo "  - 오늘 비용:           ~\$$cost / \$5"
else
    echo "  - safety.json:         ❌ 없음"
fi
echo ""

# ─── 7. Telegram API 도달 ─────────────────────────────
echo "▶ [7] Telegram API 도달"
TOKEN=$(grep '^TELEGRAM_BOT_TOKEN=' .env | cut -d= -f2 | tr -d ' \n')
if [ -n "$TOKEN" ]; then
    code=$(curl -s -o /dev/null -w '%{http_code}' "https://api.telegram.org/bot${TOKEN}/getMe" --max-time 5)
    if [ "$code" = "200" ]; then
        echo "  - getMe:               ✅ 200"
    else
        echo "  - getMe:               ❌ HTTP $code"
    fi
else
    echo "  - getMe:               ❌ 토큰 없음"
fi
echo ""

# ─── 8. GitHub API 도달 ───────────────────────────────
echo "▶ [8] GitHub API 도달"
PAT=$(grep '^GH_PAT=' .env | cut -d= -f2 | tr -d ' \n')
REPO=$(grep '^GITHUB_REPOSITORY=' .env | cut -d= -f2 | tr -d ' \n')
if [ -n "$PAT" ] && [ -n "$REPO" ]; then
    code=$(curl -s -o /dev/null -w '%{http_code}' \
        -H "Authorization: Bearer $PAT" \
        -H "Accept: application/vnd.github+json" \
        "https://api.github.com/repos/${REPO}" --max-time 5)
    if [ "$code" = "200" ]; then
        echo "  - repo 조회:           ✅ 200"
    else
        echo "  - repo 조회:           ❌ HTTP $code (PAT 권한 의심)"
    fi
else
    echo "  - repo 조회:           ❌ PAT/REPO 없음"
fi

# 최근 워크플로우 run
if [ -n "$PAT" ]; then
    echo "  - 최근 agent-loop run 3개:"
    curl -s -H "Authorization: Bearer $PAT" -H "Accept: application/vnd.github+json" \
        "https://api.github.com/repos/${REPO}/actions/workflows/agent-loop.yml/runs?per_page=3" \
        --max-time 5 \
    | .venv/bin/python -c "
import json, sys
try:
    d = json.load(sys.stdin)
    for r in d.get('workflow_runs', [])[:3]:
        print(f'      {r[\"created_at\"]}  status={r[\"status\"]}/{r[\"conclusion\"]}  #{r[\"run_number\"]}')
except Exception as e:
    print(f'      ! parse error: {e}')
" 2>/dev/null
fi
echo ""

# ─── 9. Pages 사이트 도달 ─────────────────────────────
echo "▶ [9] 라이브 사이트"
if [ -n "$REPO" ]; then
    OWNER=$(echo "$REPO" | cut -d/ -f1 | tr '[:upper:]' '[:lower:]')
    NAME=$(echo "$REPO" | cut -d/ -f2)
    URL="https://${OWNER}.github.io/${NAME}/"
    code=$(curl -s -o /dev/null -w '%{http_code}' "$URL" --max-time 5)
    echo "  - URL:                 $URL"
    echo "  - HTTP 상태:           $code"
fi
echo ""

echo "════════════════════════════════════════════════"
echo "  진단 완료. 위에서 ❌ 또는 ⚠️  표시된 줄이 막힌 곳."
echo "════════════════════════════════════════════════"
