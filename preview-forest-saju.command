#!/bin/bash
PROJECT="/Users/seohyeongmin/Desktop/강의 홈페이지 제작"
PORT=7926
URL="http://localhost:$PORT/site/forest-saju/"

cd "$PROJECT"
echo "🌿 숲사주 — 귀여운 AI 사주 웹 리포트"
echo "URL: $URL"
echo ""
echo "📁 폴더: site/forest-saju/"
echo "   - index.html              랜딩 페이지"
echo "   - result-sample.html      샘플 결과 페이지"
echo "   - result-template.html    구매자 결과 템플릿 ({{변수}})"
echo "   - README.md               운영 가이드"
echo ""

lsof -ti:$PORT 2>/dev/null | xargs kill -9 2>/dev/null || true
( sleep 2 && open -a "Google Chrome" "$URL" ) &
python3 -m http.server $PORT
