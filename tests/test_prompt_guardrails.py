from src.utils.model_client import extract_nim_model_ids
from src.utils.prompting import trim_prompt_context


def test_extract_nim_model_ids_handles_nim_payloads():
    payload = {
        "data": [
            {"id": "nvidia/nemotron-3-super-120b-a12b"},
            {"model": "meta/llama-3.1-70b-instruct"},
            {"name": "openai/gpt-oss-20b"},
        ]
    }

    assert extract_nim_model_ids(payload) == {
        "nvidia/nemotron-3-super-120b-a12b",
        "meta/llama-3.1-70b-instruct",
        "openai/gpt-oss-20b",
    }


def test_trim_prompt_context_keeps_required_instruction_text():
    direction = "핵심 방향성: 정책 보고서를 공식적이고 구체적으로 작성하라."
    instruction = "사용자 지시사항: 1. 공식적 톤, 2. 근거를 제시"
    context = "x" * 20000
    trimmed = trim_prompt_context(
        context,
        max_chars=500,
        required_fragments=[direction, instruction],
    )

    assert direction in trimmed
    assert instruction in trimmed
    assert len(trimmed) <= 2000
