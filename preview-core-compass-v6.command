#!/bin/bash
PROJECT="/Users/seohyeongmin/Desktop/강의 홈페이지 제작"
PORT=7925
URL="http://localhost:$PORT/site/landing/core-compass/v6/"

cd "$PROJECT"
echo "Core Compass v6 (yongyong 픽셀 일치 + 영상 placeholder)"
echo "URL: $URL"
echo ""
echo "영상 작업자에게 줄 사양: site/landing/core-compass/v6/VIDEO_SPEC.md"

lsof -ti:$PORT 2>/dev/null | xargs kill -9 2>/dev/null || true
( sleep 2 && open -a "Google Chrome" "$URL" ) &
python3 -m http.server $PORT
