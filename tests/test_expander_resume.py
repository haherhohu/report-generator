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


def test_process_single_section_skips_subtoc_already_in_final_report(monkeypatch):
    section_data = {
        "title": "2장 시장동향",
        "section_index": 2,
        "context_data": "시장 자료",
        "specific_instruction": "시장 동향을 작성하라",
    }
    state = {"section_final_paths": {"2장 시장동향": "/tmp/final_section.md"}}

    monkeypatch.setattr(expander_module, "read_text_if_exists", lambda path: "### 시장 규모\n\n이미 작성된 내용\n")
    monkeypatch.setattr(expander_module, "build_report_artifact_path", lambda *args, **kwargs: "/tmp/section_output.md")
    monkeypatch.setattr(expander_module, "save_file_append_only", lambda *args, **kwargs: "/tmp/section_output.md")
    monkeypatch.setattr(expander_module, "register_artifact", lambda *args, **kwargs: None)

    calls = {"count": 0}

    async def fake_ainvoke_prompt(*args, **kwargs):
        calls["count"] += 1
        if calls["count"] > 1:
            raise AssertionError("중복된 하위목차를 작성해서는 안 됩니다.")
        return type("Resp", (), {"content": '["시장 규모"]'})()

    monkeypatch.setattr(expander_module, "ainvoke_prompt", fake_ainvoke_prompt)

    result = asyncio.run(
        expander_module.process_single_section(
            section_data,
            "테스트 보고서",
            "기술 동향 분석",
            object(),
            "system prompt",
            asyncio.Semaphore(1),
            state,
        )
    )

    assert result["draft_path"] == "/tmp/section_output.md"
    assert result["content"] == ""
