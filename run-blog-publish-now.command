#!/bin/bash
# 🚀 즉시 블로그 발행 — 데몬 우회, briefs/blog-publish-*.json 1건 직접 처리

PROJECT="/Users/seohyeongmin/Desktop/강의 홈페이지 제작"
cd "$PROJECT" || { echo "프로젝트 폴더 못 찾음"; exit 1; }

echo "════════════════════════════════════════════════════════════"
echo "  🚀 즉시 블로그 발행 (데몬 우회)"
echo "════════════════════════════════════════════════════════════"
echo ""

# .env 로드
set -a; [ -f .env ] && source .env; set +a

PY=".venv/bin/python3"
[ -x "$PY" ] || PY="python3"
echo "  Python: $PY"

# brief 찾기
BRIEF=$(ls briefs/blog-publish-*.json 2>/dev/null | head -1)
if [ -z "$BRIEF" ]; then
    echo "  ❌ briefs/blog-publish-*.json 없음"
    echo "     이미 처리됐거나 큐가 비어 있음"
    read -p "  엔터로 닫기..."
    exit 1
fi

echo "  처리 대상: $(basename "$BRIEF")"
echo ""
echo "  ── 1단계: brief 로드"

COURSE_ID=$("$PY" -c "import json; print(json.load(open('$BRIEF'))['brief'].get('course_id', 'unknown'))")
COURSE_TITLE=$("$PY" -c "import json; print(json.load(open('$BRIEF'))['brief'].get('course_title', ''))")
echo "    코스: $COURSE_ID — $COURSE_TITLE"
echo ""

# 환경변수 강제 — 이번 실행에 대해서만 즉시 발행
export TISTORY_SKIP=false
export TISTORY_SCHEDULE=0
export TISTORY_BLOG=${TISTORY_BLOG:-jejumomdad}
export BLOG_IMAGE_MODEL=${BLOG_IMAGE_MODEL:-gemini}
export TISTORY_HEADLESS=0  # 헤드리스 끄기 — 안정성 우선

echo "  ── 2단계: 글 작성 + Gemini 이미지 + 티스토리 발행 (3~10분 소요)"
echo ""

"$PY" <<PYEOF
import sys, json, traceback
sys.path.insert(0, '.')

try:
    from agents.blog_publisher import BlogPublisher
except Exception as e:
    print(f"❌ BlogPublisher import 실패: {e}")
    traceback.print_exc()
    sys.exit(1)

brief_path = "$BRIEF"
brief_full = json.load(open(brief_path))
brief = brief_full['brief']

print(f"  📝 brief 로드 완료: {brief.get('course_id')}")
print()

agent = BlogPublisher()
try:
    results = agent.run(brief)
except Exception as e:
    print(f"❌ blog_publisher 실행 실패: {e}")
    traceback.print_exc()
    sys.exit(1)

if not results:
    print("❌ 결과 0건 — 글 생성 실패 가능성")
    sys.exit(1)

for r in results:
    print(f"\n  ✓ 산출물 ID: {r.id}")
    print(f"    Kind: {r.kind}")
    print(f"    Title: {r.title}")
    if r.meta:
        url = r.meta.get('published_url') or r.meta.get('url')
        if url:
            print(f"    🔗 URL: {url}")
        sr = r.meta.get('self_review')
        if sr:
            print(f"    Self-review: {sr.get('result', '?')}")

    # brief 파일을 _processed로 이동
    import shutil, os
    proc_dir = "briefs/_processed"
    os.makedirs(proc_dir, exist_ok=True)
    try:
        shutil.move(brief_path, os.path.join(proc_dir, os.path.basename(brief_path)))
        print(f"    ✓ brief → _processed/ 이동")
    except Exception:
        pass

print()
print("════════════════════════════════════════════════════════════")
print("  ✓ 완료 — jejumomdad.tistory.com 확인")
print("════════════════════════════════════════════════════════════")
PYEOF

RC=$?
echo ""
if [ $RC -eq 0 ]; then
    echo "  💡 다음 brief도 발행하려면 이 .command를 한 번 더 더블클릭"
fi
echo ""
read -p "엔터로 닫기..."
