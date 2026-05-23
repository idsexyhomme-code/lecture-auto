#!/bin/bash
# Core Compass 6 LLM 멀티 검증 시스템 테스트
# 더블클릭으로 실행

PROJECT="/Users/seohyeongmin/Desktop/강의 홈페이지 제작"
cd "$PROJECT"

echo "═══════════════════════════════════════════════════════════"
echo " Core Compass 6 LLM 멀티 검증 시스템 — 실 환경 테스트"
echo "═══════════════════════════════════════════════════════════"
echo ""

# 1. 패키지 자동 설치
echo "[1/3] 필수 패키지 설치 확인..."
python3 -c "import openai, google.genai, httpx, anthropic" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "   ⚙️  패키지 설치 중 (openai + google-genai + httpx)..."
    pip3 install --quiet openai google-genai httpx anthropic python-dotenv 2>&1 | tail -3
fi
echo "   ✅ 패키지 준비 완료"
echo ""

# 2. 상태 확인 (활성화된 LLM 수)
echo "[2/3] 활성화된 LLM 확인..."
echo ""
python3 scripts/test_multi_llm.py status
echo ""

# 3. 실측 호출 (활성 LLM에 짧은 ping)
echo "[3/3] 실측 호출 — 짧은 프롬프트로 활성 LLM 모두 호출"
echo ""
read -p "   실 API 호출 진행할까요? (y/N): " yn
if [[ "$yn" == "y" || "$yn" == "Y" ]]; then
    python3 scripts/test_multi_llm.py ping
    echo ""
    echo "═══════════════════════════════════════════════════════════"
    echo "  Core Compass 진단 1건 데모 실측 (6 LLM 통합 응답 생성)"
    echo "═══════════════════════════════════════════════════════════"
    read -p "   데모 진단까지 생성할까요? (비용 ~$0.05) (y/N): " yn2
    if [[ "$yn2" == "y" || "$yn2" == "Y" ]]; then
        python3 scripts/test_multi_llm.py demo
        echo ""
        echo "✅ 데모 진단 완료. content/state/multi_llm_demo.json 확인"
    fi
fi

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  종료"
echo "═══════════════════════════════════════════════════════════"
echo ""
read -p "엔터를 눌러 창 닫기..."
