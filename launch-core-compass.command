#!/bin/bash
# Core Compass D-day 출시 명령어 — 더블클릭 → 모든 점검 자동
PROJECT="/Users/seohyeongmin/Desktop/강의 홈페이지 제작"
cd "$PROJECT"

echo "======================================"
echo "  Core Compass 출시 D-day 점검"
echo "======================================"
echo ""

# 1. .env 키 점검
echo "[1/6] .env 키 점검..."
for KEY in PAYAPP_SHOP_ID PAYAPP_LINK_KEY PAYAPP_LINK_VAL RESEND_API_KEY ANTHROPIC_API_KEY TELEGRAM_BOT_TOKEN; do
  if grep -qE "^$KEY=." .env 2>/dev/null; then
    echo "  ✓ $KEY"
  else
    echo "  ✗ $KEY 누락"
  fi
done

# 2. v4 페이지 로드 확인
echo ""
echo "[2/6] v4 페이지 검수..."
python3 -c "
import sys, re
sys.path.insert(0, '.')
from agents.base import BaseAgent
from pathlib import Path
ok = True
for p in sorted(Path('site/landing/core-compass/v4').glob('*.html')):
    html = p.read_text()
    text = re.sub(r'<style.*?</style>', '', html, flags=re.S)
    text = re.sub(r'<script.*?</script>', '', text, flags=re.S)
    text = re.sub(r'<[^>]+>', ' ', text)
    r = BaseAgent.self_review(text, kind='copy')
    if r['hard_violations']:
        print(f'  ✗ {p.name}: HARD ban!')
        ok = False
    else:
        print(f'  ✓ {p.name}')
sys.exit(0 if ok else 1)
"

# 3. 결제 라우터 dry-run
echo ""
echo "[3/6] 결제 라우터 dry-run..."
python3 -c "
import sys; sys.path.insert(0, '.')
from scripts.payment_router import route_payment
r = route_payment(product_id='core-compass', amount=9900, email='dryrun@test.com')
if r['ok']:
    print(f'  ✓ Core Compass 라우터 OK ({r[\"extra\"][\"pg\"]})')
else:
    print(f'  ⚠ 라우터: {r.get(\"error\", \"unknown\")} — PG 키 입력 필요')
"

# 4. 토큰 시스템 테스트
echo ""
echo "[4/6] 토큰 시스템 테스트..."
python3 -c "
import sys; sys.path.insert(0, '.')
from scripts.compass_token import generate_token, verify_token
t = generate_token(order_id='dryrun', email='test@test.com')
v = verify_token(t['token'])
if v: print('  ✓ 토큰 발급·검증 OK')
"

# 5. 진단 생성 dry-run
echo ""
echo "[5/6] 진단 생성 dry-run..."
python3 -c "
import sys; sys.path.insert(0, '.')
from scripts.generate_diagnosis import generate_full_diagnosis
r = generate_full_diagnosis(order_id='dryrun', email='test@test.com', user_name='테스트')
if r['ok']:
    print(f'  ✓ 진단 생성 OK ({r[\"user_persona\"]})')
"

# 6. 대시보드 헬스
echo ""
echo "[6/6] KPI·대시보드 헬스..."
python3 -c "
import sys; sys.path.insert(0, '.')
from scripts.collect_kpi import collect
snap = collect()
print(f'  ✓ KPI 수집 OK (courses={snap.get(\"courses_total\")} blog_today={snap.get(\"blog_published_today\")})')
"

echo ""
echo "======================================"
echo "  점검 완료"
echo "======================================"
echo ""
echo "출시 권장 순서:"
echo "  1. SNS 인스타·페북·X 동시 발행 (오전 9시)"
echo "  2. 블로그 글 발행 — site/blog-drafts/core-compass-launch/"
echo "  3. 이메일 발송 — 구독자 있다면 (오전 10시)"
echo "  4. 카톡 친구·지인 메시지 (오후)"
echo "  5. 텔레그램 알림 활성 — 실시간 결제 모니터"
echo ""
read -p "엔터 누르면 창 닫힘..."
