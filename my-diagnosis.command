#!/bin/bash
# 회원님 개인 진단 1건 생성 — Core Compass 3 AI 다중 검증
# 더블클릭으로 실행

PROJECT="/Users/seohyeongmin/Desktop/강의 홈페이지 제작"
cd "$PROJECT"

echo "════════════════════════════════════════════════════════════"
echo " Core Compass — 회원님 진단 (3 AI 다중 검증)"
echo "════════════════════════════════════════════════════════════"
echo ""

# 패키지 자동 확인
python3 -c "import openai, google.genai, anthropic" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚙️  패키지 설치 중..."
    pip3 install --quiet openai google-genai anthropic python-dotenv httpx 2>&1 | tail -2
fi

# 인터랙티브 진단 시작
python3 scripts/my_diagnosis.py

echo ""
read -p "엔터를 눌러 창 닫기..."
