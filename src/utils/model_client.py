from typing import Any, Mapping
import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

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

        return ChatOpenAI(
            model=model_name,
            temperature=temperature,
            api_key=api_key,
            base_url=base_url,
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
