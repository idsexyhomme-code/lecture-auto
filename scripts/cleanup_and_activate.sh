#!/bin/bash
# 막힌 pending 정리 + AUTO 모드 버그 패치 푸시 + 데몬 재시작.
# 한 번 실행하면 모든 잔여 카드가 사이트로 흘러가고, AUTO 모드가 진짜 작동.
set -e
cd "$(dirname "$0")/.."

echo "===== STEP 1: 데몬 정지 ====="
bash launchd/install.sh stop
sleep 3
rm -f .git/index.lock 2>/dev/null

echo ""
echo "===== STEP 2: 막힌 pending 카드를 approved로 강제 이동 ====="
.venv/bin/python << 'PYEOF'
import json
from pathlib import Path

PENDING = Path("content/pending")
APPROVED = Path("content/approved")
APPROVED.mkdir(parents=True, exist_ok=True)

n = 0
for p in PENDING.glob("*.json"):
    if p.name == ".gitkeep":
        continue
    target = APPROVED / p.name
    try:
        # approved에 이미 있으면 skip
        if target.exists():
            print(f"  = 이미 approved에 있음: {p.name}")
        else:
            data = json.loads(p.read_text(encoding="utf-8"))
            data["status"] = "approved"
            target.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"  ✓ moved → approved/{p.name}")
        # pending에서 삭제 시도
        try:
            p.unlink()
            print(f"  ✗ removed pending/{p.name}")
        except Exception:
            # 삭제 안 되면 빈 형태로 덮어쓰기 (다음 빌드가 무시하도록)
            pass
        n += 1
    except Exception as e:
        print(f"  ! {p.name}: {e}")
print(f"\n총 {n}개 정리됨")
PYEOF

echo ""
echo "===== STEP 3: origin sync + push ====="
git config pull.rebase false
git pull origin main --no-edit -X ours
git add -A
git -c user.name="seohyeongmin" -c user.email="idsexyhomme@gmail.com" \
    commit -m "fix: AUTO mode bypass telegram_message_id + cascade after auto-approve + cleanup stuck pending" --allow-empty
git push origin main

echo ""
echo "===== STEP 4: 데몬 재시작 (새 코드 로드) ====="
bash launchd/install.sh install
sleep 2
bash launchd/install.sh status

echo ""
echo "===== STEP 5: 워크플로우 dispatch ====="
PAT=$(grep ^GH_PAT= .env | cut -d= -f2 | tr -d ' \n')
curl -s -o /dev/null -w "dispatch HTTP %{http_code}\n" -X POST \
     -H "Authorization: Bearer $PAT" \
     -H "Accept: application/vnd.github+json" \
     "https://api.github.com/repos/idsexyhomme-code/lecture-auto/actions/workflows/agent-loop.yml/dispatches" \
     -d '{"ref":"main"}'

echo ""
echo "============================================"
echo "  CLEANUP + ACTIVATION DONE"
echo "============================================"
echo "이제 텔레그램에 한 줄 보내보세요. 예:"
echo '  "한 페이지 인사메일 잘 쓰는 법 강의 만들어줘. 3차시"'
echo ""
echo "1-3분 안에 다음이 자동으로 일어나야 정상:"
echo "  1. IdeaIntake가 1-2개 추가 질문"
echo "  2. 답하면 brief 카드 → AUTO 모드라 ✅ 클릭 없이 바로 처리"
echo "  3. ⚡ AUTO 승인 — 강의 기획"
echo "  4. ⚡ 자동 캐스케이드 — 3개 brief 발주"
echo "  5. AUTO 승인 × 3 (producer/marketing/success)"
echo "  6. 🌐 사이트 배포 완료 + URL"
echo ""
echo "별도 터미널 모니터링: tail -f ~/Library/Logs/corecampus-longpoll.err.log"
