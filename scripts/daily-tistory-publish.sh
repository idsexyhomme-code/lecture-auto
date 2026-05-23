#!/bin/bash
# 매일 새벽 3시 자동 실행 — launchd에서 호출
# 1. content/approved의 미발행 blog_post를 티스토리에 일괄 발행 (최대 15건/일)
# 2. 결과를 텔레그램으로 전송 — 회원이 아침에 확인

PROJECT="/Users/seohyeongmin/Desktop/강의 홈페이지 제작"
cd "$PROJECT" || exit 1

# 시작 로그
echo ""
echo "════════════════════════════════════════════════════════════"
echo "  $(date '+%Y-%m-%d %H:%M:%S KST')  daily-tistory-publish 시작"
echo "════════════════════════════════════════════════════════════"

# .env 로드
set -a; [ -f .env ] && source .env; set +a

# 강제 환경변수
export TISTORY_SKIP=false
export TISTORY_SCHEDULE=0
export TISTORY_BLOG=${TISTORY_BLOG:-jejumomdad}
export TISTORY_HEADLESS=0

PY=".venv/bin/python3"
[ -x "$PY" ] || PY="python3"

# Python 실행 — 결과를 JSON으로 받음
RESULT=$("$PY" <<'PYEOF'
import json, os, sys, glob, time
sys.path.insert(0, '.')

# 일일 한도 — 공개 발행은 15건 한도, 임시저장은 보통 한도 없음.
# 임시저장으로 운영하므로 50건까지 시도 (안전 한도)
DAILY_LIMIT = 50

approved_files = sorted(
    glob.glob("content/approved/*.json"),
    key=os.path.getmtime,
)

to_publish = []
for f in approved_files:
    try:
        d = json.load(open(f, 'r', encoding='utf-8'))
        if d.get("kind") != "blog_post":
            continue
        meta = d.get("meta") or {}
        if meta.get("published_url") or meta.get("tistory_url"):
            continue
        to_publish.append((f, d))
    except Exception:
        pass

if not to_publish:
    print(json.dumps({
        "status": "no_pending",
        "message": "발행 대기 글 0건 — 새 brief 큐잉 필요",
        "success": 0,
        "failed": 0,
    }, ensure_ascii=False))
    sys.exit(0)

# 일일 한도 적용
batch = to_publish[:DAILY_LIMIT]

try:
    from tistory_helpers.publisher import publish_post
except ImportError as e:
    print(json.dumps({
        "status": "import_error",
        "error": str(e),
        "success": 0,
        "failed": 0,
    }, ensure_ascii=False))
    sys.exit(1)

blog = os.environ.get("TISTORY_BLOG", "jejumomdad")
success = []
failed = []

for i, (f, d) in enumerate(batch, 1):
    title = d.get("title", "").replace("[블로그 임시저장] ", "").strip()
    meta = d.get("meta") or {}
    body_html = meta.get("body_html") or meta.get("html") or meta.get("content") or ""

    if not body_html:
        failed.append({"title": title[:50], "error": "body_html 없음"})
        continue

    course_id = d.get("course_id", "")
    tags = ["Claude", "1인 사업가"]
    if course_id:
        tags.append(course_id)

    try:
        url = publish_post(
            blog=blog,
            title=title,
            body_html=body_html,
            tags=tags,
            publish=False,  # 임시저장 — 회원이 직접 공개
            headless=False,
        )
        d.setdefault("meta", {})["published_url"] = url
        d["meta"]["published_at"] = int(time.time())
        with open(f, 'w', encoding='utf-8') as fh:
            json.dump(d, fh, ensure_ascii=False, indent=2)
        success.append({"title": title[:50], "url": url})

        if i < len(batch):
            time.sleep(5)  # rate limit 방지

    except Exception as e:
        err = str(e)[:200]
        failed.append({"title": title[:50], "error": err})
        # 한도 초과 메시지면 즉시 중단
        if any(k in err.lower() for k in ["한도", "limit", "15", "초과", "block"]):
            print(json.dumps({
                "status": "rate_limit_hit",
                "message": f"{i}건 발행 후 한도 도달 — 내일 새벽 3시 자동 재개",
                "success_count": len(success),
                "failed_count": len(failed),
                "success": success,
                "failed": failed,
                "remaining": len(to_publish) - len(success) - len(failed),
            }, ensure_ascii=False))
            sys.exit(0)

print(json.dumps({
    "status": "ok",
    "success_count": len(success),
    "failed_count": len(failed),
    "success": success,
    "failed": failed,
    "remaining": len(to_publish) - len(success) - len(failed),
}, ensure_ascii=False))
PYEOF
)

echo "$RESULT"

# 텔레그램 카드 전송
"$PY" <<PYEOF
import json, os, sys
sys.path.insert(0, '.')

try:
    result = json.loads('''$RESULT''')
except Exception as e:
    print(f"JSON 파싱 실패: {e}")
    sys.exit(0)

try:
    from telegram_bot import client as tg
except ImportError:
    print("텔레그램 import 실패 — 발송 건너뜀")
    sys.exit(0)

status = result.get("status", "?")
sc = result.get("success_count", 0)
fc = result.get("failed_count", 0)
remaining = result.get("remaining", 0)

if status == "no_pending":
    msg = "🌙 *새벽 3시 발행* — 발행 대기 글 없음\n\n새 blog_post brief 큐잉 필요"
elif status == "rate_limit_hit":
    msg = (
        f"🌙 *새벽 3시 자동 발행 완료*\n\n"
        f"✅ 발행: *{sc}건*\n"
        f"❌ 실패: *{fc}건*\n"
        f"⏸ 일일 한도 도달 — 남은 *{remaining}건*은 내일 3시 자동 재개\n\n"
        f"확인: https://jejumomdad.tistory.com"
    )
elif status == "ok":
    msg = (
        f"🌙 *새벽 3시 자동 발행 완료*\n\n"
        f"✅ 성공: *{sc}건*\n"
        f"❌ 실패: *{fc}건*\n"
        f"📋 남은 대기: *{remaining}건*\n\n"
        f"확인: https://jejumomdad.tistory.com"
    )
else:
    msg = f"⚠️ 새벽 3시 발행 — 상태 *{status}*\n\n{result.get('error', '')[:200]}"

# 성공한 글 URL 일부 첨부
success_list = result.get("success", [])[:5]
if success_list:
    msg += "\n\n*최근 발행:*"
    for s in success_list:
        msg += f"\n• {s['title'][:40]}\n  {s.get('url', '')}"

try:
    tg.send_text(msg)
    print("✓ 텔레그램 발송 완료")
except Exception as e:
    print(f"텔레그램 발송 실패: {e}")
PYEOF

echo "$(date '+%Y-%m-%d %H:%M:%S KST')  daily-tistory-publish 종료"
echo ""
