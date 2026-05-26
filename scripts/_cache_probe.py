"""일회성 캐싱 검증 — 동일 시스템 프롬프트로 2회 호출, 캐시 토큰 확인."""
import os, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

# .env 로드
try:
    from dotenv import load_dotenv
    load_dotenv(pathlib.Path(__file__).resolve().parents[1] / ".env")
except Exception as e:
    print("dotenv load 경고:", e)

from agents.curriculum import CurriculumArchitect

agent = CurriculumArchitect()
sys_param = agent._build_system()
print("model:", agent.model)
print("system 블록 타입:", type(sys_param).__name__,
      "| 캐시마크:", sys_param[0].get("cache_control") if isinstance(sys_param, list) else "(문자열)")
print("-" * 60)

for i in (1, 2):
    msg = agent.client.messages.create(
        model=agent.model, max_tokens=10, system=sys_param,
        messages=[{"role": "user", "content": "한 단어로 답해: 1+1?"}],
    )
    u = msg.usage
    cc = getattr(u, "cache_creation_input_tokens", 0) or 0
    cr = getattr(u, "cache_read_input_tokens", 0) or 0
    print(f"[{i}회차] input={u.input_tokens}  cache_creation={cc}  "
          f"cache_read={cr}  output={u.output_tokens}")

print("-" * 60)
print("판정: 2회차 cache_read>0 이면 ✅ 캐싱 작동. cache_creation/read 모두 0이면 "
      "시스템 프롬프트가 최소 토큰(1024) 미만 → 캐싱 미발동(코드는 정상, API가 무시).")
