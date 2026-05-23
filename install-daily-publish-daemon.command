#!/bin/bash
# 🌙 매일 새벽 3시 자동 티스토리 발행 데몬 — 1회 설치

PROJECT="/Users/seohyeongmin/Desktop/강의 홈페이지 제작"
cd "$PROJECT" || exit 1

PLIST="com.corecampus.daily-tistory-publish.plist"
DST="$HOME/Library/LaunchAgents/$PLIST"
SH="scripts/daily-tistory-publish.sh"

echo "════════════════════════════════════════════════════════════"
echo "  🌙 매일 새벽 3시 자동 티스토리 발행 데몬 설치"
echo "════════════════════════════════════════════════════════════"
echo ""

# 1. 셸 스크립트 실행 권한
chmod +x "$SH" 2>/dev/null
echo "  ✓ scripts/daily-tistory-publish.sh — 실행 권한 적용"

# 2. plist를 LaunchAgents로 복사
mkdir -p "$HOME/Library/LaunchAgents"
cp "$PLIST" "$DST"
echo "  ✓ plist 복사: $DST"

# 3. 기존 등록 해제 (이미 있을 경우)
launchctl unload "$DST" 2>/dev/null

# 4. 새로 등록
launchctl load "$DST" 2>&1 | sed 's/^/    /'
echo ""

# 5. 등록 확인
if launchctl list | grep -q "com.corecampus.daily-tistory-publish"; then
    echo "  ✅ 데몬 등록 성공"
    echo ""
    echo "  📅 다음 실행: 내일 새벽 03:00 KST"
    echo "  📋 로그: ~/Library/Logs/corecampus-daily-publish.log"
    echo "  📨 결과: 텔레그램 카드로 자동 발송"
    echo ""
    echo "  ── 동작 ──"
    echo "  1. 매일 새벽 3시 자동 실행"
    echo "  2. content/approved 의 미발행 blog_post 최대 15건 발행"
    echo "  3. 티스토리 한도 도달 시 즉시 중단, 다음날 재개"
    echo "  4. 결과 텔레그램 카드로 알림"
else
    echo "  ❌ 데몬 등록 실패 — launchctl 로그 확인 필요"
fi

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  💡 즉시 테스트 실행 (선택)"
echo "  지금 1번 돌려보려면 다음 명령:"
echo "  launchctl start com.corecampus.daily-tistory-publish"
echo "════════════════════════════════════════════════════════════"
echo ""
read -p "엔터로 닫기..."
