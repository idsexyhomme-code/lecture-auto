# 콘텐츠 자동 파이프라인 — 코스 → 블로그 → SNS → 이메일

> 1개 콘텐츠 작성 → 4개 채널 자동 변환·발행

## 전체 흐름

```
┌─────────────┐
│  코스 1편   │ (curriculum + producer agent 자동 생성)
└──────┬──────┘
       ↓
┌─────────────┐
│ 블로그 1편  │ (blog_publisher 자동 변환)
└──────┬──────┘
       ↓ (이미 Tistory·Naver 자동 발행)
       │
       ├──→ [인스타 카드 SVG] (blog_to_instagram.py)
       ├──→ [X 쓰레드] (blog_to_x_thread.py)
       └──→ [이메일 뉴스레터] (blog_to_newsletter.py)
                ↓
       [Resend 자동 발송]
```

## 1. 블로그 → 인스타 카드 자동 변환

**스크립트**: `scripts/blog_to_instagram.py`

```python
"""블로그 글 HTML → 인스타 1080×1080 SVG 카드 생성.

추출 항목:
- H1 (메인 카피)
- 첫 H2 (서브 카피)
- 인용문 또는 핵심 1줄

생성: site/landing/core-compass/v4/cards/instagram-{slug}.svg
"""
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
BLOG_DIR = ROOT / "site/blog-drafts"
OUTPUT_DIR = ROOT / "site/landing/core-compass/v4/cards"


def extract_headline(html):
    m = re.search(r'<h1[^>]*>(.+?)</h1>', html, re.S)
    return re.sub(r'<[^>]+>', '', m.group(1)).strip() if m else ''


def generate_instagram_card(headline, sub, slug):
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1080" viewBox="0 0 1080 1080">
  <rect width="1080" height="1080" fill="#F5EFE0"/>
  <text x="80" y="380" font-family="Pretendard, sans-serif" font-size="56" font-weight="800"
    fill="#1F1F1F" letter-spacing="-2">{headline[:30]}</text>
  <text x="80" y="460" font-family="Pretendard, sans-serif" font-size="36" font-weight="800"
    fill="#D85A30" letter-spacing="-1.5">{headline[30:60] if len(headline) > 30 else ''}</text>
  <text x="80" y="560" font-family="Pretendard, sans-serif" font-size="20"
    fill="#6B6B6B">{sub[:50]}</text>
  <rect x="80" y="920" width="280" height="60" rx="12" fill="#D85A30"/>
  <text x="220" y="958" text-anchor="middle" font-family="Pretendard, sans-serif" font-size="20"
    font-weight="700" fill="#FFFFFF">자세히 보기</text>
</svg>'''


# 사용 예
for blog_dir in BLOG_DIR.iterdir():
    if not blog_dir.is_dir(): continue
    post = blog_dir / "post.html"
    if not post.exists(): continue
    html = post.read_text(encoding='utf-8')
    headline = extract_headline(html)
    sub = "1인 사업가의 AI 수익 시스템"
    svg = generate_instagram_card(headline, sub, blog_dir.name)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / f"instagram-{blog_dir.name}.svg").write_text(svg)
```

## 2. 블로그 → X (트위터) 쓰레드 자동 생성

**스크립트**: `scripts/blog_to_x_thread.py` (Claude API 활용)

```python
"""블로그 → 3~5 트윗 자동 분할.

각 트윗 280자 안. 마지막 트윗에 블로그 링크.
"""
import os, sys
sys.path.insert(0, '/Users/seohyeongmin/Desktop/강의 홈페이지 제작')

PROMPT = """다음 한국어 블로그 글을 X(트위터) 쓰레드로 변환하세요.
- 280자 한 트윗 단위 (한글은 글자수 줄임)
- 3~5 트윗
- 첫 트윗: 강력한 hook (질문·놀라움)
- 중간 트윗: 핵심 인사이트
- 마지막 트윗: 블로그 링크 + CTA

JSON 형식:
{"thread": ["트윗1", "트윗2", "트윗3"]}

블로그 본문:
{BLOG_CONTENT}
"""
# (Claude API 호출 코드)
```

## 3. 블로그 → 이메일 뉴스레터 자동 변환

**스크립트**: `scripts/blog_to_newsletter.py`

```python
"""블로그 HTML → Resend 호환 인라인 CSS 이메일.

핵심:
- max-width 600px
- 인라인 CSS만 (Tistory처럼)
- 도메인 sender from corecampus.kr
"""
TEMPLATE = '''
<table cellpadding="0" cellspacing="0" border="0" width="100%" style="...">
  <tr><td style="..."> {TITLE_H1} </td></tr>
  <tr><td style="..."> {EXCERPT_PREVIEW} </td></tr>
  <tr><td style="...">
    <a href="{BLOG_URL}" style="...">전체 글 읽기 →</a>
  </td></tr>
</table>
'''
```

## 4. 파이프라인 대시보드

site/admin/content-pipeline.html — 모든 코스의 각 단계 상태:

| 코스 | 블로그 | 인스타 | X 쓰레드 | 이메일 |
|---|---|---|---|---|
| claude-launchpad | ✓ 발행 | ✓ | 대기 | ✓ |
| claude-autowork | ✓ 발행 | 대기 | 대기 | 대기 |
| ... | | | | |

## 5. 자동 발행 스케줄러

`scripts/scheduled_publish.py` — 매주 화·금 09:00 KST 실행:

```
1. 미발행 블로그 글 picks 1편
2. Tistory 발행 (기존 blog_publisher)
3. 인스타 카드 SVG 생성
4. X 쓰레드 생성 (수동 발행)
5. 이메일 뉴스레터 발송 (구독자에게)
6. 텔레그램 알림 — 발행 완료
```

launchd plist 추가 — `com.corecampus.weekly-publish.plist`

## 회원 직접 진행 가이드

1. **인스타 카드** — 자동 생성 후 회원이 직접 인스타 발행 (Meta API 자동화 별도)
2. **X 쓰레드** — 자동 생성 후 회원이 X에서 직접 thread 발행
3. **이메일** — Resend·Stibee 구독자 DB와 연동 후 자동 발송
