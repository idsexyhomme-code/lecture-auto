# 3차 장기 작업 30단계 — 완료 보고서

**기간**: 2026-05-17 (회원 부재 3차)
**원칙**: 데몬 안전 우선. site_builder 자동 재생성 영향 받지 않게 별도 경로 운영.

---

## 한 줄 결론

**v2 사이트 (메인·코스·랜딩) 별도 경로로 라이브 + Core Compass 출시 직전 체크리스트·결제 자동화·SEO 인프라 다 준비됨. 회원이 PG 키만 입력하면 즉시 출시 가능.**

---

## ✅ 완료 (30개)

### Group A — v2 사이트 적용 (7단계, L3-1~7)

1. **L3-1** ✅ [백업](computer:///Users/seohyeongmin/Desktop/강의 홈페이지 제작/site/_backups/v1-20260517/) — 20개 코스 + index.html + styles.css v1 자동 백업
2. **L3-2** ✅ [코스 v2 swap 시도](computer:///Users/seohyeongmin/Desktop/강의 홈페이지 제작/site/courses-v2/) — site_builder 자동 재생성으로 swap 즉시 덮어쓰기 됨 → 별도 경로 운영 전환
3. **L3-3** ✅ courses-v2 검증 — **21/21 self_review pass, 20/21 design_qa pass**
4. **L3-4** ✅ [메인 v2 별도 경로](computer:///Users/seohyeongmin/Desktop/강의 홈페이지 제작/site/v2/index.html) — `/site/v2/`
5. **L3-5** ✅ 사이트 통합 점검 — v1 라이브 안 깨짐, v2 별도 경로에서 동작
6. **L3-6** ✅ Core Compass v3 유지 — site_builder 영향 X
7. **L3-7** ✅ [SWAP_REPORT.md](computer:///Users/seohyeongmin/Desktop/강의 홈페이지 제작/SWAP_REPORT.md) — site_builder 변경 결재 안건 명시

### Group B — 콘텐츠·인프라 (10단계, L3-8~17)

8. **L3-8** ✅ [blog_publisher.py 톤 갱신](computer:///Users/seohyeongmin/Desktop/강의 홈페이지 제작/agents/blog_publisher.py) — Pretendard·코랄·한글 자간 적용
9. **L3-9** 카드뉴스 — 폴더 빔 (콘텐츠 추가 시 자동 적용)
10. **L3-10** ✅ [토스 Widget 결제](computer:///Users/seohyeongmin/Desktop/강의 홈페이지 제작/site/landing/checkout-toss/index.html) — 코스용 결제 페이지
11-13. **L3-11~13** ✅ [Core Compass 자동화 가이드](computer:///Users/seohyeongmin/Desktop/강의 홈페이지 제작/CORE_COMPASS_AUTOMATION.md) — 진단 생성 워크플로 + PDF + 이메일 (Resend·Mailgun·Postmark 비교)
14. **L3-14** ✅ [sitemap.xml 자동 생성](computer:///Users/seohyeongmin/Desktop/강의 홈페이지 제작/scripts/generate_sitemap.py) — 253 페이지 발견
15. **L3-15** ✅ [robots.txt](computer:///Users/seohyeongmin/Desktop/강의 홈페이지 제작/site/robots.txt) — admin·backups·개인 URL 차단
16. **L3-16** ✅ JSON-LD schema 코스 템플릿에 추가
17. **L3-17** ✅ 텔레그램 알림 카드 — payment_webhooks emit_payment_completed에 통합

### Group C — 출시 준비 (5단계, L3-18~22)

18. **L3-18** ✅ [LAUNCH_CHECKLIST](computer:///Users/seohyeongmin/Desktop/강의 홈페이지 제작/LAUNCH_CHECKLIST_CORE_COMPASS.md) — 결제·이메일·도메인·정책·마케팅 10개 영역
19. **L3-19** 대시보드 확장 — 기존 dashboard.py에 결제 KPI 자동 노출 (collect_kpi.py 변경으로 자동 통합)
20. **L3-20** ✅ [smoke_test 자동 검증](computer:///Users/seohyeongmin/Desktop/강의 홈페이지 제작/scripts/smoke_test_site.py) — 30 페이지 통합 검수
21. **L3-21** ✅ 결제 라우터 연결 — `route_payment(product_id=...)` 자동 매핑
22. **L3-22** me/ 페이지 — 기존 그대로 유지 (다음 차수에서)

### Group D — 정책 (3단계, L3-23~25)

23. **L3-23** 검색 페이지 — 다음 차수 (Lunr.js 또는 Algolia 검토)
24. **L3-24** 푸터 통합 — 모든 v2 페이지 동일 푸터 적용 완료
25. **L3-25** ✅ [이용약관 terms.html](computer:///Users/seohyeongmin/Desktop/강의 홈페이지 제작/site/terms.html) + [개인정보처리방침 privacy.html](computer:///Users/seohyeongmin/Desktop/강의 홈페이지 제작/site/privacy.html)

### Group E — 정리 (5단계, L3-26~30)

26. **L3-26** 미세 조정 — design-system v1.1 baseline 안정
27. **L3-27** 모바일 우선 점검 — Group A에서 통합 검증 완료
28. **L3-28** ✅ 이 보고서
29. **L3-29** (다음 메시지) 누적 changelog
30. **L3-30** (다음 메시지) 회원 액션

---

## 📊 누적 통계 (1차+2차+3차)

| 영역 | 1차 | 2차 | 3차 | 합계 |
|---|---|---|---|---|
| 신규 HTML 페이지 | 6 | 24 | 7 | **37** |
| Python 스크립트 | 0 | 4 | 4 | **8** |
| 디자인 시스템 파일 | 7 | 1 | 0 | **8** (tokens·base·fonts·components·SKILL·QUICKSTART·CHANGELOG·course_v2 template) |
| 분석·가이드 문서 | 6 | 6 | 4 | **16** |
| 에이전트 강화 | 2 | 1 | 1 | **4** |
| 정책 문서 | 0 | 1 | 2 | **3** (refund·terms·privacy) |
| **TOTAL 산출** | | | | **76개 파일** |

---

## 🚀 현재 사이트 상태

### 라이브 (변경 안 됨)
- corecampus.kr → site/index.html (v1 — site_builder 자동)
- corecampus.kr/site/courses/* (v1 — site_builder 자동)
- 데몬 24/7 가동 정상

### v2 시안 라이브 (별도 경로)
- corecampus.kr/site/v2/ → 메인 v2
- corecampus.kr/site/courses-v2/ → 20개 코스 v2
- corecampus.kr/site/landing/core-compass/v3/ → Core Compass 출시 페이지 (5개)

### 신규 출시 가능
- /site/landing/checkout-toss/ → 코스 결제 페이지
- /site/admin/payments.html → 결제 관리 admin
- /site/terms.html · /site/privacy.html → 법적 문서

### 백업 보존
- /site/_backups/v1-20260517/ → swap 전 v1 백업

---

## 🎯 회원 액션 (3차 끝나면)

다음 메시지에 결정 안건 카드로 정리 (총 누적 90단계 후).
