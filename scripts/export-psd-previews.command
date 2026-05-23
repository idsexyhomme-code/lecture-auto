#!/bin/bash
# Track A — 회원 작업물 PSD → PNG 미리보기 추출
# macOS 내장 qlmanage 사용 (Photoshop·brew 설치 불필요)
# 결과: design-system/references/raw-psd-previews/ 에 PNG 저장

PROJECT="/Users/seohyeongmin/Desktop/강의 홈페이지 제작"
DST="$PROJECT/design-system/references/raw-psd-previews"
SCAN="$PROJECT/design-system/_hdd_scan/design_files.txt"
IMG_SCAN="$PROJECT/design-system/_hdd_scan/large_images.txt"

mkdir -p "$DST"

clear
echo "======================================"
echo "  Track A — 회원 작업물 미리보기 추출"
echo "======================================"
echo ""

if [ ! -f "$SCAN" ]; then
  echo "✗ design_files.txt 없음. 먼저 scan-hdd-design.command 실행."
  read; exit 1
fi

TOTAL=0

# ───── 폴더별 PSD/AI 2~3개씩 변환 ─────
FOLDERS=(
  "몽생이 모션"
  "한국환경공단"
  "워터밤"
  "감귤박람회"
  "JTP 아카이브"
  "161212 포토샵 판넬"
  "선흘"
)

for folder in "${FOLDERS[@]}"; do
  echo "[$folder]"
  count=0
  while IFS= read -r psd; do
    [ -z "$psd" ] && continue
    [ ! -f "$psd" ] && continue
    name=$(basename "$psd")
    # qlmanage: macOS 내장 QuickLook 썸네일러 — PSD/AI 미리보기 PNG 생성
    if qlmanage -t -s 1600 -o "$DST" "$psd" >/dev/null 2>&1; then
      # 결과 파일명은 "$name.png" 형태가 됨 → 안전한 이름으로 변경
      orig_png="$DST/$name.png"
      safe_name="${folder// /_}_${count}_${name%.*}.png"
      safe_name="${safe_name// /_}"
      [ -f "$orig_png" ] && mv "$orig_png" "$DST/$safe_name"
      echo "  ✓ $safe_name"
      count=$((count + 1))
      TOTAL=$((TOTAL + 1))
    fi
    [ $count -ge 3 ] && break
  done < <(grep -F "$folder" "$SCAN" 2>/dev/null | head -10)
done

# ───── 추가: 큰 이미지 (실제 디자인 결과물) 5개 폴더별 1~2개 ─────
echo ""
echo "[추가 — 큰 이미지 (실제 결과물 PNG/JPG)]"
for folder in "몽생이" "환경공단" "워터밤" "감귤" "JTP" "선흘"; do
  count=0
  while IFS= read -r img; do
    [ -z "$img" ] && continue
    [ ! -f "$img" ] && continue
    name=$(basename "$img")
    safe_name="ref_${folder// /_}_${count}_${name}"
    cp "$img" "$DST/$safe_name" 2>/dev/null && echo "  ✓ $safe_name" && count=$((count + 1)) && TOTAL=$((TOTAL + 1))
    [ $count -ge 2 ] && break
  done < <(grep -F "$folder" "$IMG_SCAN" 2>/dev/null | grep -iE "\.(png|jpg|jpeg)$" | head -10)
done

echo ""
echo "======================================"
echo "  ✅ 완료 — 총 $TOTAL 개 미리보기 추출"
echo "======================================"
echo ""
echo "위치: $DST"
echo ""
ls -1 "$DST" | head -30
echo ""
echo "이제 Claude에게 \"PSD 추출 끝났어\" 라고 말씀하시면 분석 시작합니다."
read -p "엔터 누르면 창 닫힘..."
