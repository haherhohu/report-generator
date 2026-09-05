"""Unit tests for final shield and deduplication logic."""
from pathlib import Path
from src.utils.final_guard import should_reuse_or_create_final


def test_should_reuse_or_create_final_trigger_duplicate(tmp_path):
    paths = []
    for i in range(5):
        p = tmp_path / f"test_note_{i}.md"
        p.write_text(f"# 시장 동향 {i}\n\n내용입니다 {i}\n", encoding="utf-8")
        paths.append(str(p))

    state = {
        "artifact_history": [
            {"title": "시장 동향", "type": "research-note", "path": p}
            for p in paths
        ]
    }

    res = should_reuse_or_create_final(
        state,
        title="시장 동향",
        related_paths=paths,
        duplicate_threshold=5,
        summary_only=True,
    )

    assert res["triggered_duplicate"] is True
    assert "시장 동향 최종본" in res["content"]


def test_should_reuse_or_create_final_reusing_existing(tmp_path):
    final_file = tmp_path / "final_report.md"
    final_file.write_text("# 시장 동향 최종본\n\n기존 최종본 재사용\n", encoding="utf-8")

    state = {
        "artifact_history": [
            {"title": "시장 동향", "type": "final-report", "path": str(final_file)}
        ]
    }

    res = should_reuse_or_create_final(
        state,
        title="시장 동향",
        related_paths=[str(final_file)],
        duplicate_threshold=5,
    )

    assert res["used_final"] is True
    assert res["path"] == str(final_file)

