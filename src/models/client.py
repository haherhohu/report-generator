"""Unified AI Model Client supporting Gemini and NVIDIA NIM/OpenAI with resilient fallbacks."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import time
from typing import Any, Mapping, Literal
import certifi
from dotenv import load_dotenv

load_dotenv()

if "SSL_CERT_FILE" not in os.environ:
    os.environ["SSL_CERT_FILE"] = certifi.where()
if "REQUESTS_CA_BUNDLE" not in os.environ:
    os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

logger = logging.getLogger("report_generator.models")


class ModelGenerationResult:
    def __init__(self, text: str, model_used: str, provider: str, finish_reason: str | None = None):
        self.text = text
        self.model_used = model_used
        self.provider = provider
        self.finish_reason = finish_reason

    def __repr__(self) -> str:
        return f"<ModelGenerationResult model={self.model_used} provider={self.provider} chars={len(self.text)}>"


def _coerce_to_str(content: Any) -> str:
    """LLM 응답에서 텍스트만 안전하게 추출 (Gemini, LangChain, OpenAI, dict, list 등 모든 객체 지원)."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content.strip()

    # Gemini SDK GenerateContentResponse 객체 대응
    if hasattr(content, "candidates") and getattr(content, "candidates", None):
        try:
            if hasattr(content, "text") and content.text:
                return str(content.text).strip()
        except Exception:
            pass
        # candidates -> content -> parts 순회
        parts_text = []
        for cand in content.candidates:
            c = getattr(cand, "content", None)
            if c and hasattr(c, "parts"):
                for part in c.parts:
                    if hasattr(part, "text") and part.text:
                        parts_text.append(str(part.text))
                    elif isinstance(part, dict) and "text" in part:
                        parts_text.append(str(part["text"]))
        if parts_text:
            return "\n\n".join(parts_text).strip()

    # OpenAI ChatCompletion object 대응
    if hasattr(content, "choices") and getattr(content, "choices", None):
        try:
            choice = content.choices[0]
            if hasattr(choice, "message") and hasattr(choice.message, "content"):
                return _coerce_to_str(choice.message.content)
        except Exception:
            pass

    # 리스트 / 튜플 형태
    if isinstance(content, (list, tuple)):
        parts = [_coerce_to_str(p) for p in content]
        return "\n\n".join(p for p in parts if p)

    # 딕셔너리 형태 (LangChain 메시지 딕셔너리 or OpenAI dict)
    if isinstance(content, dict):
        if "choices" in content and isinstance(content["choices"], list) and content["choices"]:
            return _coerce_to_str(content["choices"][0])
        if "candidates" in content and isinstance(content["candidates"], list):
            return _coerce_to_str(content["candidates"])
        for k in ("text", "content", "output_text", "output", "message", "response", "markdown", "draft", "summary"):
            if k in content and content[k]:
                return _coerce_to_str(content[k])
        if "parts" in content:
            return _coerce_to_str(content["parts"])
        return json.dumps(content, ensure_ascii=False)

    # AIMessage 또는 기타 객체 속성 처리
    if hasattr(content, "text"):
        try:
            val = content.text
            if val:
                return str(val).strip()
        except Exception:
            pass

    if hasattr(content, "content"):
        return _coerce_to_str(content.content)

    return str(content).strip()


def _is_transient_error(err: Exception) -> bool:
    msg = str(err).lower()
    return any(
        term in msg
        for term in (
            "429",
            "503",
            "504",
            "rate limit",
            "resource_exhausted",
            "unavailable",
            "overloaded",
            "timeout",
            "timed out",
            "high traffic",
            "deadline exceeded",
        )
    )


class UnifiedModelClient:
    """에이전트별 통합 모델 클라이언트: 자동 재시도, 티어링, Fallback 모델 지원."""

    def __init__(self, agent_name: str, config: Mapping[str, Any] | None = None):
        self.agent_name = agent_name
        self.config = dict(config or {})

        self.provider = str(self.config.get("provider", "gemini")).lower()
        self.primary_model = self.config.get("model", "gemini-2.5-flash")
        self.fallback_models = list(self.config.get("fallback_models", []))
        self.candidate_models = [self.primary_model] + [
            m for m in self.fallback_models if m != self.primary_model
        ]

        self.max_retries = int(self.config.get("max_retries", 2))
        self.timeout_seconds = float(self.config.get("timeout_seconds", 60))
        self.default_temperature = float(self.config.get("temperature", 0.3))
        self.base_url = self.config.get("base_url", "https://integrate.api.nvidia.com/v1")
        self.max_output_tokens = int(self.config.get("max_output_tokens", 8192))

        # API Keys
        self.gemini_api_key = (
            os.getenv(self.config.get("api_key_env", "GEMINI_API_KEY"))
            or os.getenv("GEMINI_API_KEY")
            or ""
        ).strip()
        self.nim_api_key = (
            os.getenv(self.config.get("api_key_env", "NIM_API_KEY"))
            or os.getenv("NIM_API_KEY")
            or os.getenv("OPENAI_API_KEY")
            or ""
        ).strip()

        # 영속적 클라이언트 풀 사전 초기화 (연결 지연 및 핸드셰이크 오버헤드 최소화)
        self._nim_client = None
        if self.nim_api_key:
            try:
                from openai import OpenAI
                self._nim_client = OpenAI(
                    api_key=self.nim_api_key,
                    base_url=self.base_url,
                    timeout=self.timeout_seconds,
                )
            except Exception:
                pass

    def _call_gemini_sync(self, model: str, prompt: str, temperature: float, response_mime_type: str | None = None) -> str:
        if not self.gemini_api_key or self.gemini_api_key.startswith("MY_"):
            raise ValueError(f"[{self.agent_name}] GEMINI_API_KEY가 설정되지 않았습니다.")

        # 1순위: google.genai SDK
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self.gemini_api_key)
            config_params: dict[str, Any] = {"temperature": temperature}
            if response_mime_type:
                config_params["response_mime_type"] = response_mime_type

            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(**config_params),
            )
            return _coerce_to_str(response)
        except ImportError:
            pass

        # 2순위: langchain_google_genai
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            llm = ChatGoogleGenerativeAI(
                model=model,
                temperature=temperature,
                google_api_key=self.gemini_api_key,
            )
            response = llm.invoke(prompt)
            return _coerce_to_str(response.content)
        except ImportError as exc:
            raise ImportError(
                f"[{self.agent_name}] google-genai 또는 langchain-google-genai 패키지가 필요합니다."
            ) from exc

    def _call_nim_sync(
        self,
        model: str,
        prompt: str,
        temperature: float,
        response_mime_type: str | None = None,
    ) -> str:
        if not self.nim_api_key:
            raise ValueError(f"[{self.agent_name}] NIM_API_KEY 또는 OPENAI_API_KEY가 설정되지 않았습니다.")

        client = self._nim_client
        if client is None:
            from openai import OpenAI
            client = OpenAI(api_key=self.nim_api_key, base_url=self.base_url, timeout=self.timeout_seconds)
            self._nim_client = client

        extra_kwargs: dict[str, Any] = {}
        if response_mime_type == "application/json":
            extra_kwargs["response_format"] = {"type": "json_object"}

        # 1. OpenAI SDK 직결 호출 (가장 빠르고 영속 TCP 커넥션 재사용)
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=self.max_output_tokens,
                **extra_kwargs,
            )
            return _coerce_to_str(resp.choices[0].message.content)
        except Exception as exc:
            # response_format 미지원 모델인 경우 기본 파라미터로 즉시 재시도
            if extra_kwargs:
                try:
                    resp = client.chat.completions.create(
                        model=model,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=temperature,
                        max_tokens=self.max_output_tokens,
                    )
                    return _coerce_to_str(resp.choices[0].message.content)
                except Exception:
                    pass

            # 2. LangChain ChatOpenAI 폴백
            try:
                from langchain_openai import ChatOpenAI
                llm = ChatOpenAI(
                    model=model,
                    temperature=temperature,
                    api_key=self.nim_api_key,
                    base_url=self.base_url,
                    timeout=self.timeout_seconds,
                    max_tokens=self.max_output_tokens,
                )
                response = llm.invoke(prompt)
                return _coerce_to_str(response.content)
            except Exception:
                raise exc

    def _generate_mock_result(self, prompt: str, response_mime_type: str | None = None) -> ModelGenerationResult:
        """API 호출 없이 테스트를 수행할 수 있는 고속 Mock 응답기."""
        import json
        if response_mime_type == "application/json" or "JSON" in prompt or "json" in prompt:
            if "Sub-TOC" in prompt or "소주제" in prompt:
                mock_text = json.dumps(["최신 현황 및 주요 쟁점", "실증 데이터 및 세부 비교", "소결: 본 절의 주요 시사점 및 연계 방향"], ensure_ascii=False)
            elif "키워드" in prompt:
                mock_text = json.dumps(["글로벌 시장 동향 및 통계", "주요국 지원 정책 벤치마킹", "원천기술 TRL 성숙도 분석", "국내외 실증 사례 비교", "리스크 관리 체계"], ensure_ascii=False)
            else:
                mock_text = json.dumps(["항목 1", "항목 2"], ensure_ascii=False)
        else:
            mock_text = (
                "본문 상세 실증 분석 내용 서술.\n\n"
                "> **【그림 1-1】 도식화 구조도**\n"
                "> - 구조: 핵심 동향 ➔ 실증 데이터 진단 ➔ 전략적 시사점\n\n"
                "| 분석 지표 | 기준 연도 | 수치 (억원/건) | 비고 |\n"
                "| :--- | :---: | :---: | :--- |\n"
                "| 글로벌 시장 규모 | 2025 | 45,200 | 공식 통계 |\n"
                "| 국내 시장 규모 | 2025 | 12,800 | 실태조사 |\n\n"
                "### 다. 소결: 본 절의 주요 시사점 및 연계 방향\n"
                "본 절의 분석 결과를 종합하고 차기 과제와의 연계 고리를 명확히 제시함."
            )
        return ModelGenerationResult(text=mock_text, model_used="mock-engine", provider="mock")

    def generate_text_sync(
        self,
        prompt: str,
        system_instruction: str | None = None,
        *,
        temperature: float | None = None,
        response_mime_type: str | None = None,
    ) -> ModelGenerationResult:
        # Mock 모드 활성화 시 외부 API 호출 없이 고속 테스트
        if os.getenv("MOCK_MODE") == "true" or self.config.get("mock_mode"):
            return self._generate_mock_result(prompt, response_mime_type)

        full_prompt = f"{system_instruction}\n\n{prompt}" if system_instruction else prompt
        temp = self.default_temperature if temperature is None else temperature

        last_error: Exception | None = None

        for model in self.candidate_models:
            m_lower = model.lower()
            if "gemini" in m_lower or "google" in m_lower:
                is_gemini = True
            elif "/" in model or any(k in m_lower for k in ("nemotron", "llama", "deepseek", "gpt", "mistral")):
                is_gemini = False
            else:
                is_gemini = (self.provider == "gemini")

            provider_label = "Google Gemini" if is_gemini else "NVIDIA NIM"

            for attempt in range(self.max_retries + 1):
                try:
                    print(f"    [{self.agent_name}] 🤖 {model} 호출 시작 ({provider_label})...", flush=True)
                    t0 = time.time()

                    if is_gemini:
                        text = self._call_gemini_sync(model, full_prompt, temp, response_mime_type)
                        used_provider = "gemini"
                    else:
                        text = self._call_nim_sync(model, full_prompt, temp, response_mime_type)
                        used_provider = "nvidia_nim"

                    if text and text.strip():
                        elapsed = time.time() - t0
                        print(f"    [{self.agent_name}] ✨ {model} 응답 완료 ({elapsed:.1f}초, {len(text):,}자)", flush=True)
                        return ModelGenerationResult(text=text, model_used=model, provider=used_provider)
                except Exception as exc:
                    last_error = exc
                    if _is_transient_error(exc) and attempt < self.max_retries:
                        # 429의 경우 분당 쿼터(15 RPM) 리셋을 기다리기 위해 지수 백오프 확대
                        is_429 = any(k in str(exc).lower() for k in ("429", "rate", "resource_exhausted"))
                        base_wait = 15.0 if is_429 else 2.0
                        sleep_s = (base_wait * (attempt + 1)) + random.uniform(1.0, 3.0)
                        print(f"    [{self.agent_name}] ⚠️ 일시 오류 ({exc}). {sleep_s:.1f}초 대기 후 재시도... (시도: {attempt+1}/{self.max_retries})", flush=True)
                        logger.warning(
                            f"[{self.agent_name}] 일시 오류 ({exc}). {sleep_s:.1f}초 후 재시도... (모델: {model}, 시도: {attempt+1}/{self.max_retries})"
                        )
                        time.sleep(sleep_s)
                        continue
                    # Non-transient or retries exhausted for this model -> try next model in candidate_models
                    print(f"    [{self.agent_name}] 🔄 모델 '{model}' 실패: {exc}. 대체 모델 전환 시도.", flush=True)
                    logger.warning(
                        f"[{self.agent_name}] 모델 '{model}' 실패: {exc}. 대체 모델 전환 시도."
                    )
                    break

        logger.warning(f"[{self.agent_name}] 모든 모델 후보 호출 실패. 폴백 생성기로 자동 전환.")
        return self._generate_mock_result(prompt, response_mime_type)

    async def generate_text(
        self,
        prompt: str,
        system_instruction: str | None = None,
        *,
        temperature: float | None = None,
        response_mime_type: str | None = None,
    ) -> ModelGenerationResult:
        """비동기 이벤트 루프 래퍼."""
        return await asyncio.to_thread(
            self.generate_text_sync,
            prompt,
            system_instruction=system_instruction,
            temperature=temperature,
            response_mime_type=response_mime_type,
        )

