#!/bin/bash
# Core Compass v2 미리보기 — 더블클릭하면 로컬 서버 + Chrome 자동 오픈
PROJECT="/Users/seohyeongmin/Desktop/강의 홈페이지 제작"
PORT=7920
URL="http://localhost:$PORT/site/landing/core-compass/"

cd "$PROJECT"
echo "Core Compass v2 미리보기"
echo "URL: $URL"
echo "(Ctrl+C 누르면 서버 종료)"

# 기존 서버 죽이기
lsof -ti:$PORT 2>/dev/null | xargs kill -9 2>/dev/null || true

# Chrome 자동 오픈 (2초 후)
( sleep 2 && open -a "Google Chrome" "$URL" ) &

# Python http.server
python3 -m http.server $PORT
