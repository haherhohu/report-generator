"""Unified AI Model Client supporting Gemini and NVIDIA NIM/OpenAI with resilient fallbacks."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import time
from typing import Any, Mapping, Literal
from dotenv import load_dotenv

load_dotenv()

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

    def _call_nim_sync(self, model: str, prompt: str, temperature: float) -> str:
        if not self.nim_api_key:
            raise ValueError(f"[{self.agent_name}] NIM_API_KEY 또는 OPENAI_API_KEY가 설정되지 않았습니다.")

        base_url = self.config.get("base_url", "https://integrate.api.nvidia.com/v1")
        try:
            from langchain_openai import ChatOpenAI
            llm = ChatOpenAI(
                model=model,
                temperature=temperature,
                api_key=self.nim_api_key,
                base_url=base_url,
                timeout=self.timeout_seconds,
            )
            response = llm.invoke(prompt)
            return _coerce_to_str(response.content)
        except ImportError:
            from openai import OpenAI
            client = OpenAI(api_key=self.nim_api_key, base_url=base_url, timeout=self.timeout_seconds)
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
            )
            return _coerce_to_str(resp.choices[0].message.content)

    def generate_text_sync(
        self,
        prompt: str,
        system_instruction: str | None = None,
        *,
        temperature: float | None = None,
        response_mime_type: str | None = None,
    ) -> ModelGenerationResult:
        full_prompt = f"{system_instruction}\n\n{prompt}" if system_instruction else prompt
        temp = self.default_temperature if temperature is None else temperature

        last_error: Exception | None = None

        for model in self.candidate_models:
            is_gemini = "gemini" in model.lower() or self.provider == "gemini"

            for attempt in range(self.max_retries + 1):
                try:
                    if is_gemini:
                        text = self._call_gemini_sync(model, full_prompt, temp, response_mime_type)
                        used_provider = "gemini"
                    else:
                        text = self._call_nim_sync(model, full_prompt, temp)
                        used_provider = "nvidia_nim"

                    if text and text.strip():
                        return ModelGenerationResult(text=text, model_used=model, provider=used_provider)
                except Exception as exc:
                    last_error = exc
                    if _is_transient_error(exc) and attempt < self.max_retries:
                        sleep_s = (2 ** attempt) + random.uniform(0.5, 1.5)
                        logger.warning(
                            f"[{self.agent_name}] 일시 오류 ({exc}). {sleep_s:.1f}초 후 재시도... (모델: {model}, 시도: {attempt+1})"
                        )
                        time.sleep(sleep_s)
                        continue
                    # Non-transient or retries exhausted for this model -> try next model in candidate_models
                    logger.warning(
                        f"[{self.agent_name}] 모델 '{model}' 실패: {exc}. 대체 모델 전환 시도."
                    )
                    break

        raise last_error or RuntimeError(f"[{self.agent_name}] 모든 모델 후보 호출 실패.")

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

