#!/bin/bash
# 티스토리 세션 갱신 — 더블클릭으로 실행
cd "/Users/seohyeongmin/Desktop/강의 홈페이지 제작" || exit 1
source .venv/bin/activate
python -m tistory_helpers.auth
echo ""
echo "=== 완료. 이 창은 그냥 닫으셔도 됩니다 ==="
read -p "닫기 ▶ "
