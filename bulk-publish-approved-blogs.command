#!/bin/bash
# 🚀 일괄 티스토리 발행 — content/approved의 미발행 blog_post 전체

PROJECT="/Users/seohyeongmin/Desktop/강의 홈페이지 제작"
cd "$PROJECT" || exit 1

echo "════════════════════════════════════════════════════════════"
echo "  🚀 일괄 티스토리 발행 — 승인된 미발행 blog_post"
echo "════════════════════════════════════════════════════════════"
echo ""

set -a; [ -f .env ] && source .env; set +a

PY=".venv/bin/python3"
[ -x "$PY" ] || PY="python3"

# 환경변수 강제 — 이번 실행에만 즉시 발행
export TISTORY_SKIP=false
export TISTORY_SCHEDULE=0
export TISTORY_BLOG=${TISTORY_BLOG:-jejumomdad}
export TISTORY_HEADLESS=0

"$PY" <<'PYEOF'
import json, os, sys, glob, time
sys.path.insert(0, '.')

approved_files = sorted(
    glob.glob("content/approved/*.json"),
    key=os.path.getmtime,
    reverse=True,
)

blog_posts = []
for f in approved_files:
    try:
        d = json.load(open(f, 'r', encoding='utf-8'))
        if d.get("kind") == "blog_post":
            blog_posts.append((f, d))
    except Exception:
        pass

# 이미 published_url 있는 글 제외
to_publish = []
for f, d in blog_posts:
    meta = d.get("meta") or {}
    if not meta.get("published_url") and not meta.get("tistory_url"):
        to_publish.append((f, d))

print(f"  승인된 blog_post 총: {len(blog_posts)}건")
print(f"  발행 대기 (미발행): {len(to_publish)}건")
print()

if not to_publish:
    print("  ✓ 모두 이미 발행됨 — 새 brief 큐잉 필요")
    sys.exit(0)

try:
    from tistory_helpers.publisher import publish_post
except ImportError as e:
    print(f"❌ publisher import 실패: {e}")
    sys.exit(1)

blog = os.environ.get("TISTORY_BLOG", "jejumomdad")
print(f"  타깃 블로그: {blog}.tistory.com")
print()

success = 0
failed = 0
for i, (f, d) in enumerate(to_publish, 1):
    title = d.get("title", "").replace("[블로그 임시저장] ", "").strip()
    meta = d.get("meta") or {}
    body_html = meta.get("body_html") or meta.get("html") or ""

    if not body_html:
        # raw·content 필드도 시도
        body_html = meta.get("content") or meta.get("raw_html") or ""

    if not body_html:
        print(f"  [{i}/{len(to_publish)}] ❌ body_html 없음: {title[:40]}")
        failed += 1
        continue

    course_id = d.get("course_id", "")
    tags = ["Claude", "1인 사업가", "코어 캠퍼스"]
    if course_id:
        tags.append(course_id)

    print(f"  [{i}/{len(to_publish)}] 임시저장 중: {title[:50]}")
    try:
        url = publish_post(
            blog=blog,
            title=title,
            body_html=body_html,
            tags=tags,
            publish=False,  # 임시저장 모드 — 회원이 검토 후 공개
            headless=False,
        )
        print(f"           ✅ → {url}")

        # meta 갱신
        d.setdefault("meta", {})["published_url"] = url
        d["meta"]["published_at"] = int(time.time())
        with open(f, 'w', encoding='utf-8') as fh:
            json.dump(d, fh, ensure_ascii=False, indent=2)
        success += 1

        # 다음 발행 전 짧은 대기 (티스토리 rate limit 방지)
        if i < len(to_publish):
            time.sleep(3)

    except Exception as e:
        print(f"           ❌ 실패: {type(e).__name__}: {str(e)[:200]}")
        failed += 1

print()
print("════════════════════════════════════════════════════════════")
print(f"  완료 — 성공 {success}건 / 실패 {failed}건")
print(f"  확인: https://{blog}.tistory.com/")
print("════════════════════════════════════════════════════════════")
PYEOF

echo ""
read -p "엔터로 닫기..."
