#!/bin/bash
# 코어 캠퍼스 long-poll 데몬 — launchd 자동시작 설치 스크립트.
#
# 사용:
#   bash launchd/install.sh         # 설치 (또는 갱신)
#   bash launchd/install.sh stop    # 정지하고 자동시작 끄기
#   bash launchd/install.sh status  # 현재 상태 확인
#   bash launchd/install.sh logs    # 로그 실시간 보기

set -e

PLIST_NAME="com.corecampus.longpoll"
PLIST_SRC="$(cd "$(dirname "$0")" && pwd)/${PLIST_NAME}.plist"
PLIST_DST="$HOME/Library/LaunchAgents/${PLIST_NAME}.plist"
LOG_DIR="$HOME/Library/Logs"

cmd="${1:-install}"

case "$cmd" in
    install)
        echo "▶ launchd plist 설치 중..."
        mkdir -p "$LOG_DIR"
        mkdir -p "$(dirname "$PLIST_DST")"

        # 기존이 있으면 먼저 unload
        if [ -f "$PLIST_DST" ]; then
            launchctl unload "$PLIST_DST" 2>/dev/null || true
            echo "  - 기존 plist unload"
        fi

        cp "$PLIST_SRC" "$PLIST_DST"
        echo "  - plist 복사: $PLIST_DST"

        launchctl load "$PLIST_DST"
        echo "  - load 완료"

        sleep 2
        if launchctl list | grep -q "$PLIST_NAME"; then
            echo "✅ 설치 완료 — 데몬 시작됨"
            echo
            echo "📋 상태 확인:    bash $0 status"
            echo "📋 로그 보기:    bash $0 logs"
            echo "📋 정지:         bash $0 stop"
        else
            echo "⚠️ load는 됐는데 launchctl list에 안 보임 — .err.log 확인 필요"
            echo "    tail $LOG_DIR/corecampus-longpoll.err.log"
        fi
        ;;

    stop|uninstall)
        if [ -f "$PLIST_DST" ]; then
            launchctl unload "$PLIST_DST" 2>/dev/null || true
            rm -f "$PLIST_DST"
            echo "✅ 정지 완료 — 자동시작 꺼짐"
        else
            echo "ℹ plist 파일이 이미 없습니다"
        fi
        ;;

    status)
        if launchctl list | grep -q "$PLIST_NAME"; then
            line=$(launchctl list | grep "$PLIST_NAME")
            echo "✅ 데몬 실행 중"
            echo "   $line"
            echo
            echo "최근 로그 (마지막 20줄):"
            echo "─────────────────────────────────────"
            tail -20 "$LOG_DIR/corecampus-longpoll.log" 2>/dev/null || echo "(로그 없음)"
        else
            echo "❌ 데몬 안 도는 중"
            if [ -f "$PLIST_DST" ]; then
                echo "   plist는 설치돼 있음 — 로드 안 됐을 수 있습니다."
                echo "   수동 로드: launchctl load $PLIST_DST"
            else
                echo "   plist 미설치 — bash $0 install"
            fi
        fi
        ;;

    logs)
        echo "▶ 로그 실시간 보기 (Ctrl+C로 종료)"
        echo "─ stdout: $LOG_DIR/corecampus-longpoll.log"
        echo "─ stderr: $LOG_DIR/corecampus-longpoll.err.log"
        echo "─────────────────────────────────────────"
        tail -f "$LOG_DIR/corecampus-longpoll.log" "$LOG_DIR/corecampus-longpoll.err.log"
        ;;

    *)
        echo "사용: $0 [install|stop|status|logs]"
        exit 1
        ;;
esac
