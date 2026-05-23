# 데몬 재시작·복구 가이드

## 데몬 상태 확인
```bash
launchctl list | grep corecampus
```
정상이면 PID + Exit Code (0) 표시.

## 정지
```bash
launchctl unload ~/Library/LaunchAgents/com.corecampus.longpoll.plist
```

## 재기동
```bash
launchctl load ~/Library/LaunchAgents/com.corecampus.longpoll.plist
```

## 강제 재시작 (정지 → 5초 대기 → 재기동)
```bash
launchctl unload ~/Library/LaunchAgents/com.corecampus.longpoll.plist
sleep 5
launchctl load ~/Library/LaunchAgents/com.corecampus.longpoll.plist
```

## 로그 확인 (최근 50줄)
```bash
tail -50 ~/Library/Logs/corecampus-longpoll.log
```

## 비상 시 — 데몬 망가졌을 때

1. **즉시 정지**:
   ```bash
   launchctl unload ~/Library/LaunchAgents/com.corecampus.longpoll.plist
   ```

2. **최근 변경 되돌리기** (Git):
   ```bash
   cd "~/Desktop/강의 홈페이지 제작"
   git log -5  # 최근 5개 커밋 확인
   git reset --hard HEAD~1  # 1단계 되돌리기
   ```

3. **재기동**:
   ```bash
   launchctl load ~/Library/LaunchAgents/com.corecampus.longpoll.plist
   ```

4. **로그 모니터**:
   ```bash
   tail -f ~/Library/Logs/corecampus-longpoll.log
   ```

## 잠금 파일 정리 (드물지만 stuck 시)
```bash
rm -f content/state/locks/*.lock
```

## 비상 백업 위치
- 사이트 백업: `site/_backups/v1-20260517/`
- 콘텐츠 백업: `content/approved/` (시간순)
- 설정 백업: `data/site_config.json` (Git 관리)
