from typing import Any, Mapping
import os
import json
import asyncio
import threading
import time
from collections import deque
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

FALLBACK_MODEL_PRIORITY = {
    "nvidia_nim": [
        {"provider": "nvidia_nim", "model": "nvidia/nemotron-3.5-lightning-30b-a3b"},
        {"provider": "nvidia_nim", "model": "nvidia/nemotron-3-super-120b-a12b"},
        {"provider": "nvidia_nim", "model": "meta/llama-3.1-70b-instruct"},
        {"provider": "nvidia_nim", "model": "openai/gpt-oss-20b"},
    ],
}

load_dotenv()

SUPPORTED_GEMINI_MODELS = {
    "gemini-3.1-pro-preview",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-3-flash-preview",
    "gemini-3.1-flash-lite",
    "gemini-2.5-flash-lite",
    "deep-research-preview-04-2026",
    "deep-research-max-preview-04-2026",
}

NIM_MODEL_INVENTORY_PATH = os.path.join("config", "nim_model_inventory.json")
NIM_RUNTIME_LOG_PATH = os.path.join("config", "nim_runtime_log.jsonl")
UNAVAILABLE_MODEL_PATH = os.path.join("config", "unavailable_models.json")

# LangChain 모델 객체는 provider 메타데이터를 공통으로 노출하지 않으므로
# 객체 id를 기준으로 호출 시 오류를 기록할 수 있게 합니다.
_MODEL_METADATA: dict[int, tuple[str, str]] = {}
_MODEL_LIMITERS: dict[int, "GeminiRateLimiter"] = {}
_MODEL_RATE_CONFIG: dict[int, dict[str, int]] = {}
_GEMINI_LIMITER: "GeminiRateLimiter | None" = None


class GeminiRateLimiter:
    """Sliding-window RPM/TPM limiter for one Gemini model instance."""

    def __init__(self, requests_per_minute: int, tokens_per_minute: int):
        if requests_per_minute < 1 or tokens_per_minute < 1:
            raise ValueError("Gemini RPM/TPM 제한은 1 이상이어야 합니다.")
        self.requests_per_minute = requests_per_minute
        self.tokens_per_minute = tokens_per_minute
        self._requests: deque[float] = deque()
        self._tokens: deque[tuple[float, int]] = deque()
        self._lock = threading.Lock()

    def acquire(self, estimated_tokens: int) -> None:
        """호출 전 최악의 토큰 사용량을 예약하고 필요하면 대기합니다."""
        tokens = max(1, estimated_tokens)
        if tokens > self.tokens_per_minute:
            raise ValueError(
                f"Gemini 호출 예상 토큰({tokens})이 TPM 제한({self.tokens_per_minute})을 초과합니다. "
                "max_input_tokens/max_output_tokens 또는 rate_limits.tokens_per_minute를 조정하세요."
            )
        while True:
            with self._lock:
                now = time.monotonic()
                cutoff = now - 60
                while self._requests and self._requests[0] <= cutoff:
                    self._requests.popleft()
                while self._tokens and self._tokens[0][0] <= cutoff:
                    self._tokens.popleft()

                used_tokens = sum(item[1] for item in self._tokens)
                if (
                    len(self._requests) < self.requests_per_minute
                    and used_tokens + tokens <= self.tokens_per_minute
                ):
                    self._requests.append(now)
                    self._tokens.append((now, tokens))
                    return

                wait_for = 1.0
                if self._requests and len(self._requests) >= self.requests_per_minute:
                    wait_for = max(wait_for, 60 - (now - self._requests[0]))
                if self._tokens and used_tokens + tokens > self.tokens_per_minute:
                    wait_for = max(wait_for, 60 - (now - self._tokens[0][0]))
            time.sleep(wait_for)


def _get_gemini_limiter(requests_per_minute: int, tokens_per_minute: int) -> GeminiRateLimiter:
    """모든 Gemini agent가 같은 프로젝트 quota를 공유하도록 제한기를 공유합니다."""
    global _GEMINI_LIMITER
    if _GEMINI_LIMITER is None:
        _GEMINI_LIMITER = GeminiRateLimiter(requests_per_minute, tokens_per_minute)
    else:
        _GEMINI_LIMITER.requests_per_minute = min(
            _GEMINI_LIMITER.requests_per_minute, requests_per_minute
        )
        _GEMINI_LIMITER.tokens_per_minute = min(
            _GEMINI_LIMITER.tokens_per_minute, tokens_per_minute
        )
    return _GEMINI_LIMITER


def _estimate_prompt_tokens(value: Any) -> int:
    """API 호출 전 보수적으로 문자열 입력을 토큰 수로 환산합니다."""
    if isinstance(value, Mapping):
        text = " ".join(str(item) for item in value.values())
    else:
        text = str(value)
    return max(1, (len(text) + 2) // 3)


def throttle_model_call(llm: Any, inputs: Any = None) -> None:
    metadata = model_metadata(llm)
    if metadata is None:
        return
    limiter = _MODEL_LIMITERS.get(id(llm))
    if limiter is None:
        return
    config = _MODEL_RATE_CONFIG.get(id(llm), {})
    max_output_tokens = int(config.get("max_output_tokens", 1024))
    max_input_tokens = int(config.get("max_input_tokens", 8000))
    limiter.acquire(max_input_tokens + max_output_tokens)


async def async_throttle_model_call(llm: Any, inputs: Any = None) -> None:
    """Async 호출에서 rate limiter의 대기가 event loop를 막지 않게 합니다."""
    await asyncio.to_thread(throttle_model_call, llm, inputs)


def load_unavailable_models() -> dict[str, set[str]]:
    """이전 실행에서 실제 호출 실패한 모델 목록을 읽습니다."""
    return _read_unavailable_model_ids()


def persist_unavailable_model(provider: str, model: str, reason: str) -> None:
    """실제 호출에 실패한 모델을 다음 실행에서도 제외하도록 기록합니다."""
    unavailable = load_unavailable_models()
    unavailable.setdefault(provider, set()).add(model)
    payload = {
        provider_name: {
            "models": sorted(models),
        }
        for provider_name, models in unavailable.items()
    }
    # 사람이 확인할 수 있도록 사유/시각도 함께 남기되 모델 목록은 안정적인 구조로 유지합니다.
    entry = payload.setdefault(provider, {"models": []})
    entry["models"] = sorted(unavailable[provider])
    entry["last_failure_reason"] = reason[:1000]
    entry["updated_at"] = datetime.now(timezone.utc).isoformat()
    os.makedirs(os.path.dirname(UNAVAILABLE_MODEL_PATH), exist_ok=True)
    with open(UNAVAILABLE_MODEL_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def _read_unavailable_model_ids() -> dict[str, set[str]]:
    """구버전 목록과 현재의 {models: [...]} 형식을 모두 읽습니다."""
    if not os.path.exists(UNAVAILABLE_MODEL_PATH):
        return {}
    with open(UNAVAILABLE_MODEL_PATH, "r", encoding="utf-8") as f:
        payload = json.load(f)
    result = {}
    for provider, value in (payload or {}).items():
        models = value.get("models", []) if isinstance(value, dict) else value
        if isinstance(models, list):
            result[str(provider)] = {str(model) for model in models}
    return result


def model_metadata(llm: Any) -> tuple[str, str] | None:
    return _MODEL_METADATA.get(id(llm))


def should_mark_model_unavailable(provider: str, exc: Exception) -> bool:
    """영구적인 모델/계정 불가 오류만 차단 목록에 추가합니다."""
    message = str(exc).lower()
    if "api_key_invalid" in message or "api key invalid" in message:
        return True
    if provider == "nvidia_nim":
        return "404" in message or "not found" in message or "model not found" in message
    if provider == "gemini":
        # Gemini는 계정별 모델 노출 차이로 400이 모델 불가를 의미할 수 있습니다.
        return "400" in message or "invalid_argument" in message
    return False


def record_model_failure(llm: Any, exc: Exception) -> None:
    metadata = model_metadata(llm)
    if metadata is None:
        return
    provider, model = metadata
    if should_mark_model_unavailable(provider, exc):
        persist_unavailable_model(provider, model, str(exc))
        print(f"[{provider}] '{model}'을 사용할 수 없는 모델 목록에 기록했습니다.")


def _require_api_key(agent_name: str, env_name: str) -> str:
    api_key = os.getenv(env_name)
    if not api_key:
        raise ValueError(
            f"[{agent_name}] {env_name} 환경변수가 비어 있습니다. "
            f"프로젝트 루트의 .env 파일에 {env_name}을 설정하세요."
        )
    return api_key


def _validate_base_url(agent_name: str, base_url: str | None) -> str:
    if not base_url:
        raise ValueError(
            f"[{agent_name}] base_url 설정이 없습니다. "
            "config/agents_config.yaml에서 해당 에이전트의 base_url을 설정하세요."
        )

    if not str(base_url).startswith("https://"):
        raise ValueError(
            f"[{agent_name}] base_url 형식이 올바르지 않습니다: {base_url}. "
            "https:// 로 시작해야 합니다."
        )

    return base_url


def _normalize_model_ref(value: Any, default_provider: str) -> tuple[str, str]:
    """모델 설정을 provider/model 쌍으로 정규화합니다."""
    if isinstance(value, str):
        return default_provider, value
    if isinstance(value, Mapping):
        provider = str(value.get("provider", default_provider)).lower()
        model = value.get("model")
        if isinstance(model, str) and model.strip():
            return provider, model.strip()
    raise ValueError(
        "모델 설정은 문자열 또는 {provider: ..., model: ...} 형식이어야 합니다."
    )


def extract_nim_model_ids(payload: Any) -> set[str]:
    """NVIDIA NIM의 /models 응답에서 모델 id를 추출합니다."""
    if payload is None:
        return set()

    items = payload.get("data", []) if isinstance(payload, dict) else payload
    found: set[str] = set()

    for item in items or []:
        if not isinstance(item, dict):
            continue
        for key in ("id", "model", "name"):
            value = item.get(key)
            if value and isinstance(value, str):
                found.add(value.strip())
    return {entry for entry in found if entry}


def persist_nim_model_inventory(base_url: str, available_models: set[str], *, error: str | None = None):
    """문제 재현을 위해 사용 가능한 NIM 모델 목록을 로컬 파일로 남깁니다."""
    os.makedirs(os.path.dirname(NIM_MODEL_INVENTORY_PATH), exist_ok=True)
    payload = {
        "base_url": base_url,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "available_models": sorted(available_models),
        "error": error,
    }
    with open(NIM_MODEL_INVENTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def fetch_nim_model_ids(base_url: str, api_key: str) -> set[str]:
    """NIM 모델 목록을 조회합니다. 호출이 실패하면 빈 집합을 반환합니다."""
    url = str(base_url).rstrip("/") + "/models"
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        response = requests.get(url, headers=headers, timeout=20)
        if response.status_code == 404:
            persist_nim_model_inventory(base_url, set(), error="404 model catalog not found")
            return set()
        response.raise_for_status()
        payload = response.json()
        models = extract_nim_model_ids(payload)
        persist_nim_model_inventory(base_url, models)
        return models
    except Exception as exc:
        persist_nim_model_inventory(base_url, set(), error=str(exc))
        return set()


def log_nim_runtime_event(agent_name: str, *, status: str, model: str, base_url: str, details: Mapping[str, Any] | None = None):
    """NIM 모델 선택 및 대체 로그를 남겨 운영 중 장애를 추적합니다."""
    os.makedirs(os.path.dirname(NIM_RUNTIME_LOG_PATH), exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agent_name": agent_name,
        "status": status,
        "model": model,
        "base_url": base_url,
        "details": dict(details or {}),
    }
    with open(NIM_RUNTIME_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def resolve_fallback_model(agent_name: str, provider: str, requested_model: str, available_models: set[str], configured_fallbacks: list[Any] | tuple[Any, ...] | None = None) -> str | None:
    """에이전트별 fallback 후보를 우선으로 사용 가능한 대체 모델을 선택합니다."""
    candidates: list[tuple[str, str, str]] = []
    if configured_fallbacks:
        candidates.extend(
            (candidate_provider, candidate_model, "agent-config")
            for candidate in configured_fallbacks
            for candidate_provider, candidate_model in [_normalize_model_ref(candidate, provider)]
        )

    if provider in FALLBACK_MODEL_PRIORITY:
        candidates.extend(
            (candidate_provider, candidate_model, "global-default")
            for candidate in FALLBACK_MODEL_PRIORITY[provider]
            for candidate_provider, candidate_model in [_normalize_model_ref(candidate, provider)]
        )

    seen = set()
    for candidate_provider, candidate, source in candidates:
        if candidate_provider != provider or candidate in seen or candidate == requested_model:
            continue
        seen.add(candidate)
        if candidate in available_models:
            log_nim_runtime_event(
                agent_name,
                status="fallback-selected",
                model=candidate,
                base_url=provider,
                details={"from_model": requested_model, "source": source, "provider": candidate_provider},
            )
            return candidate

    return None


def build_llm(
    *,
    agent_name: str,
    agent_config: Mapping[str, Any],
    default_model: str,
    temperature: float
) -> Any:
    provider = str(agent_config.get("provider", "openai_compatible")).lower()
    model_name = agent_config.get("model", default_model)

    if provider in {"openai_compatible", "nvidia_nim", "github_models"}:
        default_env_by_provider = {
            "openai_compatible": "OPENAI_API_KEY",
            "nvidia_nim": "NIM_API_KEY",
            "github_models": "GITHUB_TOKEN"
        }
        api_key_env = agent_config.get("api_key_env", default_env_by_provider[provider])
        api_key = _require_api_key(agent_name, api_key_env)

        default_base_url = "https://integrate.api.nvidia.com/v1" if provider == "nvidia_nim" else None
        base_url = _validate_base_url(agent_name, agent_config.get("base_url", default_base_url))

        if provider == "nvidia_nim":
            unavailable_models = load_unavailable_models().get(provider, set())
            if model_name in unavailable_models:
                fallback_candidates = agent_config.get("fallback_models", []) or []
                fallback_model = next(
                    (
                        candidate_model
                        for candidate in fallback_candidates
                        for candidate_provider, candidate_model in [_normalize_model_ref(candidate, provider)]
                        if candidate_provider == provider
                        and candidate_model not in unavailable_models
                        and candidate_model != model_name
                    ),
                    None,
                )
                if fallback_model:
                    print(f"[{agent_name}] '{model_name}'은 차단 목록에 있어 '{fallback_model}'로 fallback 합니다.")
                    model_name = fallback_model
                else:
                    raise ValueError(
                        f"[{agent_name}] NIM 모델 '{model_name}'은 이전 호출 실패로 차단되었습니다. "
                        f"{UNAVAILABLE_MODEL_PATH}를 확인하거나 사용 가능한 모델로 설정하세요."
                    )
            available_models = fetch_nim_model_ids(base_url, api_key)
            fallback_candidates = agent_config.get("fallback_models", []) or []
            if available_models:
                if model_name not in available_models:
                    fallback_model = resolve_fallback_model(
                        agent_name,
                        provider,
                        model_name,
                        available_models,
                        configured_fallbacks=fallback_candidates,
                    )
                    if fallback_model and fallback_model not in unavailable_models:
                        print(
                            f"[{agent_name}] WARNING: '{model_name}'은 사용 가능 목록에 없어 '{fallback_model}'로 fallback 합니다."
                        )
                        log_nim_runtime_event(
                            agent_name,
                            status="model-mismatch",
                            model=model_name,
                            base_url=base_url,
                            details={
                                "replaced_with": fallback_model,
                                "available_models": sorted(available_models)[:20],
                            },
                        )
                        model_name = fallback_model
                    else:
                        log_nim_runtime_event(
                            agent_name,
                            status="model-unavailable",
                            model=model_name,
                            base_url=base_url,
                            details={"available_models": sorted(available_models)[:20]},
                        )
                        raise ValueError(
                            f"[{agent_name}] NIM 모델 '{model_name}'은 현재 사용 가능한 모델 목록에 없습니다. "
                            f"사용 가능한 모델: {sorted(available_models)[:20]}"
                        )
            else:
                log_nim_runtime_event(
                    agent_name,
                    status="inventory-unavailable",
                    model=model_name,
                    base_url=base_url,
                    details={"note": "NIM model inventory could not be fetched"},
                )
                print(
                    f"[{agent_name}] WARNING: NIM 모델 목록을 확인할 수 없어 운영 중인 모델 검증을 건너뜁니다. "
                    f"(model={model_name}, base_url={base_url})"
                )

        llm = ChatOpenAI(
            model=model_name,
            temperature=temperature,
            api_key=api_key,
            base_url=base_url,
            max_tokens=int(agent_config.get("max_output_tokens", 4096)),
            max_retries=int(agent_config.get("max_retries", 2)),
            timeout=float(agent_config.get("timeout_seconds", 60)),
        )
        _MODEL_METADATA[id(llm)] = (provider, model_name)
        return llm

    if provider == "gemini":
        api_key_env = agent_config.get("api_key_env", "GEMINI_API_KEY")
        api_key = _require_api_key(agent_name, api_key_env)
        if model_name not in SUPPORTED_GEMINI_MODELS:
            raise ValueError(
                f"[{agent_name}] 지원되지 않는 Gemini 모델: '{model_name}'. "
                f"사용 가능한 모델: {sorted(SUPPORTED_GEMINI_MODELS)}"
            )
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
        except ImportError as exc:
            raise ValueError(
                "[gemini] langchain-google-genai 패키지가 필요합니다. "
                "requirements.txt 설치를 다시 수행하세요."
            ) from exc

        unavailable_models = load_unavailable_models().get(provider, set())
        if model_name in unavailable_models:
            raise ValueError(
                f"[{agent_name}] Gemini 모델 '{model_name}'은 이 계정에서 이전 호출 실패로 차단되었습니다. "
                f"{UNAVAILABLE_MODEL_PATH}를 확인하세요."
            )
        rate_config = agent_config.get("rate_limits", {}) or {}
        requests_per_minute = int(rate_config.get("requests_per_minute", 5))
        tokens_per_minute = int(rate_config.get("tokens_per_minute", 30000))
        llm = ChatGoogleGenerativeAI(
            model=model_name,
            temperature=temperature,
            google_api_key=api_key,
        )
        _MODEL_METADATA[id(llm)] = (provider, model_name)
        _MODEL_RATE_CONFIG[id(llm)] = {
            "max_input_tokens": int(agent_config.get("max_input_tokens", 8000)),
            "max_output_tokens": int(agent_config.get("max_output_tokens", 4096)),
        }
        _MODEL_LIMITERS[id(llm)] = _get_gemini_limiter(
            requests_per_minute=requests_per_minute,
            tokens_per_minute=tokens_per_minute,
        )
        return llm

    raise ValueError(
        f"[{agent_name}] 지원하지 않는 provider='{provider}'. "
        "허용값: openai_compatible, nvidia_nim, gemini, github_models"
    )
