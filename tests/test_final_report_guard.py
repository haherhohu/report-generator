from src.utils.final_report_guard import should_reuse_or_create_final


def test_should_reuse_or_create_final_when_same_title_is_repeated(tmp_path):
    paths = []
    for i in range(5):
        path = tmp_path / f"section_{i}.md"
        path.write_text(f"# 시장 동향 {i}\n\n중복 문단 A. 시장은 성장한다.\n", encoding="utf-8")
        paths.append(str(path))

    state = {"artifact_history": [{"title": "시장 동향", "type": "research-note", "path": p} for p in paths]}

    result = should_reuse_or_create_final(
        state,
        title="시장 동향",
        related_paths=paths,
        duplicate_threshold=5,
        summary_only=True,
    )

    assert result["triggered_duplicate"] is True
    assert "시장 동향 최종본" in result["content"]


def test_should_reuse_or_create_final_when_final_exists(tmp_path):
    final_path = tmp_path / "market_final.md"
    final_path.write_text("# 시장 동향 최종본\n\n기존 최종본 사용\n", encoding="utf-8")

    state = {
        "artifact_history": [{"title": "시장 동향", "type": "final-report", "path": str(final_path)}],
    }

    result = should_reuse_or_create_final(
        state,
        title="시장 동향",
        related_paths=[str(final_path)],
        duplicate_threshold=5,
        summary_only=True,
    )

    assert result["used_final"] is True
    assert result["path"] == str(final_path)
