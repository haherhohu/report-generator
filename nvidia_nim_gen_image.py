import base64
import os

import requests

# 1. 환경 설정 (NVIDIA NIM API 키 설정)
# 로컬 NIM 서버라면 주소를 "http://localhost:8000/v1/images/generations" 형태로 바꾸세요.
API_URL = "https://ai.api.nvidia.com/v1/genai/black-forest-labs/flux.2-klein-4b"
API_KEY = os.environ.get(
    "NVIDIA_API_KEY",
    "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",
)

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
    "Accept": "application/json",
}

# 2. flux.2-klein-4b 최적화 페이로드 설정
payload = {
    #    "prompt": "A futuristic workspace with dual monitors, glowing mechanical keyboard, minimalist setup, cinematic lighting, 8k resolution, highly detailed",
    "prompt": "macro wildlife photo of a green frog in a rainforest pond, highly detailed, eye-level shot",
    "width": 1024,
    "height": 1024,
    "seed": 0,
    "steps": 4,  # schnell 모델은 4스텝이 표준이자 맥스 효율입니다.
}

print("🎨 flux.2-klein-4b 모델로 이미지 생성을 요청 중입니다...")

try:
    response = requests.post(API_URL, headers=headers, json=payload)
    response.raise_for_status()  # 에러 발생 시 예외 발생

    response_data = response.json()
    # 응답출력
    # print(response_data)
    # 3. 리턴된 Base64 데이터를 이미지 파일로 변환 및 저장
    image_base64 = response_data["artifacts"][0]["base64"]
    image_data = base64.b64decode(image_base64)

    output_filename = "flux_output.png"
    with open(output_filename, "wb") as f:
        f.write(image_data)

    print(f"✨ 이미지 생성 성공! '{output_filename}' 파일로 저장되었습니다.")

except requests.exceptions.HTTPError as http_err:
    print(f"❌ HTTP 에러 발생: {http_err}")
    print(f"서버 응답 내용: {response.text}")
except Exception as e:
    print(f"❌ 오류 발생: {e}")
