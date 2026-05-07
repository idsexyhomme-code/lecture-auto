"""기존 blog_post 본문을 새 system_prompt(20년 경력 블로그 마케터 톤)로 일괄 재생성.

사용:
    python scripts/rewrite_blog_posts.py            # 모두
    python scripts/rewrite_blog_posts.py --only scheduled,draft   # 상태 필터
    python scripts/rewrite_blog_posts.py --limit 5  # 개수 제한
    python scripts/rewrite_blog_posts.py --id 1778189337-75aaa2 # 특정 ID

출력: content/blog_v2/<id>.html (재생성된 본문) + content/blog_v2/<id>.meta.json (제목·코스·이전상태)
원본 content/approved/*.json 은 *건드리지 않음*.
"""
from __future__ import annotations
import argparse, json, os, sys, time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

try:
    from dotenv import load_dotenv
    load_dotenv(REPO / ".env")
except Exception:
    pass

from agents.blog_publisher import BlogPublisher  # 새 system_prompt 포함

APPROVED = REPO / "content" / "approved"
OUT = REPO / "content" / "blog_v2"
OUT.mkdir(parents=True, exist_ok=True)


def categorize(d: dict) -> str:
    m = d.get("meta") or {}
    st = m.get("tistory_status")
    if st in ("scheduled", "draft", "failed"):
        return st
    if m.get("tistory_url"):
        return "draft"
    return "unknown"


def collect_blog_posts():
    items = []
    for f in sorted(APPROVED.glob("*.json")):
        try:
            d = json.load(open(f))
        except Exception:
            continue
        if d.get("kind") != "blog_post":
            continue
        d["__path"] = str(f)
        d["__cat"] = categorize(d)
        items.append(d)
    return items


def rewrite_one(pub: BlogPublisher, item: dict, *, force: bool = False) -> bool:
    pid = item.get("id") or Path(item["__path"]).stem
    out_html = OUT / f"{pid}.html"
    out_meta = OUT / f"{pid}.meta.json"
    if out_html.exists() and not force:
        print(f"  [skip] 이미 재생성됨: {pid}")
        return False

    course_id = item.get("course_id") or "unknown"
    course_title = (item.get("meta") or {}).get("course_title") or course_id
    title_old = item.get("title") or ""
    summary_old = item.get("summary") or ""

    # Claude API에 보낼 컨텍스트: 코스 제목 + 기존 제목/요약
    prompt = f"""티스토리 블로그 글 1편을 *처음부터 다시* 작성합니다. 시스템 프롬프트의 카피 원칙 *반드시* 따르세요.

[기존 글 정보 — 같은 주제로 다시 쓰는 것]
코스: {course_title} ({course_id})
이전 제목: {title_old}
이전 요약: {summary_old}

⚠️ 절대 쓰지 않을 단어:
  - 워크플로우, 프로세스, 솔루션, 효율적, 체계적, 최적화, 자동화 시스템, AI 활용
  - 여러분, 고민이 있으신가요, 한 차원 높은, 바쁜 일상 속에서도, ~할 수 있는 분이라면
  - 반드시, 100%, 완벽한, 단숨에, 획기적

구조 (HTML, 1500-2500자):
  <h2>(도입 — 구체적 장면 한 줄로 시작)</h2>
  <p>회원님 일상에서 실제 일어나는 장면 묘사. 시간·숫자·구체 사례.</p>

  <h2>왜 이게 어려운지</h2>
  <p>2-3 문단. 보통 사람의 진짜 이유를 솔직하게.</p>

  <h2>Claude로 어떻게 하는지</h2>
  <p>구체적 5단계. 각 단계는 한 줄 + 짧은 설명. 예시 포함.</p>
  <ul>
    <li><strong>1단계 — ...</strong> 구체적 행동</li>
    <li><strong>2단계 — ...</strong> ...</li>
  </ul>

  <h2>이게 작동하는 이유</h2>
  <p>왜 첫 시도부터 결과가 나오는지 1-2가지.</p>

  <h2>지금 시작하기</h2>
  <p>첫 차시 1개부터 보라는 한 줄. 사이트 링크: <a href="https://idsexyhomme-code.github.io/lecture-auto/courses/{course_id}.html">{course_title}</a></p>

HTML로만 답하세요. 코드펜스 금지. AI 티 나는 단어 *0개*."""

    try:
        body_html = pub.call(prompt, max_tokens=6000).strip()
        if body_html.startswith("```"):
            body_html = body_html.split("```", 2)[1]
            if body_html.startswith("html"):
                body_html = body_html[4:]
            body_html = body_html.rsplit("```", 1)[0].strip()
    except Exception as e:
        print(f"  [error] body 생성 실패 {pid}: {e}")
        return False

    # 새 제목도 생성
    title_prompt = (
        f"티스토리 블로그 글 *제목* 한 줄을 작성하세요.\n"
        f"코스: {course_title} ({course_id})\n"
        f"이전 제목: {title_old}\n\n"
        f"규칙:\n"
        f"- 25-45자\n"
        f"- 사람이 검색창에 칠 만한 단어로\n"
        f"- 약속·결과를 구체적 숫자로 (예: '메일 30통, 5분이면 끝납니다')\n"
        f"- 또는 일상 장면으로 (예: '월요일 아침 받은편지함, 더는 무섭지 않아요')\n"
        f"- 절대 금지 단어: 워크플로우, 자동화, 효율, 체계, 솔루션, AI 활용, 여러분\n"
        f"- 따옴표·이모지·마크다운 없이 일반 텍스트만\n"
        f"- 한 줄만"
    )
    try:
        title_new = pub.call(title_prompt, max_tokens=200).strip().strip('"').strip("'").split("\n")[0]
    except Exception as e:
        print(f"  [warn] 제목 생성 실패 {pid}: {e}")
        title_new = title_old

    out_html.write_text(body_html, encoding="utf-8")
    out_meta.write_text(json.dumps({
        "id": pid,
        "course_id": course_id,
        "course_title": course_title,
        "title_old": title_old,
        "title_new": title_new,
        "summary_old": summary_old,
        "tistory_status_old": (item.get("meta") or {}).get("tistory_status"),
        "scheduled_at_old": (item.get("meta") or {}).get("scheduled_at"),
        "tistory_url_old": (item.get("meta") or {}).get("tistory_url"),
        "rewritten_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "body_len": len(body_html),
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  [ok] {pid}  title_new={title_new[:40]}  body_len={len(body_html)}")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", type=str, default="", help="상태 필터 (scheduled,draft,failed,unknown 콤마)")
    ap.add_argument("--limit", type=int, default=0, help="처리 개수 제한 (0=무제한)")
    ap.add_argument("--id", type=str, default="", help="특정 ID만")
    ap.add_argument("--force", action="store_true", help="이미 재생성된 것도 다시")
    args = ap.parse_args()

    only = set(s.strip() for s in args.only.split(",") if s.strip()) if args.only else None
    items = collect_blog_posts()
    if args.id:
        items = [i for i in items if (i.get("id") or "").startswith(args.id)]
    if only:
        items = [i for i in items if i["__cat"] in only]

    print(f"대상 blog_post: {len(items)}건")
    for c in ("scheduled", "draft", "failed", "unknown"):
        n = sum(1 for i in items if i["__cat"] == c)
        if n:
            print(f"  {c}: {n}")

    if args.limit > 0:
        items = items[: args.limit]
        print(f"limit 적용: {len(items)}건만 처리")

    pub = BlogPublisher()
    done = 0
    for i, item in enumerate(items, 1):
        print(f"[{i}/{len(items)}] {Path(item['__path']).name}  cat={item['__cat']}")
        if rewrite_one(pub, item, force=args.force):
            done += 1
        time.sleep(0.5)  # API rate limiting
    print(f"\n=== 완료: {done}/{len(items)} 재생성 ===")
    print(f"출력: {OUT}")


if __name__ == "__main__":
    main()
