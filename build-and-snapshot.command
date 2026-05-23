#!/bin/bash
# 🛠 수동 빌드 + 스냅샷 — 회원이 더블클릭으로 즉시 실행
# 1) site_builder/build.py 실행 → site/* 갱신
# 2) Playwright로 메인 페이지·코스 인덱스 스크린샷
# 3) Lighthouse 점수 (라이브 URL — npx 설치되어 있을 때만)
# 4) 텔레그램에 모두 발송

PROJECT="/Users/seohyeongmin/Desktop/강의 홈페이지 제작"
cd "$PROJECT" || { echo "프로젝트 폴더 못 찾음"; exit 1; }

echo "════════════════════════════════════════════════════════════"
echo "  🛠  Core Campus — 수동 빌드 + 스냅샷"
echo "════════════════════════════════════════════════════════════"
echo ""

# .venv 우선 사용
if [ -x ".venv/bin/python3" ]; then
    PY=".venv/bin/python3"
elif [ -x ".venv/bin/python" ]; then
    PY=".venv/bin/python"
else
    PY="python3"
fi
echo "  Python: $PY"
echo ""

# 1) 빌드
echo "  ── 1단계: 빌드 실행"
"$PY" scripts/auto_build.py
BUILD_RC=$?
echo ""

if [ $BUILD_RC -ne 0 ]; then
    echo "  ❌ 빌드 실패 — 스냅샷 건너뜀"
    read -p "  엔터로 닫기..."
    exit 1
fi

# 2) Playwright 확인 (없으면 스냅샷 건너뜀)
"$PY" -c "from playwright.sync_api import sync_playwright" 2>/dev/null || {
    echo "  ⚙️  Playwright 미설치 — 설치 중..."
    "$PY" -m pip install --quiet playwright 2>&1 | tail -3
    "$PY" -m playwright install chromium 2>&1 | tail -3
}

# 3) 스냅샷 (로컬 + 모바일)
echo ""
echo "  ── 2단계: 스냅샷 캡처 (desktop)"
"$PY" scripts/site_snapshot.py --mobile --send --label "manual"
echo ""

# 4) Lighthouse (라이브 — 옵션)
if command -v npx >/dev/null 2>&1; then
    echo "  ── 3단계: Lighthouse 점수 (라이브 URL)"
    "$PY" -c "
import os
os.environ.setdefault('SITE_LIVE_URL', 'https://idsexyhomme-code.github.io/lecture-auto')
from scripts.site_snapshot import lighthouse_score, format_lighthouse_card
lh = lighthouse_score()
print(format_lighthouse_card(lh, os.environ['SITE_LIVE_URL']))
try:
    from telegram_bot import client as tg
    tg.send_text(format_lighthouse_card(lh, os.environ['SITE_LIVE_URL']))
    print('→ 텔레그램 발송됨')
except Exception as e:
    print('  발송 실패:', e)
"
else
    echo "  ── 3단계: Lighthouse 건너뜀 (npx 미설치)"
fi

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  ✓ 완료 — 텔레그램에서 결과 확인"
echo "════════════════════════════════════════════════════════════"
read -p "  엔터로 닫기..."
