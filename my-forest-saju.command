#!/bin/bash
# 🌿 숲사주 — 내 정보로 결과 받아보기
# 더블클릭 → 정보 입력 → 3 AI 생성 → 브라우저 자동 오픈

PROJECT="/Users/seohyeongmin/Desktop/강의 홈페이지 제작"
cd "$PROJECT"

echo "════════════════════════════════════════════════════════════"
echo "  🌿 숲사주 — 나만의 사주 숲이 열립니다"
echo "════════════════════════════════════════════════════════════"
echo ""

# 패키지 확인
python3 -c "import openai, google.genai, anthropic, dotenv" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "  ⚙️  필요한 패키지 설치 중..."
    pip3 install --quiet openai google-genai anthropic python-dotenv httpx 2>&1 | tail -2
    echo "  ✅ 설치 완료"
    echo ""
fi

# 인터랙티브 진단 시작
python3 scripts/forest_saju.py

echo ""
echo "════════════════════════════════════════════════════════════"
read -p "  엔터를 눌러 창 닫기..."
