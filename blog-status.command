#!/bin/bash
# 🔍 블로그 발행 시스템 — 전체 상태 한 화면 (가시성 인프라 1단계)

PROJECT="/Users/seohyeongmin/Desktop/강의 홈페이지 제작"
cd "$PROJECT" || exit 1

clear
echo "════════════════════════════════════════════════════════════"
echo "  🔍 블로그 발행 시스템 — 현재 상태  $(date '+%Y-%m-%d %H:%M')"
echo "════════════════════════════════════════════════════════════"
echo ""

# 1. 데몬 상태
echo "▶ 1) 데몬 (24/7 가동 여부)"
if launchctl list 2>/dev/null | grep -q corecampus; then
    echo "    ✅ 가동 중"
    launchctl list 2>/dev/null | grep corecampus | sed 's/^/    /'
else
    echo "    ❌ 데몬 꺼져 있음 — install-daemon.command 더블클릭 필요"
fi
echo ""

# 2. brief 큐
echo "▶ 2) 큐 (briefs/) — 처리 대기 중인 발행 요청"
QUEUE=$(ls briefs/blog-publish-*.json 2>/dev/null | wc -l | tr -d ' ')
PROC=$(ls briefs/_processed/blog-publish-*.json 2>/dev/null | wc -l | tr -d ' ')
echo "    대기: ${QUEUE}건  /  처리완료: ${PROC}건"
if [ "$QUEUE" -gt 0 ]; then
    ls briefs/blog-publish-*.json 2>/dev/null | head -3 | sed 's|^|    • |'
fi
echo ""

# 3. 산출물
echo "▶ 3) 검수 대기 (content/pending/)"
PENDING=$(ls content/pending/*.json 2>/dev/null | wc -l | tr -d ' ')
echo "    ${PENDING}건 검수 대기 중"
echo ""

echo "▶ 4) 최근 승인된 블로그 글 (content/approved/, 최근 5건)"
ls -t content/approved/*.json 2>/dev/null | head -10 | while read f; do
    KIND=$(python3 -c "import json; d=json.load(open('$f')); print(d.get('kind',''))" 2>/dev/null)
    if [ "$KIND" = "blog_post" ]; then
        TITLE=$(python3 -c "import json; d=json.load(open('$f')); print(d.get('title','')[:50])" 2>/dev/null)
        URL=$(python3 -c "import json; d=json.load(open('$f')); print((d.get('meta') or {}).get('published_url','') or (d.get('meta') or {}).get('url',''))" 2>/dev/null)
        echo "    • $TITLE"
        [ -n "$URL" ] && echo "      🔗 $URL"
    fi
done
echo ""

# 4. 환경 점검
echo "▶ 5) 환경변수 (.env)"
[ -f .env ] && {
    SKIP=$(grep "^TISTORY_SKIP=" .env | cut -d= -f2)
    SCHED=$(grep "^TISTORY_SCHEDULE=" .env | cut -d= -f2)
    BLOG=$(grep "^TISTORY_BLOG=" .env | cut -d= -f2)
    IMG=$(grep "^BLOG_IMAGE_MODEL=" .env | cut -d= -f2)
    echo "    TISTORY_SKIP=${SKIP:-(미설정)}  $([ "$SKIP" = "false" ] && echo "✅ 발행 허용" || echo "❌ 발행 차단됨")"
    echo "    TISTORY_SCHEDULE=${SCHED:-(미설정=분산예약)}"
    echo "    TISTORY_BLOG=${BLOG:-(미설정)}"
    echo "    BLOG_IMAGE_MODEL=${IMG:-gemini}"
}
echo ""

# 5. 세션
echo "▶ 6) 티스토리 세션 (.command 인증 상태)"
SESS=content/state/tistory_session.json
if [ -f "$SESS" ]; then
    MTIME=$(stat -f "%Sm" -t "%Y-%m-%d %H:%M" "$SESS" 2>/dev/null)
    SIZE=$(stat -f "%z" "$SESS" 2>/dev/null)
    echo "    파일 있음 — 갱신: $MTIME  크기: ${SIZE}B"
    [ "$SIZE" -lt 1000 ] && echo "    ⚠️ 크기 작음 — 세션 유효성 의심. login-tistory.command 재실행 권장"
else
    echo "    ❌ 세션 없음 — login-tistory.command 더블클릭 필요"
fi
echo ""

# 6. 데몬 로그 마지막
echo "▶ 7) 데몬 로그 마지막 10줄"
LOG=~/Library/Logs/corecampus-longpoll.log
if [ -f "$LOG" ]; then
    tail -10 "$LOG" | sed 's/^/    /'
else
    echo "    로그 파일 없음"
fi
echo ""

echo "════════════════════════════════════════════════════════════"
echo "  💡 다음 액션 추천"
echo "════════════════════════════════════════════════════════════"
if [ "$SKIP" = "true" ]; then
    echo "  ❗ TISTORY_SKIP=true — 발행 차단됨. .env에서 false로 변경."
fi
if [ "$PENDING" -gt 0 ]; then
    echo "  📬 검수 대기 ${PENDING}건 — 텔레그램 카드 확인 후 ✅/❌"
fi
if [ "$QUEUE" -eq 0 ] && [ "$PROC" -eq 0 ]; then
    echo "  📭 큐 비어있음 — brief 새로 생성 필요"
fi
echo ""
read -p "엔터로 닫기..."
