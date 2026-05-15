#!/bin/bash
# 데몬 로그 실시간 보기 — 더블클릭 실행
# 데몬이 무슨 brief 처리 중인지, 무슨 에러 났는지 실시간

LOG="$HOME/Library/Logs/corecampus-longpoll.log"
ERR_LOG="$HOME/Library/Logs/corecampus-longpoll.err.log"

echo "🎓 Core Campus 데몬 로그 — 실시간"
echo "   stdout: $LOG"
echo "   stderr: $ERR_LOG"
echo "   종료: Ctrl+C"
echo "═══════════════════════════════════════════════════════════"
echo ""

# stdout + stderr 같이
if [ -f "$LOG" ] && [ -f "$ERR_LOG" ]; then
    tail -f "$LOG" "$ERR_LOG"
elif [ -f "$LOG" ]; then
    tail -f "$LOG"
else
    echo "⚠️ 로그 파일이 없습니다. 데몬이 한 번도 실행 안 됐을 수 있어요."
    echo "   먼저 install-daemon.command 더블클릭으로 등록하세요."
    echo ""
    read -p "닫기 ▶ "
fi
