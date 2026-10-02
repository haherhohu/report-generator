"""HWPX exporter: converts cleaned markdown documents to Korean government standard HWPX format."""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from src.utils.markdown_cleaner import clean_and_format_markdown

logger = logging.getLogger("report_generator.hwpx_exporter")


def export_markdown_to_hwpx(
    markdown_path: str | Path,
    output_hwpx_path: str | Path | None = None,
) -> str | None:
    """
    정제된 마크다운 파일을 공공 표준 HWPX 문서로 변환.
    md2hwpx CLI 또는 Python 라이브러리가 있을 경우 변환을 실행하며,
    부재 시 전처리 완료된 HWPX 지향 표준 규격을 확정합니다.
    """
    src = Path(markdown_path)
    if not src.exists():
        logger.warning(f"[HWPX Exporter] 원본 마크다운 파일을 찾을 수 없습니다: {markdown_path}")
        return None

    if not output_hwpx_path:
        out_hwpx = src.with_suffix(".hwpx")
    else:
        out_hwpx = Path(output_hwpx_path)

    out_hwpx.parent.mkdir(parents=True, exist_ok=True)

    # 1. 자체 Python HWPX 변환기 (krauv_template.hwpx 양식 기반) 우선 실행
    try:
        from src.tools.hwpx_converter import convert_markdown_to_hwpx
        template_file = "krauv_template.hwpx"
        if os.path.exists(template_file):
            logger.info(f"[HWPX Exporter] 자체 파이썬 변환기 실행 (템플릿: {template_file}): {src} -> {out_hwpx}")
            res = convert_markdown_to_hwpx(src, out_hwpx, template_path=template_file)
            if os.path.exists(res):
                logger.info(f"[HWPX Exporter] ✅ HWPX 문서 변환 성공: {out_hwpx}")
                return res
    except Exception as e:
        logger.warning(f"[HWPX Exporter] 자체 파이썬 변환기 실패 ({e}), CLI fallback 시도")

    # 2. md2hwpx CLI 존재 확인 및 fallback 실행
    md2hwpx_cmd = shutil.which("md2hwpx")
    if md2hwpx_cmd:
        try:
            logger.info(f"[HWPX Exporter] md2hwpx CLI 호출: {src} -> {out_hwpx}")
            subprocess.run(
                [md2hwpx_cmd, str(src), "-o", str(out_hwpx)],
                check=True,
                capture_output=True,
                text=True,
                timeout=60,
            )
            if out_hwpx.exists():
                logger.info(f"[HWPX Exporter] ✅ md2hwpx HWPX 변환 성공: {out_hwpx}")
                return str(out_hwpx)
        except Exception as e:
            logger.warning(f"[HWPX Exporter] md2hwpx 변환 실패: {e}")

    return str(out_hwpx) if out_hwpx.exists() else None
