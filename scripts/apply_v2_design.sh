#!/bin/bash
# 1777918110-00ebf6의 V2 (비대칭 임팩트) 디자인을 site_config.json에 적용 + push.
# pending/_failed/ 정리도 함께.
set -e

cd "$(dirname "$0")/.."
echo "===== STEP 1: 데몬 정지 (lock 해제) ====="
bash launchd/install.sh stop
sleep 3
rm -f .git/index.lock .git/objects/maintenance.lock 2>/dev/null

echo ""
echo "===== STEP 2: origin에서 최신 pull (merge) ====="
git config pull.rebase false
git pull origin main --no-edit -X ours

echo ""
echo "===== STEP 3: V2 적용 (Python) ====="
python3 << 'PYEOF'
import json
from pathlib import Path

ROOT = Path('.')
TARGET_ID = "1777918110-00ebf6"
CHOSEN_VID = "v2"

pf = ROOT / "content" / "pending" / f"{TARGET_ID}.json"
if not pf.exists():
    print(f"! pending file not found: {pf}")
    raise SystemExit(1)

card = json.loads(pf.read_text(encoding="utf-8"))
meta = card.get("meta") or {}
variants = meta.get("variants") or []
chosen = next((v for v in variants if v.get("id") == CHOSEN_VID), None)
if not chosen:
    print(f"! variant {CHOSEN_VID} not found")
    raise SystemExit(1)

target = meta.get("target", "home_intro")
print(f"  target={target}, chosen={CHOSEN_VID} ({chosen.get('name')})")

# site_config.json 로드 + 갱신
cfg = json.loads(ROOT.joinpath("site_config.json").read_text(encoding="utf-8"))
slot_map = {"hero": "hero_html", "home_intro": "home_intro_html", "footer": "footer_html"}
slot = slot_map.get(target, "hero_html")
cfg[slot] = chosen.get("html") or ""
print(f"  + applied {slot} ({len(cfg[slot])} chars)")

# design_tokens merge
existing = cfg.get("design_tokens") or {}
if not isinstance(existing, dict):
    existing = {}
chosen_tokens = chosen.get("design_tokens") or {}
existing.update(chosen_tokens)
cfg["design_tokens"] = existing
print(f"  + merged {len(chosen_tokens)} design_tokens (total {len(existing)})")

ROOT.joinpath("site_config.json").write_text(
    json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8"
)

# pending → approved 이동
ap = ROOT / "content" / "approved" / f"{TARGET_ID}.json"
card["status"] = "approved"
card["meta"]["chosen_variant_id"] = CHOSEN_VID
ap.parent.mkdir(parents=True, exist_ok=True)
ap.write_text(json.dumps(card, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"  + saved to approved/{TARGET_ID}.json")

# pending 파일 삭제
try:
    pf.unlink()
    print(f"  - removed pending/{TARGET_ID}.json")
except Exception as e:
    print(f"  ! couldn't remove pending file: {e}")
PYEOF

echo ""
echo "===== STEP 4: commit + push ====="
git add -A
git -c user.name="seohyeongmin" -c user.email="idsexyhomme@gmail.com" \
    commit -m "apply: 1777918110-00ebf6 v2 (비대칭 임팩트) → home_intro_html" --allow-empty

git push origin main

echo ""
echo "===== STEP 5: 워크플로우 dispatch ====="
PAT=$(grep ^GH_PAT= .env | cut -d= -f2 | tr -d ' \n')
curl -s -o /dev/null -w "dispatch HTTP %{http_code}\n" -X POST \
     -H "Authorization: Bearer $PAT" \
     -H "Accept: application/vnd.github+json" \
     "https://api.github.com/repos/idsexyhomme-code/lecture-auto/actions/workflows/agent-loop.yml/dispatches" \
     -d '{"ref":"main"}'

echo ""
echo "===== STEP 6: 데몬 재시작 ====="
bash launchd/install.sh install

echo ""
echo "===== DONE ====="
echo "1-2분 후 https://idsexyhomme-code.github.io/lecture-auto/ 새로고침해서 확인."
echo "텔레그램에 '배포 완료' 카드도 도착해야 정상."
