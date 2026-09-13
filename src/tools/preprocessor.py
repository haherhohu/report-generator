"""Document loader and preprocessor for heavy reference materials (PDF, HTML, TXT, MD)."""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger("report_generator.tools.preprocessor")


def read_text_with_fallback(file_path: Path | str) -> str:
    """UTF-8 우선 시도 후 한글 인코딩(cp949, euc-kr)을 순차 시도."""
    p = Path(file_path)
    encodings = ("utf-8", "utf-8-sig", "cp949", "euc-kr")
    last_err = None

    for enc in encodings:
        try:
            return p.read_text(encoding=enc)
        except UnicodeDecodeError as exc:
            last_err = exc

    raise ValueError(f"파일 {p}을 디코딩할 수 없습니다. 마지막 오류: {last_err}")


def load_source_materials(source_dir: str | Path) -> list[dict[str, Any]]:
    """지정 디렉터리에서 기초 문서(.md, .txt, .pdf)를 읽어와 팩트 청크 목록으로 반환."""
    materials = []
    p = Path(source_dir)
    if not p.exists():
        return materials

    for f in p.iterdir():
        if f.is_file():
            suffix = f.suffix.lower()
            if suffix in (".md", ".txt"):
                try:
                    content = read_text_with_fallback(f)
                    materials.append({"filename": f.name, "content": content, "path": str(f)})
                except Exception as e:
                    logger.warning(f"텍스트 파일 로드 실패: {f.name} ({e})")

            elif suffix == ".pdf":
                try:
                    from pypdf import PdfReader
                    reader = PdfReader(str(f))
                    total_pages = len(reader.pages)

                    MAX_ALLOWED_PAGES = 50
                    if total_pages > MAX_ALLOWED_PAGES:
                        logger.warning(
                            f"[Skip] {f.name} (PDF): 총 {total_pages}페이지로 {MAX_ALLOWED_PAGES}p 초과. 지연 방지를 위해 제외."
                        )
                        continue

                    text_chunks = [page.extract_text() or "" for page in reader.pages]
                    pdf_text = "\n".join(text_chunks)

                    MAX_CHARS = 20000
                    if len(pdf_text) > MAX_CHARS:
                        pdf_text = pdf_text[:MAX_CHARS] + "\n\n... [시스템: 문서 분량 초과로 이하 생략됨] ..."

                    materials.append({"filename": f.name, "content": pdf_text, "path": str(f)})
                except Exception as e:
                    logger.warning(f"PDF 파싱 실패: {f.name} ({e})")

    return materials


def run_preprocessing(
    raw_dir: str = "workspace/raw_refs",
    summary_dir: str = "workspace/source/summary",
    max_chars_per_doc: int = 15000,
) -> None:
    """원시 레퍼런스 문서를 사전 분석하여 경량 마크다운 팩트 시트로 변환 및 아카이빙."""
    raw_path = Path(raw_dir)
    if not raw_path.exists():
        return

    summary_path = Path(summary_dir)
    summary_path.mkdir(parents=True, exist_ok=True)

    target_files = [f for f in raw_path.iterdir() if f.suffix.lower() in (".pdf", ".html", ".htm", ".txt")]
    if not target_files:
        return

    for tf in target_files:
        save_name = f"{tf.stem}_summary.md"
        save_path = summary_path / save_name

        if save_path.exists():
            continue

        try:
            if tf.suffix.lower() == ".pdf":
                from pypdf import PdfReader
                reader = PdfReader(str(tf))
                raw_text = "\n".join([page.extract_text() or "" for page in reader.pages[:20]])
            else:
                raw_text = read_text_with_fallback(tf)

            trimmed = raw_text[:max_chars_per_doc]
            summary_content = (
                f"# {tf.name} 핵심 팩트 요약본\n\n"
                f"- 원본 출처: {tf.name}\n"
                f"- 등록 일시: 자동 아카이빙됨\n\n"
                f"## 주요 발췌 팩트\n\n{trimmed}\n"
            )
            save_path.write_text(summary_content, encoding="utf-8")
        except Exception as exc:
            logger.warning(f"전처리 실패: {tf.name} ({exc})")

