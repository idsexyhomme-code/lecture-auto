#!/bin/bash
PROJECT="/Users/seohyeongmin/Desktop/강의 홈페이지 제작"
PORT=7924
URL="http://localhost:$PORT/site/landing/core-compass/v5/"

cd "$PROJECT"
echo "Core Compass v5 (yongyong 흐름 흡수 + 창업자 톤)"
echo "URL: $URL"

lsof -ti:$PORT 2>/dev/null | xargs kill -9 2>/dev/null || true
( sleep 2 && open -a "Google Chrome" "$URL" ) &
python3 -m http.server $PORT
