#!/bin/bash
# 🎨 블로그 메인 이미지 — 고품질 샘플 생성 (OpenAI gpt-image-1, quality=high)
# 더블클릭하면 데스크톱에 PNG 저장 + macOS Preview 자동 열기

PROJECT="/Users/seohyeongmin/Desktop/강의 홈페이지 제작"
cd "$PROJECT" || { echo "프로젝트 폴더 못 찾음"; exit 1; }

echo "════════════════════════════════════════════════════════════"
echo "  🎨 Core Campus — 블로그 이미지 HQ 테스트"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "  백엔드: ${BLOG_IMAGE_MODEL:-gemini (나노바나나)}"
echo "  품질: high"
echo "  사이즈: 1536x1024 (OpenAI) / 1024x1024 (Gemini 기본)"
echo ""

# .venv 우선 사용
if [ -x ".venv/bin/python3" ]; then
    PY=".venv/bin/python3"
elif [ -x ".venv/bin/python" ]; then
    PY=".venv/bin/python"
else
    PY="python3"
fi

# 필요 패키지 확인 (gemini는 requests만 필요, openai는 openai SDK)
"$PY" -c "import requests" 2>/dev/null || {
    "$PY" -m pip install --quiet requests 2>&1 | tail -2
}
if [ "${BLOG_IMAGE_MODEL:-gemini}" = "openai" ]; then
    "$PY" -c "import openai" 2>/dev/null || {
        echo "  ⚙️  openai SDK 설치 중..."
        "$PY" -m pip install --quiet openai 2>&1 | tail -3
    }
fi

# .env 로드
set -a
[ -f .env ] && source .env
set +a

BACKEND="${BLOG_IMAGE_MODEL:-gemini}"
if [ "$BACKEND" = "gemini" ] && [ -z "$GOOGLE_GENERATIVEAI_API_KEY" ]; then
    echo "  ❌ GOOGLE_GENERATIVEAI_API_KEY 미설정 (.env 확인)"
    read -p "  엔터로 닫기..."
    exit 1
fi
if [ "$BACKEND" = "openai" ] && [ -z "$OPENAI_API_KEY" ]; then
    echo "  ❌ OPENAI_API_KEY 미설정 (.env 확인)"
    read -p "  엔터로 닫기..."
    exit 1
fi

echo "  ── 이미지 생성 중 (10~20초 소요)..."
echo ""

OUT="$HOME/Desktop/core-campus-blog-image-hq-$(date +%Y%m%d-%H%M%S).png"

"$PY" <<PYEOF
import os, sys, base64
sys.path.insert(0, ".")
from agents.image_gen import generate_blog_image

prompt = (
    "Editorial magazine-style cover image for a Korean online learning platform 'Core Campus'. "
    "Theme: '이메일 30통, 5분 안에 정리하기' (organizing 30 emails in 5 minutes). "
    "Warm beige and deep brown palette (#F5EFE0, #3A2E25). "
    "Minimalist editorial composition. "
    "Soft natural lighting from upper-left, subtle film grain. "
    "Abstract visual metaphor: a clean wooden desk surface with a steaming ceramic mug, "
    "a stack of neatly organized paper letters, and a softly-glowing laptop screen — all arranged with negative space. "
    "Photo-realistic, 4K quality, shallow depth of field. "
    "Sophisticated yet approachable. "
    "No Korean text in image, no logos, no faces. "
    "Aesthetic similar to magazine covers like Kinfolk or Cereal — intellectual, calm, breathable."
)

import shutil
path, url = generate_blog_image(
    prompt=prompt,
    slug="hq-test",
    size="1536x1024",
    quality="high",
)
target = "$OUT"
shutil.copy(str(path), target)
print(f"✓ 저장 완료: {target}")
print(f"✓ 파일 크기: {os.path.getsize(target):,} bytes")
PYEOF

RC=$?
echo ""

if [ $RC -eq 0 ] && [ -f "$OUT" ]; then
    echo "════════════════════════════════════════════════════════════"
    echo "  ✓ 이미지 생성 완료"
    echo "  📁 위치: $OUT"
    echo "════════════════════════════════════════════════════════════"
    echo ""
    echo "  → Preview에서 자동 열기..."
    open "$OUT"
    echo ""
    echo "  품질 검토 후 다음 중 1개 알려주세요:"
    echo "  ① 만족 — blog_publisher 기본값을 high로 변경하면 끝"
    echo "  ② 더 좋게 — Gemini 2.5 Flash Image(나노바나나)로 추가 테스트"
    echo "  ③ 다른 스타일 — 프롬프트 방향 바꿔서 재생성"
else
    echo "❌ 이미지 생성 실패 (exit=$RC)"
    echo "   OpenAI API 키 또는 네트워크 점검 필요"
fi

echo ""
read -p "엔터로 닫기..."
