import asyncio
from pathlib import Path

from src.agents import expander as expander_module


def test_run_expander_skips_completed_sections_with_normalized_titles(monkeypatch):
    state = {
        "topic": "테스트 보고서",
        "direction": "기술 동향 분석",
        "sections": [
            {"title": "1. 서론", "section_index": 1},
            {"title": "2. 필요성", "section_index": 2},
        ],
        "completed_sections": [" 1. 서론 ", "3. 사례 연구"],
        "max_concurrency": 2,
    }

    monkeypatch.setattr(expander_module, "map_references_to_sections", lambda *args, **kwargs: state["sections"])
    monkeypatch.setattr(expander_module, "build_llm", lambda *args, **kwargs: object())
    monkeypatch.setattr(Path, "read_text", lambda *args, **kwargs: "dummy")

    called_titles = []

    async def fake_process(section_data, *args, **kwargs):
        called_titles.append(section_data["title"])
        return {"title": section_data["title"], "section_index": section_data.get("section_index", 99), "content": "ok"}

    monkeypatch.setattr(expander_module, "process_single_section", fake_process)
    monkeypatch.setattr(expander_module.yaml, "safe_load", lambda *args, **kwargs: {"expander": {"model": "gpt-4o"}})

    result = asyncio.run(expander_module.run_expander_async(state))

    assert "1. 서론" not in called_titles
    assert "2. 필요성" in called_titles
    assert set(result["completed_sections"]) == {"1. 서론", "3. 사례 연구", "2. 필요성"}
