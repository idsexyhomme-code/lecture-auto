#!/bin/bash
# 데몬 24/7 자동 시작 등록 — 더블클릭으로 실행
# Mac 켜질 때마다 자동 시작 + 죽으면 자동 재시작

cd "/Users/seohyeongmin/Desktop/강의 홈페이지 제작" || exit 1
bash launchd/install.sh install
echo ""
echo "=== 등록 완료. 이제 데몬이 24/7 자동 가동됩니다 ==="
echo "  로그: tail -f ~/Library/Logs/corecampus-longpoll.log"
echo "  중지: bash launchd/install.sh stop"
echo "  상태: bash launchd/install.sh status"
echo ""
read -p "닫기 ▶ "
