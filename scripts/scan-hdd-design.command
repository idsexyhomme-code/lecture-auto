#!/bin/bash
# Core Campus — HDD 디자인 자산 스캐너
# 사용: 이 파일 더블클릭 → 자동으로 외장 HDD 전체 스캔 → 결과 design-system/_hdd_scan/ 에 저장
# 권한: 처음 실행 시 macOS가 권한 요청할 수 있음 ("터미널이 디스크에 접근하려고 합니다") → 허용

set -e

PROJECT_DIR="/Users/seohyeongmin/Desktop/강의 홈페이지 제작"
OUTPUT_DIR="$PROJECT_DIR/design-system/_hdd_scan"
mkdir -p "$OUTPUT_DIR"

MANIFEST="$OUTPUT_DIR/manifest.md"
FONTS_LIST="$OUTPUT_DIR/fonts.txt"
DESIGN_LIST="$OUTPUT_DIR/design_files.txt"
LARGE_IMG_LIST="$OUTPUT_DIR/large_images.txt"
PDF_LIST="$OUTPUT_DIR/pdfs.txt"

# ===== 시작 =====
clear
echo "======================================"
echo "  Core Campus HDD 디자인 자산 스캐너"
echo "======================================"
echo ""

# 마운트된 볼륨 (외장 디스크) 목록
echo "## 마운트된 외장 디스크:"
VOLUMES=$(ls -1 /Volumes/ 2>/dev/null | grep -v "^Macintosh HD" || true)
if [ -z "$VOLUMES" ]; then
  echo "  (내장 디스크만 있습니다. 외장 HDD가 마운트됐는지 확인하세요)"
else
  echo "$VOLUMES" | sed 's/^/  - /'
fi
echo ""

# 매니페스트 초기화
{
  echo "# Core Campus HDD 디자인 자산 스캔 결과"
  echo ""
  echo "스캔 시작: $(date '+%Y-%m-%d %H:%M:%S')"
  echo ""
  echo "## 마운트된 볼륨"
  echo ""
  echo "$VOLUMES" | sed 's/^/- /'
  echo ""
} > "$MANIFEST"

SCAN_PATHS="/Volumes"

# ===== 1. 폰트 검색 =====
echo "[1/5] 폰트 파일 스캔 중... (TTF, OTF, TTC, WOFF, WOFF2)"
find "$SCAN_PATHS" -type f \( \
  -iname "*.ttf" -o \
  -iname "*.otf" -o \
  -iname "*.ttc" -o \
  -iname "*.otc" -o \
  -iname "*.woff" -o \
  -iname "*.woff2" -o \
  -iname "*.eot" \
\) 2>/dev/null > "$FONTS_LIST" || true
FONT_COUNT=$(wc -l < "$FONTS_LIST" | tr -d ' ')
echo "      → 폰트 파일 $FONT_COUNT 개 발견"

# ===== 2. 디자인 소스 파일 =====
echo "[2/5] 디자인 소스 파일 스캔 중... (PSD, AI, Sketch, Figma, XD, INDD)"
find "$SCAN_PATHS" -type f \( \
  -iname "*.psd" -o \
  -iname "*.psb" -o \
  -iname "*.ai" -o \
  -iname "*.sketch" -o \
  -iname "*.fig" -o \
  -iname "*.xd" -o \
  -iname "*.indd" -o \
  -iname "*.idml" -o \
  -iname "*.afdesign" -o \
  -iname "*.afphoto" \
\) 2>/dev/null > "$DESIGN_LIST" || true
DESIGN_COUNT=$(wc -l < "$DESIGN_LIST" | tr -d ' ')
echo "      → 디자인 소스 $DESIGN_COUNT 개 발견"

# ===== 3. 큰 이미지 (500KB 이상 — 썸네일이 아닌 실제 디자인) =====
echo "[3/5] 큰 이미지 (500KB 이상 PNG/JPG) 스캔 중..."
find "$SCAN_PATHS" -type f \( \
  -iname "*.png" -o \
  -iname "*.jpg" -o \
  -iname "*.jpeg" -o \
  -iname "*.webp" -o \
  -iname "*.tiff" -o \
  -iname "*.heic" \
\) -size +500k 2>/dev/null | head -5000 > "$LARGE_IMG_LIST" || true
IMG_COUNT=$(wc -l < "$LARGE_IMG_LIST" | tr -d ' ')
echo "      → 큰 이미지 $IMG_COUNT 개 (최대 5000개까지)"

# ===== 4. PDF 디자인 자료 =====
echo "[4/5] PDF 자료 (5MB 이상 — 가이드·포트폴리오) 스캔 중..."
find "$SCAN_PATHS" -type f -iname "*.pdf" -size +5M 2>/dev/null | head -1000 > "$PDF_LIST" || true
PDF_COUNT=$(wc -l < "$PDF_LIST" | tr -d ' ')
echo "      → 큰 PDF $PDF_COUNT 개"

# ===== 5. 폴더별 요약 (어디에 자산이 몰려있는지) =====
echo "[5/5] 요약 생성 중..."

{
  echo "## 폰트 분포 — TOP 50 폴더"
  echo ""
  echo "\`\`\`"
  sort "$FONTS_LIST" | awk -F'/' '{NF--; print}' OFS='/' | sort | uniq -c | sort -rn | head -50
  echo "\`\`\`"
  echo ""

  echo "## 폰트 — 한글 이름 추정 (파일명에 한글 또는 'kor', 'kr', 'hangul', 'pretendard', 'nanum', 'noto' 등 포함)"
  echo ""
  echo "\`\`\`"
  grep -iE "(한글|kor|hangul|nanum|noto.*kr|noto.*korean|pretendard|spoqa|suit|paperlogy|cafe24|black.*han|nanum|jeju|gowun|gmarket|cookierun|leeseoyun|tway|kopub|kbiz|sandol|tmoney|tossface|이순신|배달의민족|삼성|네이버|봄|봄봄|꽃|굴림|돋움|바탕|궁서|맑은|함초롬|솔내체|순바탕|크릭스|타이포|동아|조선)" "$FONTS_LIST" 2>/dev/null | head -200
  echo "\`\`\`"
  echo ""

  echo "## 폰트 — 영문 프리미엄 추정 (파일명에 'pro', 'display', 'variable', 'inter', 'sf', 'helvetica', 'futura', 'didot', 'bodoni', 'gotham', 'avenir', 'futura', 'minion' 등)"
  echo ""
  echo "\`\`\`"
  grep -iE "(inter|helvetica|futura|didot|bodoni|gotham|avenir|minion|garamond|baskerville|caslon|geometric|neue|grotesque|monaco|menlo|fira|jetbrains|sf.?pro|sf.?mono|sf.?display|brandon|montserrat|playfair|merriweather|raleway|oswald|lato|barlow|manrope|poppins|nunito|recoleta|sohne|tiempos|saol|moderat|graphik|maison|founders|halyard|signifier|reckless|surt)" "$FONTS_LIST" 2>/dev/null | head -200
  echo "\`\`\`"
  echo ""

  echo "## 디자인 소스 — 폴더별 분포"
  echo ""
  echo "\`\`\`"
  sort "$DESIGN_LIST" | awk -F'/' '{NF--; print}' OFS='/' | sort | uniq -c | sort -rn | head -50
  echo "\`\`\`"
  echo ""

  echo "## 디자인 소스 — 랜딩·상세페이지 추정 (파일명에 'landing', '상세', '랜딩', 'detail', 'lp', 'mainpage', '메인', '홈페이지' 포함)"
  echo ""
  echo "\`\`\`"
  grep -iE "(landing|랜딩|상세|detail|lp|mainpage|메인|홈페이지|쇼핑몰|product|상품)" "$DESIGN_LIST" 2>/dev/null | head -200
  echo "\`\`\`"
  echo ""

  echo "## 큰 이미지 — 폴더별 TOP 50 (디자인 참고 후보)"
  echo ""
  echo "\`\`\`"
  sort "$LARGE_IMG_LIST" | awk -F'/' '{NF--; print}' OFS='/' | sort | uniq -c | sort -rn | head -50
  echo "\`\`\`"
  echo ""

  echo "## PDF — 디자인·브랜드 가이드 추정"
  echo ""
  echo "\`\`\`"
  grep -iE "(brand|guide|guideline|design|디자인|브랜드|가이드|매뉴얼|포트폴리오|portfolio|book)" "$PDF_LIST" 2>/dev/null | head -100
  echo "\`\`\`"
  echo ""

  echo "## 통계 요약"
  echo ""
  echo "| 카테고리 | 개수 |"
  echo "|---|---|"
  echo "| 폰트 파일 | $FONT_COUNT |"
  echo "| 디자인 소스 (PSD·AI·Sketch·Figma·XD·INDD) | $DESIGN_COUNT |"
  echo "| 큰 이미지 (500KB+) | $IMG_COUNT |"
  echo "| 큰 PDF (5MB+) | $PDF_COUNT |"
  echo ""

  echo "---"
  echo ""
  echo "스캔 완료: $(date '+%Y-%m-%d %H:%M:%S')"
} >> "$MANIFEST"

# ===== 출력 =====
echo ""
echo "======================================"
echo "  ✅ 스캔 완료!"
echo "======================================"
echo ""
echo "결과 위치:"
echo "  $OUTPUT_DIR"
echo ""
echo "파일:"
echo "  manifest.md          — 요약 (Claude가 읽음)"
echo "  fonts.txt            — 폰트 전체 경로 $FONT_COUNT 줄"
echo "  design_files.txt     — 디자인 소스 $DESIGN_COUNT 줄"
echo "  large_images.txt     — 큰 이미지 $IMG_COUNT 줄"
echo "  pdfs.txt             — 큰 PDF $PDF_COUNT 줄"
echo ""
echo "이제 Claude에게 \"스캔 결과 확인해줘\" 라고 말씀하시면"
echo "manifest.md를 읽고 design-system 구축 계획을 짭니다."
echo ""

# Terminal 창 자동 닫지 않음 — 결과 확인용
read -p "엔터를 누르면 창이 닫힙니다..."
