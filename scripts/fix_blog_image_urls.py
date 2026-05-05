"""approved/blog_post 글 본문의 Pages URL → raw.githubusercontent.com URL 치환.

Pages 빌드 안 기다려도 즉시 라이브.
"""
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
APPROVED_DIR = REPO_ROOT / "content" / "approved"

OLD = "https://idsexyhomme-code.github.io/lecture-auto"
NEW = "https://raw.githubusercontent.com/idsexyhomme-code/lecture-auto/main/site"

count = 0
for f in sorted(APPROVED_DIR.glob("*.json")):
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        continue
    if d.get("kind") != "blog_post":
        continue

    meta = d.get("meta") or {}
    body = meta.get("body_html") or ""
    hero = meta.get("hero_image_url") or ""
    body_md = d.get("body_md") or ""

    changed = False
    if OLD in body:
        meta["body_html"] = body.replace(OLD, NEW)
        changed = True
    if OLD in hero:
        meta["hero_image_url"] = hero.replace(OLD, NEW)
        changed = True
    if OLD in body_md:
        d["body_md"] = body_md.replace(OLD, NEW)
        changed = True

    if changed:
        d["meta"] = meta
        f.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
        count += 1
        print(f"  ✓ {f.name} ({d.get('course_id')})")

print(f"\n총 {count}개 파일 URL 치환 완료.")
