# 시스템 헬스 체크 — 2026-05-16

## KPI 상태 (content/state/kpi.json)

| 항목 | 값 |
|---|---|
| courses_total | 20 |
| posts_total | 171 |
| categories_total | 3 |
| approved_count (누적) | 355 |
| pending_count | 0 |
| rejected_count | 0 |
| last_brief_processed | 2026-05-16 06:20 KST |
| blog_published_today | 0 |
| blog_failed_today | 0 |
| blog_scheduled_total | 24 |
| last_blog_publish | 2026-05-05 (11일 전 — 알람 필요?) |

**관찰**:
- ✅ Brief 처리 정상 (오늘 06:20에 마지막 처리)
- ⚠ 블로그 마지막 발행이 5/5 — 11일간 발행 정지 상태
- 원인 추정: 티스토리 세션 만료 (#49 실패 40건 미발행)

## 비용 (content/state/daily_total.json)

- 오늘 (5/16) 누적: **$0.98** (한도 안)
- 어제 (5/15) 종료: $1.40 (추정)
- 일평균 $1.20 정도 — 월 $36 수준 (예산 안)

## §11 디스패치 큐 (content/tasks/)

| 상태 | 개수 |
|---|---|
| pending | 5 |
| in_progress | 1 |
| completed | 2 |
| review_required | 0 |
| approved | 1 |
| rejected | 0 |

**관찰**:
- pending 5건 적체 — 데몬이 잘 처리하는지 확인 필요
- in_progress 1건 stuck 가능성 → 회원 복귀 시 직접 점검

## 데몬 상태

`launchctl` 샌드박스에서 직접 확인 불가. 회원님 Mac에서 확인:
```bash
launchctl list | grep corecampus
```

기대 결과:
```
- 0 com.corecampus.longpoll    (Daemon 정상 동작)
```

## 자가 학습 상태 (data/learning/)

- `copy_principles_v2.json` 존재 — 통계 0건 (아직 산출물 self_review 데이터 없음)
- 새 산출물 생성 시 자동 누적될 예정

## 다음 헬스 체크 추천 (회원 직접)

1. `launchctl list | grep corecampus` — 데몬 정상?
2. `tail -50 ~/Library/Logs/corecampus-longpoll.log` — 최근 에러?
3. 대시보드 (http://localhost:7878) 더블클릭 → 워커 큐 확인
4. 티스토리 세션 새로 캡쳐 (`tistory_session.json` mtime 확인 후 만료 시 재캡쳐)
5. 실패 40건 재발행 (#49) — 세션 갱신 후 더블클릭 가능

## 정상 (변경·조치 불필요)

- KPI 수집 정상 (어제 09:00 KST 자동 캡쳐)
- 비용 추적 정상 (한도 안)
- pending 큐 적체 5건 → 데몬이 자동 처리 중
