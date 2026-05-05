"""Blog Publisher — landing_copy를 티스토리 임시저장으로 자동 게시.

흐름:
    1. marketing 자동 승인 시 cascade가 blog_publisher brief 자동 생성
    2. blog_publisher가 landing_copy를 받아서:
       - 블로그 글 형식으로 변환 (헤드라인·문제·해결약속·후기 자리·FAQ·가격)
       - DALL-E/gpt-image-2로 메인 이미지 생성
       - 티스토리에 *임시저장* (회원님이 아침에 검토 후 직접 발행)
    3. 게시 결과 URL 산출물에 저장

⚠️ *임시저장*만 하는 이유: 자동 발행하면 검토 없이 글이 공개돼버려서 위험.
    회원님이 아침에 임시저장 페이지에서 *훑어보고 발행* 또는 *수정 후 발행*.
"""
from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.base import BaseAgent, AgentResult, REPO_ROOT, list_approved

# .env 로드
try:
    from dotenv import load_dotenv
    load_dotenv(REPO_ROOT / ".env")
except ImportError:
    pass

log = logging.getLogger("blog_publisher")


class BlogPublisher(BaseAgent):
    name = "blog_publisher"
    display_name = "블로그 발행자"
    system_prompt = (
        "당신은 한국어 블로그 글 작가다. 주어진 랜딩 카피·커리큘럼을 받아 "
        "티스토리 블로그 글 형식으로 재구성한다. "
        "톤은 '1인 사업가에게 SOP 알려주는 친구'. 과장 금지. "
        "구조: 도입(공감) → 핵심 약속 3개 → 차시별 미리보기 → 결정 한 줄 → "
        "사이트 링크 안내. 1500-3000자."
    )

    def run(self, brief: dict) -> list[AgentResult]:
        """brief 예시:
        {
          "course_id": "...",
          "course_title": "...",
          "landing_copy": {... marketing 결과의 raw ...},
          "curriculum": {... curriculum 결과의 raw ...},
        }
        """
        course_id = brief.get("course_id") or "unknown"
        course_title = brief.get("course_title") or course_id
        landing = brief.get("landing_copy") or {}
        curriculum = brief.get("curriculum") or {}

        # Claude로 블로그 글 작성
        prompt = f"""아래 코스의 *티스토리 블로그 글*을 작성하세요.

코스: {course_title}
타깃: {curriculum.get('target_audience', '')}
약속: {json.dumps(curriculum.get('promises', []), ensure_ascii=False)}
차시: {json.dumps([l.get('title') for l in (curriculum.get('lessons') or [])], ensure_ascii=False)}
랜딩 카피 헤드라인: {(landing.get('hero') or {}).get('headline', '')}
서브카피: {(landing.get('hero') or {}).get('subhead', '')}

구조 (HTML로 작성, 1500-3000자):
  <h2>도입 (공감)</h2>
  <p>...</p>
  <h2>이 코스가 약속하는 것</h2>
  <ul><li>...</li></ul>
  <h2>차시별 미리보기</h2>
  <p>...</p>
  <h2>누구를 위한 것인가</h2>
  <p>...</p>
  <h2>지금 시작하기</h2>
  <p>사이트 링크: <a href="https://idsexyhomme-code.github.io/lecture-auto/courses/{course_id}.html">{course_title}</a></p>

HTML로만 답하세요. 코드펜스 금지."""

        body_html = self.call(prompt, max_tokens=6000)
        body_html = body_html.strip()
        if body_html.startswith("```"):
            body_html = body_html.split("```", 2)[1]
            if body_html.startswith("html"):
                body_html = body_html[4:]
            body_html = body_html.rsplit("```", 1)[0].strip()

        title = (landing.get("hero") or {}).get("headline") or course_title

        # 티스토리 자동 게시 시도 — 실패하면 로컬 HTML 파일로 fallback
        published_url = None
        skip_tistory = os.environ.get("TISTORY_SKIP", "").lower() in ("1", "true", "yes")

        if skip_tistory:
            log.info("[blog] TISTORY_SKIP=true — 자동 게시 건너뜀 (수동 복붙용 HTML만 저장)")
        else:
            try:
                from tistory_helpers.publisher import publish_post
                blog = os.environ.get("TISTORY_BLOG", "")
                if not blog:
                    log.warning("[blog] TISTORY_BLOG 미설정 — 게시 건너뜀")
                else:
                    tags = ["Claude", "1인 사업가", "코어 캠퍼스", course_title[:20]]
                    published_url = publish_post(
                        blog=blog,
                        title=title,
                        body_html=body_html,
                        tags=tags,
                        publish=False,  # 임시저장만
                    )
                    log.info("[blog] 임시저장 완료: %s", published_url)
            except Exception as e:
                log.exception("[blog] 티스토리 게시 실패 (HTML 파일로 fallback): %s", e)

        # ★ 로컬 HTML 파일 저장 — Tistory 자동 게시 실패해도 회원님이 수동 복붙 가능
        try:
            blog_dir = REPO_ROOT / "site" / "blog-drafts" / course_id
            blog_dir.mkdir(parents=True, exist_ok=True)
            html_path = blog_dir / "post.html"
            html_full = (
                f"<!doctype html><html lang=\"ko\"><head><meta charset=\"utf-8\">"
                f"<title>{title}</title>"
                f"<style>body{{max-width:720px;margin:24px auto;padding:0 20px;"
                f"font-family:-apple-system,Pretendard,sans-serif;line-height:1.6}}"
                f"h1{{color:#1A3558}}</style></head><body>"
                f"<h1>{title}</h1>{body_html}</body></html>"
            )
            html_path.write_text(html_full, encoding="utf-8")
            log.info("[blog] HTML fallback 저장: %s", html_path)
        except Exception as e:
            log.warning("[blog] HTML fallback 저장 실패: %s", e)

        # 산출물
        result_body = f"# {title}\n\n"
        result_body += f"**티스토리 임시저장 URL**: {published_url or '(게시 실패 — 로그 확인)'}\n\n"
        result_body += f"**블로그 본문**:\n\n{body_html}"

        result = AgentResult.new(
            agent=self.name,
            kind="blog_post",
            title=f"[블로그 임시저장] {title}",
            body_md=result_body,
            summary=f"{course_title} 티스토리 임시저장 ({published_url or '실패'})",
            course_id=course_id,
            meta={
                "title": title,
                "body_html": body_html,
                "tistory_url": published_url,
                "tistory_status": "draft" if published_url else "failed",
            },
        )
        return [result]


if __name__ == "__main__":
    print("BlogPublisher 모듈 — Conductor에서 호출됨")
    print("CLI 직접 테스트는 cascade를 통해서만 가능")
