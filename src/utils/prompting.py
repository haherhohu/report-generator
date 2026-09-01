from __future__ import annotations

from typing import Any

from langchain_core.prompts import ChatPromptTemplate


def estimate_context_budget(max_input_tokens: int | str | None, default: int = 8000) -> int:
    """설정값을 안전한 문자 예산으로 환산합니다."""
    try:
        cap = int(max_input_tokens) if max_input_tokens is not None else default
    except (TypeError, ValueError):
        cap = default
    return max(2000, cap)


def trim_prompt_context(
    text: str | None,
    *,
    max_chars: int = 8000,
    required_fragments: list[str] | tuple[str, ...] = (),
) -> str:
    """사용자 지시사항이 사라지지 않도록 보존하면서 컨텍스트를 잘라냅니다."""
    if text is None:
        return ""

    normalized_text = str(text).strip()
    if not normalized_text:
        return ""

    required = [fragment.strip() for fragment in required_fragments if fragment and str(fragment).strip()]
    preserved = "\n\n".join(required)

    base_text = normalized_text
    for fragment in required:
        if fragment in base_text:
            base_text = base_text.replace(fragment, "")

    collapsed = "\n".join(part.strip() for part in base_text.splitlines() if part.strip())
    if len(collapsed) <= max_chars:
        result = collapsed
    else:
        tail_budget = max(0, max_chars - 200)
        if tail_budget <= 0:
            result = collapsed[:max_chars]
        else:
            result = collapsed[-tail_budget:]

    if required:
        return f"{preserved}\n\n[참고 컨텍스트 일부]\n{result.strip()}"
    return result.strip()


def invoke_prompt(llm, system_prompt: str | None, human_template: str, **kwargs: Any):
    """반복되는 system/human 프롬프트 패턴을 하나의 helper로 통일합니다."""
    messages = []
    if system_prompt:
        messages.append(("system", system_prompt))
    messages.append(("human", human_template))
    prompt = ChatPromptTemplate.from_messages(messages)
    return (prompt | llm).invoke(kwargs)


async def ainvoke_prompt(llm, system_prompt: str | None, human_template: str, **kwargs: Any):
    """Async 호출용 프롬프트 helper."""
    messages = []
    if system_prompt:
        messages.append(("system", system_prompt))
    messages.append(("human", human_template))
    prompt = ChatPromptTemplate.from_messages(messages)
    return await (prompt | llm).ainvoke(kwargs)
