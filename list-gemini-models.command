#!/bin/bash
# 🔍 Gemini API — 회원 계정에서 실제 사용 가능한 모델 목록 확인
# 이미지 생성 가능 모델을 찾을 때 사용

PROJECT="/Users/seohyeongmin/Desktop/강의 홈페이지 제작"
cd "$PROJECT" || exit 1

echo "════════════════════════════════════════════════════════════"
echo "  🔍 Gemini 사용 가능 모델 목록"
echo "════════════════════════════════════════════════════════════"
echo ""

set -a; [ -f .env ] && source .env; set +a

if [ -z "$GOOGLE_GENERATIVEAI_API_KEY" ]; then
    echo "  ❌ GOOGLE_GENERATIVEAI_API_KEY 미설정 (.env 확인)"
    read -p "  엔터로 닫기..."
    exit 1
fi

echo "  ── 전체 모델 목록 조회 중..."
echo ""

curl -s "https://generativelanguage.googleapis.com/v1beta/models?key=${GOOGLE_GENERATIVEAI_API_KEY}&pageSize=100" \
| python3 -c '
import json, sys
data = json.load(sys.stdin)
models = data.get("models", [])
print(f"  총 {len(models)}개 모델 발견.\n")
print("  ── 이미지 생성 지원 모델 (generateContent + responseModalities) ──\n")
image_capable = []
for m in models:
    name = m.get("name", "").replace("models/", "")
    methods = m.get("supportedGenerationMethods", [])
    if "generateContent" not in methods:
        continue
    # 이미지 관련 모델은 보통 이름에 image/imagen 포함
    if any(k in name.lower() for k in ["image", "imagen", "flash-image", "vision"]):
        image_capable.append(name)
        display_name = m.get("displayName", "")
        print(f"  ✓ {name}")
        if display_name:
            print(f"      → {display_name}")
        print()

print()
print("  ── 전체 generateContent 지원 모델 ──\n")
for m in models:
    name = m.get("name", "").replace("models/", "")
    methods = m.get("supportedGenerationMethods", [])
    if "generateContent" in methods:
        print(f"  • {name}")

if image_capable:
    best = image_capable[0]
    print()
    print(f"  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"  💡 추천 — .env에 다음 줄 추가하면 이 모델 사용:")
    print(f"     GEMINI_IMAGE_MODEL={best}")
    print(f"  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
else:
    print()
    print("  ⚠️ 이미지 생성 지원 모델 없음 — API 키 권한 확인 필요")
'

echo ""
read -p "엔터로 닫기..."
