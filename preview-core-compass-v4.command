#!/bin/bash
PROJECT="/Users/seohyeongmin/Desktop/강의 홈페이지 제작"
PORT=7923
URL="http://localhost:$PORT/site/landing/core-compass/v4/"

cd "$PROJECT"
echo "Core Compass v4 (yongyong 흡수 + 차별화)"
echo "URL: $URL"

lsof -ti:$PORT 2>/dev/null | xargs kill -9 2>/dev/null || true
( sleep 2 && open -a "Google Chrome" "$URL" ) &
python3 -m http.server $PORT
