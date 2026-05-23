# 회원 관리·DB·OAuth 통합 가이드

## DB 옵션 3가지

| 옵션 | 가격 | 난이도 | 한국 친화 |
|---|---|---|---|
| **Supabase** (Postgres + Auth) | 무료 (500MB) | 쉬움 | 영문 UI |
| **Firebase** (NoSQL + Auth) | 무료 (Spark) | 중 | 영문 UI |
| **자체 SQLite + Auth.js** | 무료 (호스팅비만) | 어려움 | 자유 |

### 추천: **Supabase** — 가격·기능·문서 가장 좋음

```bash
# 가입
https://supabase.com → New project (corecampus)

# 키 .env 추가
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_KEY=eyJ...
```

## 회원 DB 스키마 (Supabase)

```sql
-- users 테이블
create table users (
  id uuid primary key default uuid_generate_v4(),
  email text unique not null,
  name text,
  created_at timestamp default now(),
  oauth_provider text,  -- kakao·naver·google·email
  oauth_id text,
  marketing_consent boolean default false
);

-- compass_reports 테이블 — 진단 기록
create table compass_reports (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid references users(id),
  order_id text unique,
  result_url text,
  one_line_insight text,
  user_persona text,
  created_at timestamp default now(),
  expires_at timestamp,
  paid_amount integer
);

-- payments 테이블 — 모든 결제
create table payments (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid references users(id),
  order_id text unique,
  pg text,  -- payapp·toss·naver
  amount integer,
  status text,  -- pending·completed·refunded·failed
  created_at timestamp default now(),
  product_id text
);

-- course_enrollments 테이블 — 코스 수강
create table course_enrollments (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid references users(id),
  course_slug text,
  enrolled_at timestamp default now(),
  completed_lessons jsonb default '[]'
);
```

## OAuth 통합

### 카카오 (가장 일반적)
1. https://developers.kakao.com → 앱 등록
2. REST API 키 발급
3. Redirect URI 설정: `https://corecampus.kr/auth/callback/kakao`
4. .env 추가:
   ```
   KAKAO_REST_API_KEY=xxx
   KAKAO_CLIENT_SECRET=xxx (선택)
   ```

### 네이버
1. https://developers.naver.com → 애플리케이션 등록
2. Client ID·Secret 발급
3. Redirect URI: `https://corecampus.kr/auth/callback/naver`
4. .env 추가:
   ```
   NAVER_CLIENT_ID=xxx
   NAVER_CLIENT_SECRET=xxx
   ```

### 구글 (글로벌)
1. https://console.cloud.google.com → OAuth 2.0
2. Client ID 발급
3. Redirect URI: `https://corecampus.kr/auth/callback/google`
4. .env 추가:
   ```
   GOOGLE_CLIENT_ID=xxx.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=xxx
   ```

## 로그인 흐름

```
1. 사용자 [카카오로 계속하기] 클릭
2. 카카오 OAuth 페이지 리디렉트
3. 사용자 동의 → callback URL로 code 받음
4. 백엔드가 code로 access_token 교환
5. access_token으로 사용자 정보 조회 (email, name)
6. users 테이블에 upsert (있으면 update, 없으면 insert)
7. 세션 쿠키 발급 → 회원 대시보드로 리디렉트
```

## 비밀번호 인증 (옵션 B)

- bcrypt 해시 저장
- 비밀번호 찾기 — 이메일 인증 토큰
- 세션 관리 — JWT 또는 Supabase Auth

## 구현 우선순위

| Phase | 작업 | 회원 직접 |
|---|---|---|
| 1 | Supabase 가입·DB 스키마 생성 | ✅ |
| 2 | 카카오 OAuth 설정 | ✅ |
| 3 | 로그인 페이지 (시안) → 실제 동작 | ✅ |
| 4 | 회원 대시보드 (시안) → 실제 동작 | ✅ |
| 5 | 진단 결과 → users 테이블 연결 | ✅ |
| 6 | 코스 수강 추적 | ✅ |

총 작업 시간: 3~7일 (회원 직접 또는 외주)

## 코드 스켈레톤

`scripts/auth.py`:
```python
import os
from supabase import create_client

supabase = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_SERVICE_KEY"]
)

def get_or_create_user(email, name, oauth_provider="email", oauth_id=None):
    result = supabase.table('users').upsert({
        'email': email,
        'name': name,
        'oauth_provider': oauth_provider,
        'oauth_id': oauth_id,
    }, on_conflict='email').execute()
    return result.data[0]
```

## 결재 안건

- 회원 관리 시스템 도입 — 회원 ✅ 필요 (§6 큰 결재)
- 출시 1주차는 무계정 운영 (개인 URL 토큰만)
- 출시 2~3주차 회원 가입 도입 (KPI 보고 결정)
