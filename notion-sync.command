#!/bin/bash
# 🌳 Core Campus 산출물 → Notion 자동 동기화
# 더블클릭으로 실행

PROJECT="/Users/seohyeongmin/Desktop/강의 홈페이지 제작"
cd "$PROJECT"

echo "════════════════════════════════════════════════════════════"
echo "  🌳 Core Campus — Notion 산출물 동기화"
echo "════════════════════════════════════════════════════════════"
echo ""

# 패키지 확인
python3 -c "import requests, dotenv" 2>/dev/null || {
    echo "  ⚙️  패키지 설치 중..."
    pip3 install --quiet requests python-dotenv 2>&1 | tail -2
}

# .env 환경변수 확인 — ntn_ (신 형식) 또는 secret_ (옛 형식) 둘 다 허용
if ! grep -qE "^NOTION_TOKEN=(secret_|ntn_)" .env 2>/dev/null; then
    echo "❌ NOTION_TOKEN 미설정"
    echo ""
    echo "📋 셋업 가이드 (5분):"
    echo "  1. https://www.notion.so/my-integrations 접속"
    echo "  2. + New integration → Name 'Core Campus' → Submit"
    echo "  3. Internal Integration Token 복사 (secret_xxx... 형태)"
    echo "  4. .env 파일 열어서 아래 줄 추가:"
    echo "       NOTION_TOKEN=secret_여기에_복사"
    echo ""
    echo "  5. Notion에서 부모 페이지 만들기 (예: 'Core Campus')"
    echo "  6. 페이지 우상단 ⋯ → Add connections → Core Campus 선택"
    echo "  7. 페이지 URL에서 마지막 32자(하이픈 빼고)가 ID"
    echo "       예: notion.so/My-Page-abc123def... → ID는 'abc123def...'"
    echo "  8. .env에 아래 줄 추가:"
    echo "       NOTION_PARENT_PAGE_ID=여기에_32자_ID"
    echo ""
    echo "  9. 이 .command 다시 더블클릭"
    echo ""
    read -p "엔터로 닫기..."
    exit 1
fi

# 첫 실행인지 확인
if [ ! -f "content/state/notion_database_id.txt" ]; then
    echo "  🆕 첫 실행 — 데이터베이스 자동 생성합니다..."
    echo ""
fi

# 동기화 옵션 선택
echo "  무엇을 동기화할까요?"
echo "    1) approved + pending (기본, 추천)"
echo "    2) approved만 (이미 승인된 산출물만)"
echo "    3) pending만 (검토 대기 산출물)"
echo "    4) 모두 (approved + pending + rejected)"
echo "    s) Setup만 (DB 생성하고 종료)"
echo ""
read -p "  선택 [1]: " choice
choice="${choice:-1}"

case "$choice" in
    1) ARGS="" ;;
    2) ARGS="--approved" ;;
    3) ARGS="--pending" ;;
    4) ARGS="--all" ;;
    s|S) ARGS="--setup" ;;
    *) ARGS="" ;;
esac

# 동기화 실행
python3 scripts/notion_sync.py $ARGS

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  📱 다음 단계:"
echo "  1. 핸드폰 Notion 앱 켜기"
echo "  2. 'Core Campus 산출물' 페이지 찾기"
echo "  3. 어디서나 산출물 검색·필터·확인"
echo "════════════════════════════════════════════════════════════"
echo ""
read -p "  엔터를 눌러 창 닫기..."
