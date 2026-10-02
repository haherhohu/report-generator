# 앞으로 할 작업 계획임

일단 서버에 vllm 기반으로 다음 모델 설치할 예정:
솔직히 잘 해준다기 보다는 40기가를 거의 한계까지 올리는 방식임.

- Llama 3.1 8B (4.9G) (8B 순정)
- llama3.1-8b-abliterated:tools-q8_0 (8G uncensored, 8비트 양자화 모델)
- Gemma 4 26B A4B (Q4) (17-18G) → dense 모델은 아니라서 대답이 빠르대 이거 추천하네 (사실 이걸 상시서빙용으로 둬도…)
- FLUX.2 -klein (9b - 12G)
- FLUX.2 -klein (f16 - 16G) - uncensored
- Codestral 22B (Q6_K) (13G) → 미스트랄의 코딩전용
