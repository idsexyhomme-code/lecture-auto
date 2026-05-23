#!/bin/bash
# Track A v2 — 회원 디자인 작업물 미리보기 추출 (수정판)
# sips로 PSD 변환 시도 + 실제 결과물 PNG/JPG 적극 수집

PROJECT="/Users/seohyeongmin/Desktop/강의 홈페이지 제작"
DST="$PROJECT/design-system/references/raw-psd-previews"
IMG_SCAN="$PROJECT/design-system/_hdd_scan/large_images.txt"
PSD_SCAN="$PROJECT/design-system/_hdd_scan/design_files.txt"

mkdir -p "$DST"

clear
echo "======================================"
echo "  Track A v2 — 디자인 작업물 수집"
echo "======================================"
echo ""

TOTAL=0

# ───── 디자인 톤 학습에 좋은 폴더들 ─────
# (실제 design output JPG/PNG가 있는 폴더 위주)
DESIGN_FOLDERS=(
  "JTP 아카이브/복사_2024 상반기 주요소식"
  "JTP 아카이브/복사_제주테크노파크 창립기념일"
  "TP/2023/TP 1분기 주요소식"
  "산남새마을금고 45주년"
  "라온힐조/라온힐조 보정"
  "JCI 이임식"
  "렛츠런파크 5월/사진"
  "몽생이/몽생이 연출"
  "몽생이/몽생이 시설"
  "벨롱벨롱"
  "윈드1947"
  "방주"
  "비지터"
  "삼정물산"
)

echo "[큰 이미지 — 실제 결과물 수집]"
for folder in "${DESIGN_FOLDERS[@]}"; do
  count=0
  short=$(echo "$folder" | tr '/' '_' | tr ' ' '_')
  while IFS= read -r img; do
    [ -z "$img" ] && continue
    [ ! -f "$img" ] && continue
    # 2MB 이상 큰 이미지만 (사진 보정본 제외 — 디자인 결과물 위주)
    SIZE=$(stat -f%z "$img" 2>/dev/null || echo 0)
    [ "$SIZE" -lt 200000 ] && continue
    [ "$SIZE" -gt 5000000 ] && continue
    name=$(basename "$img")
    safe="ref_${short}_${count}_${name}"
    safe="${safe// /_}"
    cp "$img" "$DST/$safe" 2>/dev/null && echo "  ✓ $safe" && count=$((count + 1)) && TOTAL=$((TOTAL + 1))
    [ $count -ge 2 ] && break
  done < <(grep -F "$folder" "$IMG_SCAN" 2>/dev/null | grep -iE "\.(png|jpg|jpeg)$" | head -50)
done

# ───── sips로 PSD → JPG 변환 시도 ─────
echo ""
echo "[PSD → JPG sips 변환 시도]"
PSD_FOLDERS=(
  "몽생이 모션"
  "한국환경공단"
  "워터밤"
  "감귤박람회"
  "JTP 아카이브"
  "161212 포토샵 판넬"
)
for folder in "${PSD_FOLDERS[@]}"; do
  count=0
  short=$(echo "$folder" | tr ' ' '_')
  while IFS= read -r psd; do
    [ -z "$psd" ] && continue
    [ ! -f "$psd" ] && continue
    name=$(basename "$psd")
    safe="psd_${short}_${count}_${name%.*}.jpg"
    safe="${safe// /_}"
    # sips는 PSD 직접 변환 가능
    if sips -s format jpeg -s formatOptions 80 -Z 1600 "$psd" --out "$DST/$safe" >/dev/null 2>&1; then
      echo "  ✓ $safe"
      count=$((count + 1))
      TOTAL=$((TOTAL + 1))
    fi
    [ $count -ge 2 ] && break
  done < <(grep -F "$folder" "$PSD_SCAN" 2>/dev/null | grep -iE "\.psd$" | head -10)
done

echo ""
echo "======================================"
echo "  ✅ 완료 — 총 $TOTAL 개 추출"
echo "======================================"
echo ""
echo "위치: $DST"
ls -1 "$DST" | wc -l | tr -d ' ' | xargs -I{} echo "현재 폴더 파일 수: {}"
echo ""
echo "Claude에게 \"v2 추출 끝났어\" 라고 말씀하세요."
read -p "엔터 누르면 창 닫힘..."
