#!/bin/bash
# 🧪 8 에이전트 SYSTEM 업그레이드 — 1건 테스트
# 더블클릭으로 실행

PROJECT="/Users/seohyeongmin/Desktop/강의 홈페이지 제작"
cd "$PROJECT"

echo "════════════════════════════════════════════════════════════"
echo "  🧪 새 에이전트 SYSTEM 1건 테스트"
echo "  Amazon · Apple · Pixar · 옴니채널 · CX Automation"
echo "════════════════════════════════════════════════════════════"
echo ""

# 패키지 자동 확인
python3 -c "import anthropic, dotenv" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "  ⚙️  패키지 설치 중..."
    pip3 install --quiet anthropic python-dotenv 2>&1 | tail -2
fi

# 인터랙티브 테스트 시작
python3 scripts/test_new_agents.py

echo ""
echo "════════════════════════════════════════════════════════════"
echo ""
read -p "  엔터를 눌러 창 닫기..."
