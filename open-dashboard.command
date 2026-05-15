#!/bin/bash
# Core Campus 모니터링 대시보드 — 더블클릭 실행
# localhost:7878 로컬 서버 시작 + 브라우저 자동 열기

cd "/Users/seohyeongmin/Desktop/강의 홈페이지 제작" || exit 1
source .venv/bin/activate

# 2초 후 브라우저 자동 오픈 (백그라운드)
(sleep 2 && open "http://localhost:7878") &

echo "🎓 Core Campus 대시보드 시작 — http://localhost:7878"
echo "   브라우저가 자동으로 열립니다"
echo "   터미널 종료하려면 Ctrl+C"
echo ""

python scripts/dashboard.py
