#!/bin/bash
# Core Compass v3 미리보기
PROJECT="/Users/seohyeongmin/Desktop/강의 홈페이지 제작"
PORT=7921
URL="http://localhost:$PORT/site/landing/core-compass/v3/"

cd "$PROJECT"
echo "Core Compass v3 미리보기 (Track A + B 결합)"
echo "URL: $URL"
echo "(Ctrl+C 누르면 서버 종료)"

lsof -ti:$PORT 2>/dev/null | xargs kill -9 2>/dev/null || true
( sleep 2 && open -a "Google Chrome" "$URL" ) &
python3 -m http.server $PORT
