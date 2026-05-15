#!/bin/bash
# 실패 40건 일괄 재발행 — 더블클릭 실행
# 전제: 먼저 login-tistory.command 더블클릭으로 세션 재캡처 완료

cd "/Users/seohyeongmin/Desktop/강의 홈페이지 제작" || exit 1
source .venv/bin/activate

echo "🎓 실패 blog_post 일괄 재발행"
echo ""
echo "1단계 — dry-run으로 대상 확인"
echo ""
python scripts/retry_failed_blog.py --dry-run
echo ""
echo "═══════════════════════════════════════════════════════════"
read -p "→ 위 대상을 *예약 분산*으로 재발행할까요? [y/N] " ans
if [[ "$ans" =~ ^[Yy]$ ]]; then
    echo ""
    echo "2단계 — 예약 분산 발행 시작"
    python scripts/retry_failed_blog.py --schedule
else
    echo "취소됨."
fi

echo ""
read -p "닫기 ▶ "
