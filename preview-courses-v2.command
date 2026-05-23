#!/bin/bash
# 코스 v2 시안 미리보기 — 더블클릭
PROJECT="/Users/seohyeongmin/Desktop/강의 홈페이지 제작"
PORT=7922
URL="http://localhost:$PORT/site/design-previews/courses-v2/index.html"

cd "$PROJECT"
echo "코스 v2 시안 미리보기 (20개 코스)"
echo "URL: $URL"
echo "(Ctrl+C로 서버 종료)"

lsof -ti:$PORT 2>/dev/null | xargs kill -9 2>/dev/null || true
( sleep 2 && open -a "Google Chrome" "$URL" ) &
python3 -m http.server $PORT
