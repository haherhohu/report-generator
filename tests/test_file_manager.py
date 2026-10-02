"""Unit tests for file manager phase-based naming (p1~p5) and final tagging with v1..vn versioning."""
import os
import shutil
import tempfile
from pathlib import Path

from src.utils.file_manager import (
    build_report_artifact_path,
    normalize_phase,
    next_versioned_path,
    save_file_append_only,
    get_existing_artifact_versions,
    get_latest_artifact_path,
)


def test_normalize_phase():
    # Legacy phase mapping
    assert normalize_phase("v1") == "p1"
    assert normalize_phase("v2") == "p2"
    assert normalize_phase("draft") == "p1"
    assert normalize_phase("outline") == "p1"
    assert normalize_phase("v3") == "p3"
    assert normalize_phase("section") == "p3"
    assert normalize_phase("expanded") == "p3"
    assert normalize_phase("v3_final") == "p5"

    # Standard phase tags (p1 ~ p5)
    assert normalize_phase("p1") == "p1"
    assert normalize_phase("p2") == "p2"
    assert normalize_phase("p3") == "p3"
    assert normalize_phase("p4") == "p4"
    assert normalize_phase("p5") == "p5"

    # Reference / other
    assert normalize_phase("research") == "research"


def test_build_report_artifact_path_phases_and_final_tag():
    with tempfile.TemporaryDirectory() as tmpdir:
        topic = "AI 동향"

        # 1. Phase p1 (기초 초안 작성) v1 생성
        p1_v1 = build_report_artifact_path(topic, "p1", base_dir=tmpdir)
        assert p1_v1.endswith("AI_동향_p1_v1.md")
        saved_p1_1 = save_file_append_only(p1_v1, "# 초안 1차")
        assert os.path.exists(saved_p1_1)

        # Phase p1 새 버전 요청 시 v2 생성
        p1_v2 = build_report_artifact_path(topic, "p1", base_dir=tmpdir)
        assert p1_v2.endswith("AI_동향_p1_v2.md")

        # 2. Phase p2 (사용자 기초자료 반영 초안) v1 생성
        p2_v1 = build_report_artifact_path(topic, "p2", base_dir=tmpdir)
        assert p2_v1.endswith("AI_동향_p2_v1.md")
        saved_p2_1 = save_file_append_only(p2_v1, "# 자료반영 초안 1차")
        assert os.path.exists(saved_p2_1)

        # 3. Phase p3 (각 챕터별 중간본) 섹션 v1 생성
        p3_sec1 = build_report_artifact_path(topic, "p3", section_title="1.1 기술 개요", base_dir=tmpdir)
        assert p3_sec1.endswith("AI_동향_p3_1.1_기술_개요_v1.md")
        saved_sec1 = save_file_append_only(p3_sec1, "## 1.1 기술 개요 본문")
        assert os.path.exists(saved_sec1)

        # 4. Phase p4 (검증 및 정제) 섹션 v1 생성
        p4_sec1 = build_report_artifact_path(topic, "p4", section_title="1.1 기술 개요", base_dir=tmpdir)
        assert p4_sec1.endswith("AI_동향_p4_1.1_기술_개요_v1.md")
        saved_p4_1 = save_file_append_only(p4_sec1, "## 1.1 기술 개요 검증본")
        assert os.path.exists(saved_p4_1)

        # 5. Phase p5 (취합 및 최종 완성본) -> 시각적으로 'final' 태그 명시
        p5_v1 = build_report_artifact_path(topic, "p5", base_dir=tmpdir)
        assert p5_v1.endswith("AI_동향_p5_final_v1.md")
        saved_final1 = save_file_append_only(p5_v1, "# 최종 보고서 1차")
        assert os.path.exists(saved_final1)

        # 최종본 재취합 시 v2 생성 (final_v2)
        p5_v2 = build_report_artifact_path(topic, "p5", base_dir=tmpdir)
        assert p5_v2.endswith("AI_동향_p5_final_v2.md")
        saved_final2 = save_file_append_only(p5_v2, "# 최종 보고서 2차")
        assert os.path.exists(saved_final2)


def test_legacy_compatibility():
    with tempfile.TemporaryDirectory() as tmpdir:
        topic = "로봇산업"

        # 레거시 v1 호출 -> p1_v1 매핑 확인
        p = build_report_artifact_path(topic, "v1", base_dir=tmpdir)
        assert p.endswith("로봇산업_p1_v1.md")

        # 레거시 v2 호출 -> p2_v1 매핑 확인
        p2 = build_report_artifact_path(topic, "v2", base_dir=tmpdir)
        assert p2.endswith("로봇산업_p2_v1.md")

        # 레거시 v3_final 호출 -> p5_final_v1 매핑 확인
        p_final = build_report_artifact_path(topic, "v3_final", base_dir=tmpdir)
        assert p_final.endswith("로봇산업_p5_final_v1.md")


def test_version_query_helpers():
    with tempfile.TemporaryDirectory() as tmpdir:
        topic = "모빌리티"

        # p5 최종본 순차 생성
        p1 = build_report_artifact_path(topic, "p5", base_dir=tmpdir)
        save_file_append_only(p1, "final content 1")
        p2 = build_report_artifact_path(topic, "p5", base_dir=tmpdir)
        save_file_append_only(p2, "final content 2")

        versions = get_existing_artifact_versions(topic, "p5", base_dir=tmpdir)
        assert len(versions) == 2
        assert versions[0].endswith("모빌리티_p5_final_v1.md")
        assert versions[1].endswith("모빌리티_p5_final_v2.md")

        latest = get_latest_artifact_path(topic, "p5", base_dir=tmpdir)
        assert latest is not None
        assert latest.endswith("모빌리티_p5_final_v2.md")
