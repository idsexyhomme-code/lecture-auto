#!/bin/bash
# 6 LLM API key를 .env에 인터랙티브로 추가하는 도우미
# 더블클릭으로 실행

PROJECT="/Users/seohyeongmin/Desktop/강의 홈페이지 제작"
ENV_FILE="$PROJECT/.env"

cd "$PROJECT"

echo "════════════════════════════════════════════════════════════"
echo " Core Compass — LLM API Key 추가 도우미"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "이 도구는 발급받은 API key를 .env 파일에 안전하게 추가합니다."
echo "각 LLM별 발급 페이지를 자동으로 브라우저에서 엽니다."
echo ""

# 함수: 키 추가 또는 교체
add_or_replace_key() {
    local key_name="$1"
    local new_value="$2"

    if grep -q "^${key_name}=" "$ENV_FILE" 2>/dev/null; then
        # macOS sed
        sed -i.bak "s|^${key_name}=.*|${key_name}=${new_value}|" "$ENV_FILE"
        rm -f "${ENV_FILE}.bak"
        echo "   ✅ ${key_name} 갱신됨"
    else
        echo "${key_name}=${new_value}" >> "$ENV_FILE"
        echo "   ✅ ${key_name} 추가됨"
    fi
}

# 함수: 단일 LLM 처리
process_llm() {
    local llm_name="$1"
    local env_key="$2"
    local signup_url="$3"
    local key_prefix="$4"
    local extra_info="$5"

    echo ""
    echo "────────────────────────────────────────────────────────────"
    echo " ${llm_name}"
    echo "────────────────────────────────────────────────────────────"
    echo " 발급 페이지: ${signup_url}"
    [ -n "$extra_info" ] && echo " ℹ️  ${extra_info}"
    echo ""
    read -p " 발급 페이지 자동 오픈할까요? (y/N): " open_yn
    if [[ "$open_yn" == "y" || "$open_yn" == "Y" ]]; then
        open "$signup_url"
        echo " 🌐 브라우저에서 페이지 열림 — 발급 받고 키 복사 후 돌아오세요."
        echo ""
    fi

    echo " 발급받은 API key 붙여넣기 (Skip: 그냥 엔터):"
    [ -n "$key_prefix" ] && echo " (형식: ${key_prefix}...)"
    read -r api_key

    if [ -z "$api_key" ]; then
        echo "   ⏭️  건너뜀"
        return
    fi

    add_or_replace_key "$env_key" "$api_key"
}

# .env 파일 존재 확인
if [ ! -f "$ENV_FILE" ]; then
    echo "❌ .env 파일이 없습니다: $ENV_FILE"
    echo "   .env.example을 복사해서 만들어주세요."
    read -p "엔터를 눌러 종료..."
    exit 1
fi

# 메뉴
echo "════════════════════════════════════════════════════════════"
echo " 어떤 LLM을 추가할까요? (번호 입력, 여러개는 공백으로 구분)"
echo "════════════════════════════════════════════════════════════"
echo "   1) Gemini (Google)       — 무료 ✨"
echo "   2) OpenAI 잔액 충전 가이드 — 5분"
echo "   3) Perplexity            — \$5 무료 크레딧"
echo "   4) Grok (xAI)            — \$25 무료 크레딧"
echo "   5) Mistral               — \$5 무료 크레딧"
echo "   a) 모두 (1·3·4·5 순차)"
echo "   q) 종료"
echo ""
read -p "선택: " choice

case "$choice" in
    *1*|a) process_llm \
        "Google Gemini 2.0 Flash (무료)" \
        "GOOGLE_GENERATIVEAI_API_KEY" \
        "https://aistudio.google.com/apikey" \
        "AIzaSy" \
        "Gmail 로그인 → Create API key. 카드 등록 불필요." ;;
esac

case "$choice" in
    *2*)
        echo ""
        echo "────────────────────────────────────────────────────────────"
        echo " OpenAI 잔액 충전 (회원님 직접 진행)"
        echo "────────────────────────────────────────────────────────────"
        echo " 1. https://platform.openai.com/settings/organization/billing"
        echo " 2. Add payment method → 카드 등록"
        echo " 3. Add to credit balance → \$5 또는 \$10 충전"
        echo ""
        read -p " 충전 페이지 자동 오픈할까요? (y/N): " yn
        if [[ "$yn" == "y" || "$yn" == "Y" ]]; then
            open "https://platform.openai.com/settings/organization/billing"
        fi
        echo " 충전 후 별도 키 입력 불필요 — 기존 OPENAI_API_KEY 그대로 작동."
        ;;
esac

case "$choice" in
    *3*|a) process_llm \
        "Perplexity (sonar-pro)" \
        "PERPLEXITY_API_KEY" \
        "https://www.perplexity.ai/settings/api" \
        "pplx-" \
        "\$5 무료 크레딧 가입 보너스. 검색 기반 LLM." ;;
esac

case "$choice" in
    *4*|a) process_llm \
        "xAI Grok-2" \
        "XAI_API_KEY" \
        "https://console.x.ai/" \
        "xai-" \
        "\$25 무료 크레딧 (월간 갱신). Copilot 대체." ;;
esac

case "$choice" in
    *5*|a) process_llm \
        "Mistral Large (유럽 LLM)" \
        "MISTRAL_API_KEY" \
        "https://console.mistral.ai/api-keys/" \
        "" \
        "\$5 무료 크레딧. Bing 대체." ;;
esac

echo ""
echo "════════════════════════════════════════════════════════════"
echo " 완료 — 현재 활성화 상태 확인"
echo "════════════════════════════════════════════════════════════"
echo ""
python3 scripts/test_multi_llm.py status

echo ""
read -p "엔터를 눌러 창 닫기..."
