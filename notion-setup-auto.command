#!/bin/bash
# 🌳 Notion 셋업 자동화 — 토큰 1개만 입력하면 나머지 자동
# 더블클릭으로 실행

PROJECT="/Users/seohyeongmin/Desktop/강의 홈페이지 제작"
cd "$PROJECT"

echo "════════════════════════════════════════════════════════════"
echo "  🌳 Notion 셋업 자동화"
echo "════════════════════════════════════════════════════════════"
echo ""

# 패키지 확인
python3 -c "import requests, dotenv" 2>/dev/null || {
    echo "  ⚙️  패키지 설치 중..."
    pip3 install --quiet requests python-dotenv 2>&1 | tail -2
}

# NOTION_TOKEN 확인 — ntn_ (신 형식 2024+) 또는 secret_ (옛 형식) 둘 다 허용
if ! grep -qE "^NOTION_TOKEN=(secret_|ntn_)" .env 2>/dev/null; then
    echo "  ❌ NOTION_TOKEN 미설정"
    echo ""
    echo "  📋 토큰 입력 가이드:"
    echo "  1. https://www.notion.so/my-integrations 에서 Integration 만들기 (이름: Core Campus)"
    echo "  2. Internal Integration Token 복사"
    echo "     - 신 형식 (2024+): ntn_xxxxx... (50자)"
    echo "     - 옛 형식: secret_xxxxx... (43자)"
    echo "     둘 다 정상 작동"
    echo "  3. 토큰을 여기에 붙여넣으세요:"
    echo ""
    read -p "  NOTION_TOKEN: " TOKEN

    if [[ -z "$TOKEN" ]] || [[ ! "$TOKEN" =~ ^(secret_|ntn_) ]]; then
        echo ""
        echo "  ❌ 유효하지 않은 토큰 형식. 'ntn_' 또는 'secret_'로 시작해야 합니다."
        echo "  종료. 다시 시도해주세요."
        read -p "  엔터로 닫기..."
        exit 1
    fi

    # .env에 추가 또는 갱신
    if grep -q "^NOTION_TOKEN=" .env 2>/dev/null; then
        # macOS sed
        sed -i.bak "s|^NOTION_TOKEN=.*|NOTION_TOKEN=$TOKEN|" .env
        rm -f .env.bak
    else
        echo "NOTION_TOKEN=$TOKEN" >> .env
    fi
    echo ""
    echo "  ✓ .env에 NOTION_TOKEN 저장됨"
    echo ""
fi

# 자동 셋업 실행
python3 scripts/notion_setup_auto.py

echo ""
echo "════════════════════════════════════════════════════════════"
echo ""
read -p "  엔터를 눌러 창 닫기..."
