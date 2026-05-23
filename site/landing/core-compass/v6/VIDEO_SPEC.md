# Core Compass v6 — 영상 5개 사양서

> AI 영상 생성 작업자에게 그대로 전달. 각 영상을 만들어서 `site/landing/core-compass/v6/videos/` 에 같은 이름으로 저장하면 바로 페이지에 표시됨.

## 공통 규격
- **포맷**: MP4 (H.264) + WEBM 듀얼 인코딩 권장 (호환성)
- **자동재생**: 모바일 자동재생 위해 **무음 (audio track 없음)** 필수
- **loop**: 자연스럽게 처음·끝 이어지게 (seamless loop)
- **다크 톤**: 배경 #000~#1a2347 계열, 보라/핑크/금색 액센트
- **저용량**: 각 영상 1~3MB 이내 (모바일 데이터)

---

## 📹 VIDEO #1 — Hero (페이지 첫 화면)
- **파일명**: `videos/hero-main.mp4` + `.webm`
- **크기**: 720×900 (4:5 세로)
- **길이**: 8초 seamless loop
- **컨셉**:
  - 별이 흐르는 밤하늘 + 떠다니는 구름
  - 중앙에 빛나는 문 (아치형) + 창업자 실루엣 (정면 또는 옆모습)
  - 보라/파랑 그라데이션 (#1E2541 → #5A8AFF)
  - 신비롭고 새로운 시작 느낌
- **참고**: Midjourney 프롬프트 — "korean entrepreneur silhouette walking through ethereal arch doorway into starry night sky, purple blue gradient, mystical, cinematic, dreamy"
- **HTML 위치**: 첫 Hero 섹션 (line ~600)

---

## 📹 VIDEO #2 — 신비 분위기 (블러 미리보기 위)
- **파일명**: `videos/mystical-stars.mp4` + `.webm`
- **크기**: 1080×1080 (1:1 정사각)
- **길이**: 12초 seamless loop
- **컨셉**:
  - 별빛 흐름·달밤·구름 떠다님
  - 도서관 분위기 (오래된 책·촛불·점성술 책 펼침)도 OK
  - 보라/금색 톤
- **참고**: "old leather books open with star charts, candle light, dark library, mystical atmosphere, particles floating"
- **HTML 위치**: 블러 미리보기 카드 위 (line ~630)

---

## 📹 VIDEO #3 — 리뷰 인트로 (창업자 작업 풍경)
- **파일명**: `videos/founders-mood.mp4` + `.webm`
- **크기**: 1280×720 (16:9 가로)
- **길이**: 6초 (몽타주, 짧은 컷 3~4개)
- **컨셉**:
  - 카페에서 노트북 작업하는 창업자
  - 화이트보드 앞에서 메모하는 모습
  - 화면에 진단 리포트 표시되는 컷
  - 자연스러운 광택·진솔한 분위기
- **참고**: 실제 한국 1인 창업자 톤 (스튜디오 X / 자연광 O)
- **HTML 위치**: 리뷰 섹션 위 (line ~810)

---

## 📹 VIDEO #4 — 별밤 (위험 신호 위)
- **파일명**: `videos/danger-night-sky.mp4` + `.webm`
- **크기**: 1280×720 (16:9 가로)
- **길이**: 10초 seamless loop · 무음
- **컨셉**:
  - 깊은 밤하늘 + 별빛 흐름
  - 노란빛/금색 강조 (위험 = 주의)
  - 약간의 안개·신비
  - 분위기 강조 (앞 GUARDIAN STAR 섹션 연결)
- **참고**: "deep starry night sky with golden mist, mysterious, cinematic, ominous beautiful"
- **HTML 위치**: GUARDIAN STAR 위 (line ~890)

---

## 📹 VIDEO #5 — 책·도서관 (60,000자 분량 강조)
- **파일명**: `videos/book-library.mp4` + `.webm`
- **크기**: 960×720 (4:3)
- **길이**: 8초 seamless loop
- **컨셉**:
  - 두꺼운 책 펼침 + 페이지 천천히 넘어감
  - 도서관·책장 배경
  - 신뢰감·분량·깊이 강조
- **참고**: "thick leather book pages slowly turning, library background, warm golden light, professional, depth"
- **HTML 위치**: 책 목차 위 (line ~960)

---

## 영상 받은 후 적용 방법

각 placeholder `<div class="media-slot">`를 `<video>` 태그로 교체:

```html
<!-- 받은 영상 적용 (placeholder 교체) -->
<div class="hero__visual">
  <video autoplay loop muted playsinline poster="images/hero-poster.jpg"
         style="width: 100%; height: 100%; object-fit: cover; border-radius: 32px;">
    <source src="videos/hero-main.webm" type="video/webm">
    <source src="videos/hero-main.mp4" type="video/mp4">
  </video>
</div>
```

`poster=` 는 영상 로딩 전 보여줄 정지 이미지 (1프레임 캡쳐 추천).

---

## 추가 — 이미지도 필요한 경우

영상 부담스러우면 **고품질 정지 이미지**로 대체 가능. 같은 컨셉·같은 사이즈로:
- `images/hero-poster.png`
- `images/mystical-stars.png`
- 등

이미지만 받으면 `<video>` 대신 `<img>` 태그로 교체.

---

## 작업 우선순위 추천

1. **#1 Hero (가장 중요)** — 첫 인상 결정
2. **#2 블러 미리보기** — 결제 욕구 자극
3. **#4 위험 신호** — 감정 전환
4. **#5 책** — 신뢰 강조
5. **#3 리뷰** — 있으면 좋고 없어도 OK

5개 다 안 되면 #1, #2만 만들고 나머지는 정지 이미지로도 충분.
