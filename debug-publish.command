#!/bin/bash
# Tistory publisher 디버그 — 더블클릭으로 실행
cd "/Users/seohyeongmin/Desktop/강의 홈페이지 제작" || exit 1
source .venv/bin/activate
python scripts/debug_publish.py
echo ""
echo "=== 디버그 완료 ==="
read -p "닫기 ▶ "
