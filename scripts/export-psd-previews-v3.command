#!/bin/bash
# Track A v3 — Python 기반 (NFC↔NFD 정규화 처리)
# macOS 파일시스템 한글 분리형(NFD) 버그 해결

PROJECT="/Users/seohyeongmin/Desktop/강의 홈페이지 제작"

clear
echo "======================================"
echo "  Track A v3 — Python NFD 처리"
echo "======================================"
echo ""

python3 <<'PYEOF'
import os, shutil, subprocess, unicodedata, sys
from pathlib import Path

PROJECT = Path('/Users/seohyeongmin/Desktop/강의 홈페이지 제작')
DST = PROJECT / 'design-system/references/raw-psd-previews'
IMG_SCAN = PROJECT / 'design-system/_hdd_scan/large_images.txt'
PSD_SCAN = PROJECT / 'design-system/_hdd_scan/design_files.txt'

DST.mkdir(parents=True, exist_ok=True)

def nfd(s):
    return unicodedata.normalize('NFD', s)

def safe_name(s):
    return s.replace(' ', '_').replace('/', '_')

# ── 디자인 톤 학습에 좋은 폴더 (NFD 자동 변환됨) ──
DESIGN_FOLDERS = [
    'JTP 아카이브',
    '산남새마을금고',
    '라온힐조',
    'JCI 이임식',
    '렛츠런파크',
    '몽생이 연출',
    '몽생이 시설',
    '벨롱벨롱',
    '윈드1947',
    '방주',
    '비지터',
    '삼정물산',
    '백혈병행사',
    '미주몰',
    '붉바리',
]

PSD_FOLDERS = [
    '몽생이 모션',
    '한국환경공단',
    '워터밤',
    '감귤박람회',
    '161212 포토샵 판넬',
]

print('[큰 이미지 — 실제 결과물 수집]')
total = 0

# 매니페스트 읽기
img_lines = [l.strip() for l in open(IMG_SCAN) if l.strip()]
psd_lines = [l.strip() for l in open(PSD_SCAN) if l.strip()]

for folder in DESIGN_FOLDERS:
    folder_nfd = nfd(folder)
    matches = [l for l in img_lines if folder_nfd in l and l.lower().endswith(('.jpg', '.jpeg', '.png'))]
    if not matches:
        continue
    count = 0
    for path in matches[:50]:
        if not os.path.isfile(path):
            continue
        try:
            size = os.path.getsize(path)
        except:
            continue
        # 200KB ~ 5MB 사이만 (디자인 결과물 사이즈)
        if size < 200_000 or size > 5_000_000:
            continue
        name = os.path.basename(path)
        safe = f'ref_{safe_name(folder)}_{count}_{safe_name(name)}'
        dst_path = DST / safe
        try:
            shutil.copy(path, dst_path)
            print(f'  ✓ {safe}')
            count += 1
            total += 1
        except Exception as e:
            print(f'  ✗ {safe}: {e}')
        if count >= 2:
            break

print()
print('[PSD → JPG sips 변환]')

for folder in PSD_FOLDERS:
    folder_nfd = nfd(folder)
    matches = [l for l in psd_lines if folder_nfd in l and l.lower().endswith('.psd')]
    if not matches:
        continue
    count = 0
    for path in matches[:10]:
        if not os.path.isfile(path):
            continue
        name = os.path.basename(path)
        base = os.path.splitext(name)[0]
        safe = f'psd_{safe_name(folder)}_{count}_{safe_name(base)}.jpg'
        dst_path = DST / safe
        try:
            result = subprocess.run([
                'sips', '-s', 'format', 'jpeg', '-s', 'formatOptions', '80',
                '-Z', '1600', path, '--out', str(dst_path)
            ], capture_output=True, timeout=30)
            if result.returncode == 0 and dst_path.exists():
                print(f'  ✓ {safe}')
                count += 1
                total += 1
            else:
                pass  # 조용히 실패 (CMYK 등)
        except Exception as e:
            print(f'  ✗ {safe}: {e}')
        if count >= 2:
            break

print()
print('='*40)
print(f'  ✅ 완료 — 총 {total}개 추출')
print('='*40)
print()
print(f'위치: {DST}')
print(f'현재 파일 수: {len(list(DST.iterdir()))}')
PYEOF

echo ""
echo "Claude에게 \"v3 추출 끝났어\" 라고 말씀하세요."
read -p "엔터 누르면 창 닫힘..."
