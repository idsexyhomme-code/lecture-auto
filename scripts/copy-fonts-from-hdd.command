#!/bin/bash
# Core Campus — HDD 폰트 복사 + woff2 변환
# 사용: 더블클릭 → HDD에서 핵심 4종 폰트 자동 복사 → woff2 변환(가능하면)

set -e

PROJECT="/Users/seohyeongmin/Desktop/강의 홈페이지 제작"
RAW="$PROJECT/design-system/fonts/raw"
WOFF2="$PROJECT/design-system/fonts/woff2"
mkdir -p "$RAW" "$WOFF2"

clear
echo "======================================"
echo "  Core Campus 폰트 복사 + 변환"
echo "======================================"
echo ""

# ───── 복사 함수 ─────
copy_font() {
  local src="$1"
  local dst_name="$2"
  if [ -f "$src" ]; then
    cp "$src" "$RAW/$dst_name" 2>/dev/null && echo "  ✓ $dst_name" || echo "  ✗ $dst_name (복사 실패)"
  else
    echo "  ✗ $dst_name (파일 없음)"
  fi
}

# ───── 1. Pretendard (회원님 HDD: Regular, SemiBold만 있음) ─────
echo "[1/4] Pretendard 복사..."
PRETENDARD_DIR="/Volumes/System/SSD C드라이브/SSD C drive/Program Files (x86)/ESTsoft/ALToolsManager/font"
copy_font "$PRETENDARD_DIR/Pretendard-Regular.ttf" "Pretendard-Regular.ttf"
copy_font "$PRETENDARD_DIR/Pretendard-SemiBold.ttf" "Pretendard-SemiBold.ttf"

# HDD에 없는 웨이트는 CDN에서 다운로드 (Pretendard 공식 GitHub)
echo "  (Bold/Medium/Light는 CDN에서 받아옴)"
for weight in Bold Medium Light ExtraBold Black Thin ExtraLight; do
  curl -fsSL -o "$RAW/Pretendard-$weight.woff2" \
    "https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/packages/pretendard/dist/web/static/woff2/Pretendard-$weight.woff2" \
    && echo "  ✓ Pretendard-$weight.woff2 (CDN)" \
    || echo "  ✗ Pretendard-$weight.woff2 (CDN 실패)"
done

# Pretendard Variable (가장 효율적)
curl -fsSL -o "$RAW/PretendardVariable.woff2" \
  "https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/packages/pretendard/dist/web/variable/woff2/PretendardVariable.woff2" \
  && echo "  ✓ PretendardVariable.woff2 (가변폰트, CDN)" \
  || echo "  ✗ PretendardVariable.woff2"

# ───── 2. Noto Sans KR ─────
echo ""
echo "[2/4] Noto Sans KR 복사..."
NOTO_DIR="/Volumes/System/SSD C드라이브/SSD C drive/Program Files (x86)/Printmade3/webfont"
copy_font "$NOTO_DIR/NotoSansCJKkr-Bold.ttf" "NotoSansKR-Bold.ttf"
copy_font "$NOTO_DIR/NotoSansCJKkr-Medium.ttf" "NotoSansKR-Medium.ttf"
copy_font "$NOTO_DIR/NotoSansCJKkr-DemiLight.ttf" "NotoSansKR-DemiLight.ttf"

# ───── 3. Gmarket Sans ─────
echo ""
echo "[3/4] Gmarket Sans 복사..."
GMARKET_DIR="/Volumes/System/HDD D드라이브/다운로드"
copy_font "$GMARKET_DIR/GmarketSansTTFBold.ttf" "GmarketSans-Bold.ttf"
# Light/Medium도 같은 폴더에 있을 가능성
copy_font "$GMARKET_DIR/GmarketSansTTFMedium.ttf" "GmarketSans-Medium.ttf"
copy_font "$GMARKET_DIR/GmarketSansTTFLight.ttf" "GmarketSans-Light.ttf"

# ───── 4. Gotham (영문 프리미엄) ─────
echo ""
echo "[4/4] Gotham 복사..."
GOTHAM_DIR="/Volumes/System/SSD C드라이브/C DRIVE/Program Files/Evernote/Evernote/NodeWebKit/present/Fonts"
copy_font "$GOTHAM_DIR/Gotham-Bold.otf" "Gotham-Bold.otf"
copy_font "$GOTHAM_DIR/Gotham-Medium.otf" "Gotham-Medium.otf"
copy_font "$GOTHAM_DIR/Gotham-Book.otf" "Gotham-Book.otf"
copy_font "$GOTHAM_DIR/Gotham-Light.otf" "Gotham-Light.otf"

# ───── 5. TTF/OTF → woff2 변환 (Google woff2 도구 사용) ─────
echo ""
echo "[변환] TTF/OTF → woff2..."

# woff2 도구 확인 (brew install woff2)
if command -v woff2_compress &> /dev/null; then
  for f in "$RAW"/*.ttf "$RAW"/*.otf; do
    [ -f "$f" ] || continue
    name=$(basename "$f")
    base="${name%.*}"
    if [ ! -f "$WOFF2/$base.woff2" ]; then
      woff2_compress "$f" 2>/dev/null && mv "${f%.*}.woff2" "$WOFF2/" 2>/dev/null && echo "  ✓ $base.woff2" || echo "  ✗ $base.woff2 (변환 실패)"
    fi
  done
  # CDN으로 받은 woff2도 통합
  cp "$RAW"/*.woff2 "$WOFF2/" 2>/dev/null || true
else
  echo "  ⚠ woff2_compress 미설치 — TTF/OTF 그대로 사용."
  echo "     자가 호스팅 시 brew install woff2 추천."
  # CDN으로 받은 woff2만 이동
  cp "$RAW"/*.woff2 "$WOFF2/" 2>/dev/null || true
fi

# ───── 결과 요약 ─────
echo ""
echo "======================================"
echo "  ✅ 폰트 복사 완료"
echo "======================================"
echo ""
echo "RAW (TTF/OTF):"
ls -1 "$RAW" 2>/dev/null | sed 's/^/  /'
echo ""
echo "WOFF2 (웹용):"
ls -1 "$WOFF2" 2>/dev/null | sed 's/^/  /' | head -20
echo ""
echo "이제 Claude에게 \"폰트 복사 끝났어\" 라고 말씀하시면 다음 단계 진행합니다."
echo ""
read -p "엔터 누르면 창 닫힘..."
