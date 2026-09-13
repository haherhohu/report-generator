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


def test_clean_junk_reference_files(tmp_path):
    from src.utils.final_guard import clean_junk_reference_files

    ref_dir = tmp_path / "reference"
    ref_dir.mkdir()
    archive_dir = ref_dir / ".junk_archive"

    # 정상 파일 생성
    good_file = ref_dir / "good_research.md"
    good_file.write_text(
        "## 정상 조사보고서\n\n글로벌 AI 동향에 대한 구체적인 수치와 배경을 상세히 서술함.\n" * 5,
        encoding="utf-8",
    )

    # 불량 파일 생성 (SSL 오류 문구)
    junk_file = ref_dir / "junk_research.md"
    junk_file.write_text(
        "본 보고서는 조사를 시도했으나 SSL 인증 오류로 인해 데이터를 가져오지 못함.",
        encoding="utf-8",
    )

    cleaned = clean_junk_reference_files(ref_dir, archive_dir)
    assert len(cleaned) == 1
    assert cleaned[0]["filename"] == "junk_research.md"

    # 정상 파일은 유지되고 불량 파일은 아카이브 폴더로 이동 확인
    assert good_file.exists()
    assert not junk_file.exists()
    assert (archive_dir / "junk_research.md").exists()


