"""티스토리 자동 게시 헬퍼.

티스토리 공식 API는 2023년 4월부터 신규 발급 중단 → Playwright 브라우저
자동화 경로. 1회 수동 로그인으로 쿠키 캡처 후, 데몬이 그 쿠키로 자동 게시.

모듈:
  auth.py       — 1회 수동 로그인, 쿠키 캡처
  publisher.py  — 자동 글 게시 (마크다운/HTML)

⚠️ 보안: content/state/tistory_session.json 파일은 *절대* git에 커밋하면 안 됨.
   .gitignore에 등록되어 있어야 함.
"""
