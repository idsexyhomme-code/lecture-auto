"""티스토리 *공개 발행* 직접 테스트.

실행:
    .venv/bin/python scripts/test_tistory_publish.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tistory_helpers.publisher import publish_post


def main():
    url = publish_post(
        blog="jejumomdad",
        title="[자동화 검증] 코어 캠퍼스 봇이 쓴 첫 글",
        body_html=(
            "<h2>안녕하세요</h2>"
            "<p>이 글은 코어 캠퍼스 자동화 시스템이 <b>자동으로 작성·게시</b>한 첫 글입니다.</p>"
            "<p>이 글이 보인다면 — 자동화 검증 성공!</p>"
            "<p style='color:#999'>검증용 글이라 잘못된 부분 있을 수 있습니다. "
            "회원님이 글 우상단 ⋯ 메뉴에서 비공개 처리 가능합니다.</p>"
        ),
        tags=["자동화", "검증", "코어캠퍼스"],
        publish=True,         # 공개 발행
        headless=False,       # 브라우저 보임 (검증용)
    )
    print(f"\n✓ URL: {url}")
    print("\n블로그 메인 가서 글 확인:")
    print("  https://jejumomdad.tistory.com/")


if __name__ == "__main__":
    main()
