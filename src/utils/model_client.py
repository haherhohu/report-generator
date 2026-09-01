from typing import Any, Mapping
import os
import json
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

FALLBACK_MODEL_PRIORITY = {
    "nvidia_nim": [
        "nvidia/nemotron-3.5-lightning-30b-a3b",
        "google/gemma-4-31b-it",
        "nvidia/nemotron-3-super-120b-a12b",
        "meta/llama-3.1-70b-instruct",
        "openai/gpt-oss-20b",
    ],
}

load_dotenv()

SUPPORTED_GEMINI_MODELS = {
    "gemini-3.1-pro-preview",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-3-flash-preview",
    "gemini-3.1-flash-lite",
    "deep-research-preview-04-2026",
    "deep-research-max-preview-04-2026",
}

NIM_MODEL_INVENTORY_PATH = os.path.join("config", "nim_model_inventory.json")
NIM_RUNTIME_LOG_PATH = os.path.join("config", "nim_runtime_log.jsonl")


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


def resolve_fallback_model(agent_name: str, provider: str, requested_model: str, available_models: set[str], configured_fallbacks: list[str] | tuple[str, ...] | None = None) -> str | None:
    """에이전트별 fallback 후보를 우선으로 사용 가능한 대체 모델을 선택합니다."""
    candidates = []
    if configured_fallbacks:
        candidates.extend(configured_fallbacks)

    if provider in FALLBACK_MODEL_PRIORITY:
        candidates.extend(FALLBACK_MODEL_PRIORITY[provider])

    seen = set()
    for candidate in candidates:
        if candidate in seen or candidate == requested_model:
            continue
        seen.add(candidate)
        if candidate in available_models:
            log_nim_runtime_event(
                agent_name,
                status="fallback-selected",
                model=candidate,
                base_url="nvidia_nim",
                details={"from_model": requested_model, "source": "agent-config" if candidate in (configured_fallbacks or []) else "global-default"},
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
                    if fallback_model:
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

        return ChatOpenAI(
            model=model_name,
            temperature=temperature,
            api_key=api_key,
            base_url=base_url,
            max_tokens=int(agent_config.get("max_output_tokens", 4096)),
            max_retries=int(agent_config.get("max_retries", 2)),
            timeout=float(agent_config.get("timeout_seconds", 60)),
        )

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

        return ChatGoogleGenerativeAI(
            model=model_name,
            temperature=temperature,
            google_api_key=api_key,
        )

    raise ValueError(
        f"[{agent_name}] 지원하지 않는 provider='{provider}'. "
        "허용값: openai_compatible, nvidia_nim, gemini, github_models"
    )
