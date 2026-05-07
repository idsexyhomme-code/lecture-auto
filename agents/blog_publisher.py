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
        "당신은 20년 경력의 시니어 블로그 마케터다. 한국 1인 사업가·실무자가 매일 검색하는 키워드로 "
        "티스토리에 글을 쓴다.\n\n"
        "★ 카피 원칙 — 실제 사람이 읽고 검색하는 단어로:\n"
        "  - 추상 단어·전문 용어 금지: 워크플로우, 프로세스, 솔루션, 효율적, 체계적, 최적화, 자동화 시스템, "
        "    AI 활용, 단계별 학습, 성장, 실현, 구현, 활용\n"
        "  - 짧고 단호한 동사형 한국어: '씁니다', '줄입니다', '끝납니다', '됩니다', '남습니다', '바뀝니다'\n"
        "  - 사람이 검색창에 치는 단어: '메일 잘 쓰는 법', '회의록 정리', '고객 응대 자동', '매출 정리'\n"
        "  - 과장 금지: '반드시', '100%', '완벽한', '획기적', '단숨에', '모든'\n"
        "  - 친구한테 말하듯 — 솔직하고 구체적: '솔직히', '사실', '그냥', '바로', '한 번에'\n"
        "  - 숫자·구체 사례로 시작: '메일 30통, 5분', '월간 보고서 1시간 → 5분'\n"
        "  - AI 티 표현 금지: '여러분', '고민이 있으신가요', '~로 자동화하세요', '한 차원 높은', "
        "    '~할 수 있는 분이라면', '바쁜 일상 속에서도'\n\n"
        "★ 글 구조 (1500-2500자, 길이 욕심 X):\n"
        "  - 도입: 회원님 일상의 구체적 장면 1개 (예: '월요일 오전 9시, 받은편지함에 87통.')\n"
        "  - 본론 1: 왜 이게 어려운지 (보통 사람의 진짜 이유)\n"
        "  - 본론 2: Claude를 어떻게 쓰는지 (구체적 5단계 + 예시)\n"
        "  - 본론 3: 첫 시도가 작동하는 이유 1-2가지\n"
        "  - 마무리: 첫 차시 1개부터 보라는 한 줄 + 사이트 링크\n"
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
        prompt = f"""티스토리 블로그 글 1편을 작성하세요. 시스템 프롬프트의 카피 원칙 *반드시* 따르세요.

코스: {course_title}
타깃: {curriculum.get('target_audience', '')}
약속: {json.dumps(curriculum.get('promises', []), ensure_ascii=False)}
차시: {json.dumps([l.get('title') for l in (curriculum.get('lessons') or [])], ensure_ascii=False)}

⚠️ 절대 쓰지 않을 단어:
  - 워크플로우, 프로세스, 솔루션, 효율적, 체계적, 최적화, 자동화 시스템
  - 여러분, 고민이 있으신가요, 한 차원 높은, 바쁜 일상 속에서도
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

        body_html = self.call(prompt, max_tokens=6000)
        body_html = body_html.strip()
        if body_html.startswith("```"):
            body_html = body_html.split("```", 2)[1]
            if body_html.startswith("html"):
                body_html = body_html[4:]
            body_html = body_html.rsplit("```", 1)[0].strip()

        # 제목 — landing의 hero.headline 우선 + 비거나 코스ID 그대로면 Claude로 새로 짓기
        title = (landing.get("hero") or {}).get("headline") or ""
        if not title or title == course_id or len(title) < 10:
            title_prompt = (
                f"티스토리 블로그 글 *제목* 한 줄을 작성하세요.\n"
                f"코스: {course_title} ({course_id})\n"
                f"타깃: {curriculum.get('target_audience', '1인 사업가')}\n"
                f"약속: {json.dumps(curriculum.get('promises', [])[:2], ensure_ascii=False)}\n\n"
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
                title = self.call(title_prompt, max_tokens=200).strip().strip('"').strip("'").split("\n")[0]
                log.info("[blog] ✓ Claude 제목 생성: %s", title)
            except Exception as e:
                log.warning("[blog] 제목 생성 실패: %s", e)
                title = course_title

        # ★ 이미지 자동 생성 (gpt-image-2) + 본문 상단에 임베드
        # 전략: 티스토리에 업로드 안 함 → GitHub Pages에 호스팅 → <img>가 공개 URL 가리킴
        hero_img_url = None
        try:
            from agents.image_gen import generate_blog_image
            img_prompt = (
                f"Editorial magazine cover for Korean online course '{course_title}'. "
                f"Warm beige and dark brown palette (#F5EFE0, #3B2A1E), "
                f"minimalist composition, abstract geometric shapes representing "
                f"knowledge and growth. No Korean text in image (text rendering inconsistent). "
                f"Quiet intellectual atmosphere, editorial photography style."
            )
            _, hero_img_url = generate_blog_image(img_prompt, f"{course_id}-hero")
            hero_img_html = (
                f'<p style="text-align:center;margin:20px 0">'
                f'<img src="{hero_img_url}" alt="{title}" '
                f'style="max-width:100%;height:auto;border-radius:8px;'
                f'box-shadow:0 4px 12px rgba(0,0,0,0.08)">'
                f'</p>'
            )
            body_html = hero_img_html + "\n\n" + body_html
            log.info("[blog] ✓ hero image embedded: %s", hero_img_url)
        except Exception as e:
            log.warning("[blog] hero image gen failed (텍스트로만 진행): %s", e)

        # 티스토리 자동 게시 시도 — 실패하면 로컬 HTML 파일로 fallback
        published_url = None
        schedule_at = None  # ★ 모든 분기에서 안전하게 참조 가능하도록 최상위 정의
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
                    # publish=True — 모달에 *공개 발행* 버튼만 있어서 임시저장 불가능.
                    # 즉시 라이브 게시. 회원님이 글 검토 후 비공개 처리는 블로그에서.
                    # headless=False — 헤드리스 모드에서 모달 클릭이 불안정.
                        # 환경변수로 강제 가능: TISTORY_HEADLESS=1 → headless=True
                    headless = os.environ.get("TISTORY_HEADLESS", "0").lower() in ("1", "true", "yes")

                    # ★ 자동 분산 예약 발행 — 일일 한도 회피
                    schedule_at = None
                    use_schedule = os.environ.get("TISTORY_SCHEDULE", "1").lower() in ("1", "true", "yes")
                    if use_schedule:
                        try:
                            from tistory_helpers.scheduler import next_publish_slot, commit_slot
                            schedule_at = next_publish_slot()
                            if schedule_at:
                                log.info("[blog] 📅 예약 발행 슬롯: %s",
                                         schedule_at.strftime("%Y-%m-%d %H:%M"))
                        except Exception as e:
                            log.warning("[blog] scheduler 실패 — 즉시 발행: %s", e)

                    published_url = publish_post(
                        blog=blog,
                        title=title,
                        body_html=body_html,
                        tags=tags,
                        publish=True,
                        schedule_at=schedule_at,
                        headless=headless,
                    )

                    # 슬롯 사용 확정
                    if schedule_at and published_url:
                        try:
                            from tistory_helpers.scheduler import commit_slot
                            commit_slot(schedule_at)
                        except Exception as e:
                            log.warning("[blog] commit_slot 실패: %s", e)
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
        scheduled_str = schedule_at.strftime("%Y-%m-%d %H:%M (KST)") if schedule_at else "(즉시)"
        result_body = f"# {title}\n\n"
        result_body += f"**티스토리 URL**: {published_url or '(게시 실패 — 로그 확인)'}\n\n"
        result_body += f"**예약 시각**: {scheduled_str}\n\n"
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
                "hero_image_url": hero_img_url,
                "tistory_url": published_url,
                "tistory_status": "scheduled" if (published_url and schedule_at) else ("draft" if published_url else "failed"),
                "scheduled_at": schedule_at.isoformat() if schedule_at else None,
            },
        )
        return [result]


if __name__ == "__main__":
    print("BlogPublisher 모듈 — Conductor에서 호출됨")
    print("CLI 직접 테스트는 cascade를 통해서만 가능")
