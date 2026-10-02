"""HWPX Converter: Pure Python markdown-to-HWPX converter based on Hancom HWPX specification
and institutional templates (e.g. krauv_template.hwpx).

Features:
- Pure Python implementation without external CLI/VSCode extension dependencies.
- Reads institutional HWPX templates, preserving covers, logos, headers, and styles.
- Maps markdown structural elements (headings, bullets, tables, captions) to template styles.
- Clones base charPr to provide exact matching font and size for bold spans mid-sentence.
- Implements Shift-Tab (내어쓰기) hanging indents for list items.
- Converts blockquote figure specifications into 1x1 boxed tables.
- Disables automatic caption numbering (numberingType="NONE") to prevent double numbering.
- Fixes table indentation and page overflow (paraPrIDRef="0", safe width 49000).
- Enables cell page break (pageBreak="CELL", treatAsChar="0") for long multi-page tables.
- Inserts blank line spacing between headings, paragraphs, figures, and tables.
- Converts inline HTML <table> and <strong> tags to HWPX tables.
- Headings at level 5+ (#####) rendered as bold body paragraphs.
- Converts <br> tags in table cells into genuine multi-line paragraphs with bold support.
- Sets uniform center alignment for all table cells to ensure visual stability.
- Indents regular body paragraphs with a single leading space (" ") while preserving standard 바탕글 paragraph style.
- Cleans abrupt Hanja/foreign word transitions into official Korean terms or parenthesized text.
- Replaces escaped asterisk notes (\\*) with standard Korean reference marks (※).
- Applies left alignment (paraPr 1050) to bibliography/references to prevent stretched spacing.
- Generates fully compliant Hancom HWPX packages (mimetype, OCF container, XML schemas).
"""
from __future__ import annotations

import argparse
import copy
from datetime import datetime
import io
import logging
import os
from pathlib import Path
import re
from typing import Any
import xml.etree.ElementTree as ET
import yaml
import zipfile

try:
    from src.utils.markdown_cleaner import (
        clean_unparenthesized_foreign_words_and_hanja,
        clean_asterisk_notes,
    )
except ImportError:
    def clean_unparenthesized_foreign_words_and_hanja(text: str) -> str:
        return text

    def clean_asterisk_notes(text: str) -> str:
        return text

logger = logging.getLogger("report_generator.hwpx_converter")

# Hancom HWPX Namespaces
HWPX_NAMESPACES = {
    "ha": "http://www.hancom.co.kr/hwpml/2011/app",
    "hp": "http://www.hancom.co.kr/hwpml/2011/paragraph",
    "hp10": "http://www.hancom.co.kr/hwpml/2016/paragraph",
    "hs": "http://www.hancom.co.kr/hwpml/2011/section",
    "hc": "http://www.hancom.co.kr/hwpml/2011/core",
    "hh": "http://www.hancom.co.kr/hwpml/2011/head",
    "hhs": "http://www.hancom.co.kr/hwpml/2011/history",
    "hm": "http://www.hancom.co.kr/hwpml/2011/master-page",
    "hpf": "http://www.hancom.co.kr/schema/2011/hpf",
    "dc": "http://purl.org/dc/elements/1.1/",
    "opf": "http://www.idpf.org/2007/opf/",
    "ooxmlchart": "http://www.hancom.co.kr/hwpml/2016/ooxmlchart",
    "hwpunitchar": "http://www.hancom.co.kr/hwpml/2016/HwpUnitChar",
    "epub": "http://www.idpf.org/2007/ops",
    "config": "urn:oasis:names:tc:opendocument:xmlns:config:1.0",
}

for prefix, uri in HWPX_NAMESPACES.items():
    ET.register_namespace(prefix, uri)

HP_NS = HWPX_NAMESPACES["hp"]
HS_NS = HWPX_NAMESPACES["hs"]
HC_NS = HWPX_NAMESPACES["hc"]
HH_NS = HWPX_NAMESPACES["hh"]


class MarkdownHWPXConverter:
    """Markdown 문서를 HWPX 템플릿(krauv_template.hwpx)의 스타일에 맞춰 HWPX로 변환하는 변환기."""

    def __init__(
        self,
        template_path: str | Path = "krauv_template.hwpx",
        mapping_path: str | Path = "config/hwpx_style_mapping.yaml",
    ):
        self.template_path = Path(template_path)
        self.mapping_path = Path(mapping_path)
        self.mapping = self._load_mapping()
        self._next_id = 1159820000

    def _get_id(self) -> str:
        self._next_id += 1
        return str(self._next_id)

    def _load_mapping(self) -> dict[str, Any]:
        if self.mapping_path.exists():
            try:
                with open(self.mapping_path, "r", encoding="utf-8") as f:
                    return yaml.safe_load(f) or {}
            except Exception as e:
                logger.warning(f"매핑 설정 파일 로드 실패 ({e}), 기본값 사용")
        return self._default_mapping()

    def _default_mapping(self) -> dict[str, Any]:
        return {
            "headings": {
                "h1": {"style_id": "17", "para_pr_id": "6", "char_pr_id": "9"},
                "h2": {"style_id": "2", "para_pr_id": "9", "char_pr_id": "30"},
                "h3": {"style_id": "3", "para_pr_id": "14", "char_pr_id": "28"},
                "h4": {"style_id": "4", "para_pr_id": "23", "char_pr_id": "23"},
                "h5": {"style_id": "7", "para_pr_id": "33", "char_pr_id": "36"},
            },
            "content": {
                "body_paragraph": {"style_id": "0", "para_pr_id": "0", "char_pr_id": "0"},
                "reference_item": {"style_id": "0", "para_pr_id": "1050", "char_pr_id": "0"},
                "bullet_level1": {"style_id": "8", "para_pr_id": "30", "char_pr_id": "37", "prefix": "○ "},
                "bullet_level2": {"style_id": "8", "para_pr_id": "1030", "char_pr_id": "37", "prefix": "- "},
                "caption_table": {"style_id": "12", "para_pr_id": "28", "char_pr_id": "38"},
                "caption_figure": {"style_id": "6", "para_pr_id": "35", "char_pr_id": "40"},
                "footnote": {"style_id": "40", "para_pr_id": "40", "char_pr_id": "43"},
                "quote_block": {"style_id": "25", "para_pr_id": "3", "char_pr_id": "19"},
            },
            "table": {
                "total_width": 49000,
                "border_fill_table": "5",
                "border_fill_header": "10",
                "border_fill_cell": "8",
                "header": {"style_id": "10", "para_pr_id": "19", "char_pr_id": "31"},
                "cell_center": {"style_id": "11", "para_pr_id": "19", "char_pr_id": "24"},
                "cell_left": {"style_id": "11", "para_pr_id": "19", "char_pr_id": "24"},
            },
        }

    def convert_text(self, markdown_text: str, output_path: str | Path) -> str:
        """마크다운 텍스트를 파싱하여 HWPX 파일로 생성."""
        if not self.template_path.exists():
            raise FileNotFoundError(f"템플릿 파일을 찾을 수 없습니다: {self.template_path}")

        out_path = Path(output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        # 0. 한문 및 괄호 없는 외래어, \* 기호 자동 정제
        markdown_text = clean_unparenthesized_foreign_words_and_hanja(markdown_text)
        markdown_text = clean_asterisk_notes(markdown_text)

        # 템플릿 파일 읽기
        with zipfile.ZipFile(self.template_path, "r") as zin:
            template_files = {name: zin.read(name) for name in zin.namelist()}

        # 1. Contents/header.xml 보강: 볼드 charPr, 리스트 paraPr, 들여쓰기 1040, 참고문헌 1050 추가
        if "Contents/header.xml" in template_files:
            template_files["Contents/header.xml"] = self._enhance_header_xml(template_files["Contents/header.xml"])

        sec_xml_bytes = template_files.get("Contents/section0.xml")
        if not sec_xml_bytes:
            raise ValueError("템플릿에 Contents/section0.xml이 존재하지 않습니다.")

        root = ET.fromstring(sec_xml_bytes)

        # 2. 마크다운에서 문서 제목 및 메타정보 추출
        doc_title, doc_subtitle, lines = self._extract_front_meta(markdown_text)

        # 3. 표지 업데이트 (문서 제목, 날짜 등 반영)
        self._update_cover_page(root, doc_title, doc_subtitle)

        # 4. 템플릿의 기존 본문 샘플 제거 (인덱스 41번 이후 본문 제거, 표지 및 목차 구분자 40번까지 보존)
        all_paras = list(root.findall(f"{{{HP_NS}}}p"))
        cutoff_index = 41
        for p in all_paras[cutoff_index:]:
            root.remove(p)

        # 5. 마크다운 본문 파싱 및 HWPX 요소 변환 생성
        body_elements = self._parse_markdown_to_hwpx_elements(lines)
        for elem in body_elements:
            root.append(elem)

        # 6. 새 section0.xml 직렬화
        new_sec_bytes = ET.tostring(root, encoding="utf-8", xml_declaration=True)
        template_files["Contents/section0.xml"] = new_sec_bytes

        # 7. HWPX zip 패키지 생성 (mimetype은 압축 없이 첫 번째 파일로 수록)
        self._write_hwpx_package(out_path, template_files)
        logger.info(f"✅ HWPX 문서 변환 완료: {out_path}")
        return str(out_path)

    def convert_file(self, markdown_path: str | Path, output_path: str | Path | None = None) -> str:
        """마크다운 파일을 HWPX 파일로 변환."""
        src = Path(markdown_path)
        if not src.exists():
            raise FileNotFoundError(f"원본 마크다운 파일을 찾을 수 없습니다: {markdown_path}")

        raw_md = src.read_text(encoding="utf-8")
        if not output_path:
            output_path = src.with_suffix(".hwpx")

        return self.convert_text(raw_md, output_path)

    def _enhance_header_xml(self, header_bytes: bytes) -> bytes:
        """
        header.xml을 파싱하여:
        1) 각 base charPr의 볼드 버전(id: 1000 + base_id)을 동적 생성하여 문단 폰트/크기 일치 볼드 구현.
        2) 2단계 리스트 개조식 내어쓰기(Shift-Tab)용 paraPr id="1030" 추가.
        3) 참고문헌 전용 좌측정렬 및 자간 늘어남 방지용 paraPr id="1050" 추가.
        4) 캡션 paraPr(28, 35)의 자동 넘버링(type="NUMBER")을 해제하여 2중 넘버링 방지.
        """
        root = ET.fromstring(header_bytes)

        # 1. charProperties 내 볼드 버전 클론 생성 (1000 + id)
        char_props = root.find(f".//{{{HH_NS}}}charProperties")
        if char_props is not None:
            added_chars = 0
            for cp in list(char_props):
                cid_str = cp.attrib.get("id")
                if cid_str is not None and cid_str.isdigit():
                    cid = int(cid_str)
                    if cid < 1000:
                        new_cp = copy.deepcopy(cp)
                        new_cp.attrib["id"] = str(1000 + cid)
                        if new_cp.find(f"{{{HH_NS}}}bold") is None:
                            u_elem = new_cp.find(f"{{{HH_NS}}}underline")
                            if u_elem is not None:
                                idx = list(new_cp).index(u_elem)
                                new_cp.insert(idx, ET.Element(f"{{{HH_NS}}}bold"))
                            else:
                                new_cp.append(ET.Element(f"{{{HH_NS}}}bold"))
                        char_props.append(new_cp)
                        added_chars += 1
            if "itemCnt" in char_props.attrib:
                char_props.attrib["itemCnt"] = str(int(char_props.attrib["itemCnt"]) + added_chars)

        # 2. paraProperties 내 특수 서식 paraPr 추가
        para_props = root.find(f".//{{{HH_NS}}}paraProperties")
        if para_props is not None:
            p30 = root.find(f".//{{{HH_NS}}}paraPr[@id='30']")
            if p30 is not None:
                # 2단계 개조식 Shift-Tab 내어쓰기 paraPr 1030
                p1030 = copy.deepcopy(p30)
                p1030.attrib["id"] = "1030"
                for left in p1030.findall(f".//{{{HC_NS}}}left"):
                    left.attrib["value"] = "3800"
                for intent in p1030.findall(f".//{{{HC_NS}}}intent"):
                    intent.attrib["value"] = "-1469"
                para_props.append(p1030)

            p0 = root.find(f".//{{{HH_NS}}}paraPr[@id='0']")
            if p0 is not None:
                # 참고문헌 좌측정렬 및 단어/영문 강제 줄바꿈 paraPr 1050
                p1050 = copy.deepcopy(p0)
                p1050.attrib["id"] = "1050"
                align_elem = p1050.find(f"{{{HH_NS}}}align")
                if align_elem is not None:
                    align_elem.attrib["horizontal"] = "LEFT"
                break_elem = p1050.find(f"{{{HH_NS}}}breakSetting")
                if break_elem is not None:
                    break_elem.attrib["breakLatinWord"] = "BREAK_WORD"
                    break_elem.attrib["breakNonLatinWord"] = "BREAK_WORD"
                para_props.append(p1050)

            if "itemCnt" in para_props.attrib:
                para_props.attrib["itemCnt"] = str(int(para_props.attrib["itemCnt"]) + 2)

            # 캡션 paraPr(28, 35)의 자동 넘버링 해제
            for pid in ["28", "35"]:
                p_elem = root.find(f".//{{{HH_NS}}}paraPr[@id='{pid}']")
                if p_elem is not None:
                    h_elem = p_elem.find(f"{{{HH_NS}}}heading")
                    if h_elem is not None:
                        h_elem.attrib["type"] = "NONE"
                        h_elem.attrib["idRef"] = "0"
                        h_elem.attrib["level"] = "0"

        return ET.tostring(root, encoding="utf-8", xml_declaration=True)

    def _build_empty_line(self) -> ET.Element:
        """한 줄 띄기를 위한 빈 문단 엘리먼트 생성."""
        p = ET.Element(
            f"{{{HP_NS}}}p",
            {
                "id": self._get_id(),
                "paraPrIDRef": "0",
                "styleIDRef": "0",
                "pageBreak": "0",
                "columnBreak": "0",
                "merged": "0",
            },
        )
        run = ET.SubElement(p, f"{{{HP_NS}}}run", {"charPrIDRef": "0"})
        ET.SubElement(run, f"{{{HP_NS}}}t")
        return p

    def _extract_front_meta(self, text: str) -> tuple[str, str, list[str]]:
        """마크다운에서 제목(# ...) 및 부제/요약문을 추출하고 본문 라인 분리."""
        lines = text.splitlines()
        doc_title = "보고서"
        doc_subtitle = ""

        filtered_lines = []
        in_code_block = False

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("```"):
                in_code_block = not in_code_block
                filtered_lines.append(line)
                continue
            if not in_code_block and stripped.startswith("# ") and doc_title == "보고서":
                doc_title = stripped.lstrip("# ").strip()
                continue
            filtered_lines.append(line)

        return doc_title, doc_subtitle, filtered_lines

    def _update_cover_page(self, root: ET.Element, title: str, subtitle: str = "") -> None:
        """템플릿의 표지 문구(제목, 부제, 일자 등)를 갱신하고 기존 템플릿 기본 타이틀 텍스트를 완전 제거."""
        paras = root.findall(f"{{{HP_NS}}}p")
        if len(paras) <= 22:
            return

        # 1. 템플릿의 기존 타이틀 문구(인덱스 8: UAV 교육주제 발굴을 위한 / 인덱스 9: AI, 빅데이터 등 최신 기술동향 분석) 완전 삭제
        p8_t = paras[8].find(f".//{{{HP_NS}}}t") if len(paras) > 8 else None
        p9_t = paras[9].find(f".//{{{HP_NS}}}t") if len(paras) > 9 else None

        if p8_t is not None:
            p8_t.text = ""
        if p9_t is not None:
            p9_t.text = ""

        # 2. 문서 제목 및 부제 반영 (템플릿 문구 잔여 원천 차단)
        if subtitle and p8_t is not None:
            p8_t.text = subtitle
            if title and p9_t is not None:
                p9_t.text = title
        elif "\n" in title:
            t_lines = title.split("\n", 1)
            if p8_t is not None:
                p8_t.text = t_lines[0].strip()
            if p9_t is not None:
                p9_t.text = t_lines[1].strip()
        else:
            if title and p9_t is not None:
                p9_t.text = title

        # 3. 일자 업데이트
        if len(paras) > 13:
            t_elem = paras[13].find(f".//{{{HP_NS}}}t")
            if t_elem is not None:
                t_elem.text = datetime.now().strftime("%Y. %m. %d.")

    def _parse_html_table(self, html_text: str) -> list[list[str]]:
        """HTML <table>...</table> 태그에서 행과 열 데이터를 파싱."""
        tr_matches = re.findall(r"<tr[^>]*>(.*?)</tr>", html_text, re.DOTALL | re.IGNORECASE)
        rows: list[list[str]] = []
        for tr in tr_matches:
            cells = re.findall(r"<(?:th|td)[^>]*>(.*?)</(?:th|td)>", tr, re.DOTALL | re.IGNORECASE)
            clean_cells = []
            for c in cells:
                # Keep <br> intact for line splitting in cell builder, strip other tags
                txt = re.sub(r"<(?!/?br\b)[^>]+>", "", c)
                txt = txt.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").strip()
                txt = re.sub(r"[ \t]+", " ", txt)
                clean_cells.append(txt)
            if clean_cells:
                rows.append(clean_cells)
        return rows

    def _parse_markdown_to_hwpx_elements(self, lines: list[str]) -> list[ET.Element]:
        """마크다운 라인들을 순회하며 문단 및 표 HWPX 엘리먼트 목록 생성 (블록 간 1줄 띄기 적용)."""
        elements: list[ET.Element] = []
        last_cat = "START"
        in_ref_section = False

        def append_elem(elem: ET.Element, cat: str) -> None:
            nonlocal last_cat
            need_space_before = False
            if cat == "HEADING_PAGEBREAK":
                need_space_before = False
            elif cat in ("HEADING", "CAPTION"):
                if last_cat not in ("START", "EMPTY", "HEADING_PAGEBREAK"):
                    need_space_before = True
            elif cat == "BODY":
                if last_cat not in ("START", "EMPTY", "HEADING_PAGEBREAK"):
                    need_space_before = True
            elif cat == "LIST":
                if last_cat not in ("START", "EMPTY", "HEADING_PAGEBREAK", "LIST"):
                    need_space_before = True
            elif cat in ("TABLE", "FIGURE_BOX"):
                if last_cat not in ("START", "EMPTY", "HEADING_PAGEBREAK", "CAPTION"):
                    need_space_before = True

            if need_space_before and elements:
                elements.append(self._build_empty_line())

            elements.append(elem)
            last_cat = cat

        i = 0
        n = len(lines)

        while i < n:
            raw_line = lines[i]
            line = raw_line.strip()

            if not line:
                i += 1
                continue

            # 1. 구분선(---) 스킵
            if re.match(r"^---+$", line):
                i += 1
                continue

            # 2. HTML 표 블록 감지 (```html <table> 또는 직접 <table> 태그)
            if line.startswith("```html") or line.startswith("```") or "<table" in line.lower():
                is_html_block = "<table" in line.lower()
                chunk_lines = [raw_line]
                idx = i + 1
                while idx < n:
                    chk = lines[idx]
                    chunk_lines.append(chk)
                    if "<table" in chk.lower():
                        is_html_block = True
                    if "</table>" in chk.lower() and (not line.startswith("```") or chk.strip() == "```"):
                        idx += 1
                        break
                    if line.startswith("```") and chk.strip() == "```" and is_html_block:
                        idx += 1
                        break
                    idx += 1

                if is_html_block:
                    full_chunk = "\n".join(chunk_lines)
                    table_html_m = re.search(r"<table.*?</table>", full_chunk, re.DOTALL | re.IGNORECASE)
                    if table_html_m:
                        parsed_rows = self._parse_html_table(table_html_m.group(0))
                        tbl_elem = self._build_table_from_rows(parsed_rows)
                        if tbl_elem is not None:
                            append_elem(tbl_elem, "TABLE")
                        i = idx
                        continue

            # 3. 마크다운 파이프 표 감지 (| ... |)
            if line.startswith("|") and line.endswith("|"):
                table_lines = []
                while i < n and lines[i].strip().startswith("|") and lines[i].strip().endswith("|"):
                    table_lines.append(lines[i].strip())
                    i += 1
                tbl_elem = self._build_table_element(table_lines)
                if tbl_elem is not None:
                    append_elem(tbl_elem, "TABLE")
                continue

            # 4. 캡션 감지 (표 캡션 or 그림 캡션)
            if re.match(r"^\*{0,2}(?:\[표\s*[^\]]+\]|【표\s*[^】]+】)\*{0,2}", line):
                cap_cfg = self.mapping["content"]["caption_table"]
                clean_text = line.replace("**", "").replace("__", "").strip()
                append_elem(self._build_paragraph(clean_text, cap_cfg), "CAPTION")
                i += 1
                continue

            if re.match(r"^\*{0,2}(?:\[그림\s*[^\]]+\]|【그림\s*[^】]+】)\*{0,2}", line):
                cap_cfg = self.mapping["content"]["caption_figure"]
                clean_text = line.replace("**", "").replace("__", "").strip()
                append_elem(self._build_paragraph(clean_text, cap_cfg), "CAPTION")
                i += 1
                continue

            # 5. 헤딩 감지 (##, ###, ####, #####+)
            if line.startswith("## "):
                h_text = line.lstrip("# ").strip()
                h2_cfg = self.mapping["headings"]["h2"]
                is_roman = bool(re.match(r"^[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]\.", h_text))
                in_ref_section = "참고문헌" in h_text
                append_elem(
                    self._build_paragraph(h_text, h2_cfg, page_break=is_roman),
                    "HEADING_PAGEBREAK" if is_roman else "HEADING",
                )
                i += 1
                continue

            if line.startswith("### "):
                h_text = line.lstrip("# ").strip()
                in_ref_section = "참고문헌" in h_text
                if re.match(r"^\d+\.", h_text):
                    h3_cfg = self.mapping["headings"]["h3"]
                    append_elem(self._build_paragraph(h_text, h3_cfg), "HEADING")
                elif re.match(r"^\d+\)|^[가-힣]\)", h_text):
                    h4_cfg = self.mapping["headings"]["h4"]
                    append_elem(self._build_paragraph(h_text, h4_cfg), "HEADING")
                else:
                    h3_cfg = self.mapping["headings"]["h3"]
                    append_elem(self._build_paragraph(h_text, h3_cfg), "HEADING")
                i += 1
                continue

            if line.startswith("#### "):
                h_text = line.lstrip("# ").strip()
                in_ref_section = "참고문헌" in h_text
                h5_cfg = self.mapping["headings"]["h5"]
                append_elem(self._build_paragraph(h_text, h5_cfg), "HEADING")
                i += 1
                continue

            # 6. ##### 이하의 제목: 헤더 표시 제거 후 볼드 본문 문단으로 변환
            if re.match(r"^#{5,}\s+", line):
                h_text = re.sub(r"^#{5,}\s+", "", line).strip()
                bold_text = f"**{h_text}**" if not (h_text.startswith("**") and h_text.endswith("**")) else h_text
                p_cfg = self.mapping["content"]["body_paragraph"]
                append_elem(self._build_paragraph(bold_text, p_cfg, parse_bold=True), "BODY")
                i += 1
                continue

            # 7. 인용문 (> ...): 그림 파트 또는 인용 단락을 1x1 테두리 표로 변환
            if line.startswith(">"):
                quote_lines = []
                while i < n and lines[i].strip().startswith(">"):
                    quote_lines.append(lines[i].strip())
                    i += 1
                fig_elem = self._build_figure_box_element(quote_lines)
                append_elem(fig_elem, "FIGURE_BOX")
                continue

            # 8. 각주 / 참고 출처 (※ ... 또는 \* ... 또는 * 자료:)
            if line.startswith("※") or line.startswith(r"\*") or re.match(r"^\*\s*(?:주|자료|출처|참고|비고|Note)\b", line, re.I):
                fn_cfg = self.mapping["content"]["footnote"]
                clean_fn = re.sub(r"^\\?\*\s*(?:(주|자료|출처|참고|비고|Note)\b:?)?", r"※ \1: ", line).strip()
                clean_fn = re.sub(r"^※\s*:\s*", "※ ", clean_fn)
                append_elem(self._build_paragraph(clean_fn, fn_cfg, parse_bold=True), "BODY")
                i += 1
                continue

            # 9. 참고문헌 섹션 내부 목록 단락 (좌측정렬 paraPr 1050 적용)
            if in_ref_section:
                ref_cfg = self.mapping["content"].get("reference_item", {"style_id": "0", "para_pr_id": "1050", "char_pr_id": "0"})
                append_elem(self._build_paragraph(line, ref_cfg, parse_bold=True), "BODY")
                i += 1
                continue

            # 10. 개조식 목록 (○ ..., - ..., 1. ...)
            if line.startswith("○ ") or line.startswith("● "):
                b1_cfg = self.mapping["content"]["bullet_level1"]
                append_elem(self._build_paragraph(line, b1_cfg, parse_bold=True), "LIST")
                i += 1
                continue

            if re.match(r"^\s*[-*]\s+", raw_line):
                # 2단계 개조식: bullet prefix만 정규식으로 안전하게 제거하여 **bold** 보존
                clean_text = re.sub(r"^\s*[-*]\s+", "", raw_line).strip()
                b2_cfg = {"style_id": "8", "para_pr_id": "1030", "char_pr_id": "37"}
                append_elem(self._build_paragraph(f"- {clean_text}", b2_cfg, parse_bold=True), "LIST")
                i += 1
                continue

            if re.match(r"^\d+\)\s+", line) or re.match(r"^[가-힣]\)\s+", line):
                h5_cfg = self.mapping["headings"]["h5"]
                append_elem(self._build_paragraph(line, h5_cfg), "HEADING")
                i += 1
                continue

            # 11. 일반 본문 단락 (문단 시작 맨 앞에 빈칸 하나 " " 추가, 기본 바탕글 paraPr 0 적용)
            p_cfg = self.mapping["content"]["body_paragraph"]
            if line in ("[시사점]", "**[시사점]**", "**시사점**") or re.match(r"^\*{0,2}\[시사점\]\*{0,2}$", line):
                body_text = line
            else:
                body_text = f" {line.lstrip()}"
            append_elem(self._build_paragraph(body_text, p_cfg, parse_bold=True), "BODY")
            i += 1

        return elements

    def _build_paragraph(
        self,
        text: str,
        style_cfg: dict[str, str],
        page_break: bool = False,
        parse_bold: bool = False,
    ) -> ET.Element:
        """스타일 설정에 맞는 단일 <hp:p> 엘리먼트 생성 (폰트/크기 동일 유지 볼드 클론 적용)."""
        p = ET.Element(
            f"{{{HP_NS}}}p",
            {
                "id": self._get_id(),
                "paraPrIDRef": str(style_cfg.get("para_pr_id", "0")),
                "styleIDRef": str(style_cfg.get("style_id", "0")),
                "pageBreak": "1" if page_break else "0",
                "columnBreak": "0",
                "merged": "0",
            },
        )

        base_char_pr_id = str(style_cfg.get("char_pr_id", "0"))
        bold_char_pr_id = str(1000 + int(base_char_pr_id)) if base_char_pr_id.isdigit() else base_char_pr_id

        if not parse_bold or "**" not in text:
            run = ET.SubElement(p, f"{{{HP_NS}}}run", {"charPrIDRef": base_char_pr_id})
            t = ET.SubElement(run, f"{{{HP_NS}}}t")
            t.text = text
            return p

        # 인라인 볼드(**...**) 파싱: non-greedy 정규식으로 복수 볼드 구간 안전 분리
        parts = re.split(r"(\*\*[^*]+?\*\*)", text)
        for part in parts:
            if not part:
                continue
            if part.startswith("**") and part.endswith("**") and len(part) >= 4:
                inner = part[2:-2]
                r = ET.SubElement(p, f"{{{HP_NS}}}run", {"charPrIDRef": bold_char_pr_id})
                t = ET.SubElement(r, f"{{{HP_NS}}}t")
                t.text = inner
            else:
                r = ET.SubElement(p, f"{{{HP_NS}}}run", {"charPrIDRef": base_char_pr_id})
                t = ET.SubElement(r, f"{{{HP_NS}}}t")
                t.text = part

        return p

    def _build_figure_box_element(self, quote_lines: list[str]) -> ET.Element:
        """인용문(> ...) 형태의 그림/구조도/명세를 1x1 테두리 상자 표로 변환."""
        p = ET.Element(
            f"{{{HP_NS}}}p",
            {
                "id": self._get_id(),
                "paraPrIDRef": "0",
                "styleIDRef": "0",
                "pageBreak": "0",
                "columnBreak": "0",
                "merged": "0",
            },
        )
        run = ET.SubElement(p, f"{{{HP_NS}}}run", {"charPrIDRef": "0"})
        tbl = ET.SubElement(
            run,
            f"{{{HP_NS}}}tbl",
            {
                "id": self._get_id(),
                "zOrder": "0",
                "numberingType": "NONE",
                "textWrap": "TOP_AND_BOTTOM",
                "textFlow": "BOTH_SIDES",
                "lock": "0",
                "dropcapstyle": "None",
                "pageBreak": "CELL",
                "repeatHeader": "0",
                "rowCnt": "1",
                "colCnt": "1",
                "cellSpacing": "0",
                "borderFillIDRef": "8",
                "noAdjust": "1",
            },
        )
        ET.SubElement(
            tbl,
            f"{{{HP_NS}}}sz",
            {
                "width": "49000",
                "widthRelTo": "ABSOLUTE",
                "height": "6000",
                "heightRelTo": "ABSOLUTE",
                "protect": "0",
            },
        )
        ET.SubElement(
            tbl,
            f"{{{HP_NS}}}pos",
            {
                "treatAsChar": "0",
                "affectLSpacing": "0",
                "flowWithText": "1",
                "allowOverlap": "0",
                "holdAnchorAndSO": "0",
                "vertRelTo": "PARA",
                "horzRelTo": "COLUMN",
                "vertAlign": "TOP",
                "horzAlign": "LEFT",
                "vertOffset": "0",
                "horzOffset": "0",
            },
        )
        ET.SubElement(tbl, f"{{{HP_NS}}}outMargin", {"left": "141", "right": "141", "top": "141", "bottom": "141"})
        ET.SubElement(tbl, f"{{{HP_NS}}}inMargin", {"left": "283", "right": "283", "top": "283", "bottom": "283"})

        tr = ET.SubElement(tbl, f"{{{HP_NS}}}tr")
        tc = ET.SubElement(
            tr,
            f"{{{HP_NS}}}tc",
            {
                "name": "",
                "header": "0",
                "hasMargin": "1",
                "protect": "0",
                "editable": "0",
                "dirty": "0",
                "borderFillIDRef": "8",
            },
        )
        sub = ET.SubElement(
            tc,
            f"{{{HP_NS}}}subList",
            {
                "id": "",
                "textDirection": "HORIZONTAL",
                "lineWrap": "BREAK",
                "vertAlign": "CENTER",
                "linkListIDRef": "0",
                "linkListNextIDRef": "0",
                "textWidth": "0",
                "textHeight": "0",
                "hasTextRef": "0",
                "hasNumRef": "0",
            },
        )

        clean_lines = []
        for ql in quote_lines:
            line_txt = re.sub(r"^>\s*", "", ql).strip()
            if line_txt:
                clean_lines.append(line_txt)

        if not clean_lines:
            clean_lines = [""]

        for cl in clean_lines:
            cell_p = self._build_paragraph(
                cl,
                {"para_pr_id": "0", "style_id": "0", "char_pr_id": "19"},
                parse_bold=True,
            )
            sub.append(cell_p)

        ET.SubElement(tc, f"{{{HP_NS}}}cellAddr", {"colAddr": "0", "rowAddr": "0"})
        ET.SubElement(tc, f"{{{HP_NS}}}cellSpan", {"colSpan": "1", "rowSpan": "1"})
        ET.SubElement(tc, f"{{{HP_NS}}}cellSz", {"width": "49000", "height": "6000"})
        ET.SubElement(tc, f"{{{HP_NS}}}cellMargin", {"left": "283", "right": "283", "top": "283", "bottom": "283"})

        return p

    def _build_table_from_rows(self, parsed_rows: list[list[str]]) -> ET.Element | None:
        """행/열 리스트 데이터를 HWPX <hp:tbl> 구조로 생성 (전체 중앙정렬, <br> 줄바꿈, 들여쓰기 0)."""
        if not parsed_rows:
            return None

        headers = parsed_rows[0]
        num_cols = len(headers)
        num_rows = len(parsed_rows)
        if num_cols == 0 or num_rows == 0:
            return None

        tbl_cfg = self.mapping["table"]
        total_width = int(tbl_cfg.get("total_width", 49000))

        # 열 너비 자동 계산 (텍스트 길이에 기반한 비례 분할, 최소 너비 4000 보장)
        col_max_lengths = [max(len(row[c]) if c < len(row) else 1 for row in parsed_rows) for c in range(num_cols)]
        total_weight = sum(col_max_lengths) or 1
        col_widths: list[int] = []
        allocated = 0
        for c in range(num_cols - 1):
            w = max(4000, int(total_width * (col_max_lengths[c] / total_weight)))
            col_widths.append(w)
            allocated += w
        col_widths.append(max(4000, total_width - allocated))

        p = ET.Element(
            f"{{{HP_NS}}}p",
            {
                "id": self._get_id(),
                "paraPrIDRef": "0",  # 표 부모 문단 들여쓰기 없음
                "styleIDRef": "0",
                "pageBreak": "0",
                "columnBreak": "0",
                "merged": "0",
            },
        )
        run = ET.SubElement(p, f"{{{HP_NS}}}run", {"charPrIDRef": "41"})

        tbl = ET.SubElement(
            run,
            f"{{{HP_NS}}}tbl",
            {
                "id": self._get_id(),
                "zOrder": "0",
                "numberingType": "NONE",  # 자동 캡션 2중 번호 방지
                "textWrap": "TOP_AND_BOTTOM",
                "textFlow": "BOTH_SIDES",
                "lock": "0",
                "dropcapstyle": "None",
                "pageBreak": "CELL",  # 페이지 넘김 시 셀 단위 분할 허용
                "repeatHeader": "1",
                "rowCnt": str(num_rows),
                "colCnt": str(num_cols),
                "cellSpacing": "0",
                "borderFillIDRef": str(tbl_cfg.get("border_fill_table", "5")),
                "noAdjust": "1",
            },
        )

        ET.SubElement(
            tbl,
            f"{{{HP_NS}}}sz",
            {
                "width": str(total_width),
                "widthRelTo": "ABSOLUTE",
                "height": "12000",
                "heightRelTo": "ABSOLUTE",
                "protect": "0",
            },
        )
        ET.SubElement(
            tbl,
            f"{{{HP_NS}}}pos",
            {
                "treatAsChar": "0",  # 긴 표 페이지 분할 허용
                "affectLSpacing": "0",
                "flowWithText": "1",
                "allowOverlap": "0",
                "holdAnchorAndSO": "0",
                "vertRelTo": "PARA",
                "horzRelTo": "COLUMN",
                "vertAlign": "TOP",
                "horzAlign": "LEFT",
                "vertOffset": "0",
                "horzOffset": "0",
            },
        )
        ET.SubElement(tbl, f"{{{HP_NS}}}outMargin", {"left": "141", "right": "141", "top": "141", "bottom": "141"})
        ET.SubElement(tbl, f"{{{HP_NS}}}inMargin", {"left": "141", "right": "141", "top": "141", "bottom": "141"})

        hdr_border_id = str(tbl_cfg.get("border_fill_header", "10"))
        cell_border_id = str(tbl_cfg.get("border_fill_cell", "8"))

        for r_idx, row in enumerate(parsed_rows):
            tr = ET.SubElement(tbl, f"{{{HP_NS}}}tr")
            is_header = r_idx == 0
            border_id = hdr_border_id if is_header else cell_border_id
            base_char_id = "31" if is_header else "24"
            bold_char_id = "1031" if is_header else "1024"

            for c_idx in range(num_cols):
                raw_cell = row[c_idx] if c_idx < len(row) else ""

                # <br> 태그를 정규식으로 분할하여 다중 행 문단으로 생성
                sub_lines = re.split(r"</?br\s*/?>|\n", raw_cell, flags=re.IGNORECASE)
                clean_sub_lines = [sl.strip() for sl in sub_lines if sl.strip()]
                if not clean_sub_lines:
                    clean_sub_lines = [""]

                tc = ET.SubElement(
                    tr,
                    f"{{{HP_NS}}}tc",
                    {
                        "name": "",
                        "header": "1" if is_header else "0",
                        "hasMargin": "0",
                        "protect": "0",
                        "editable": "0",
                        "dirty": "0",
                        "borderFillIDRef": border_id,
                    },
                )

                sub = ET.SubElement(
                    tc,
                    f"{{{HP_NS}}}subList",
                    {
                        "id": "",
                        "textDirection": "HORIZONTAL",
                        "lineWrap": "BREAK",
                        "vertAlign": "CENTER",
                        "linkListIDRef": "0",
                        "linkListNextIDRef": "0",
                        "textWidth": "0",
                        "textHeight": "0",
                        "hasTextRef": "0",
                        "hasNumRef": "0",
                    },
                )

                for sl in clean_sub_lines:
                    # 표 내부 기본 중앙정렬 paraPrIDRef="19" 통일
                    cell_p = ET.SubElement(
                        sub,
                        f"{{{HP_NS}}}p",
                        {
                            "id": self._get_id(),
                            "paraPrIDRef": "19",
                            "styleIDRef": "10" if is_header else "11",
                            "pageBreak": "0",
                            "columnBreak": "0",
                            "merged": "0",
                        },
                    )

                    if "**" in sl:
                        parts = re.split(r"(\*\*[^*]+?\*\*)", sl)
                        for part in parts:
                            if not part:
                                continue
                            if part.startswith("**") and part.endswith("**") and len(part) >= 4:
                                inner = part[2:-2]
                                r = ET.SubElement(cell_p, f"{{{HP_NS}}}run", {"charPrIDRef": bold_char_id})
                                t = ET.SubElement(r, f"{{{HP_NS}}}t")
                                t.text = inner
                            else:
                                r = ET.SubElement(cell_p, f"{{{HP_NS}}}run", {"charPrIDRef": base_char_id})
                                t = ET.SubElement(r, f"{{{HP_NS}}}t")
                                t.text = part
                    else:
                        clean_text = sl.replace("**", "").replace("__", "").strip()
                        r = ET.SubElement(cell_p, f"{{{HP_NS}}}run", {"charPrIDRef": base_char_id})
                        t = ET.SubElement(r, f"{{{HP_NS}}}t")
                        t.text = clean_text

                ET.SubElement(tc, f"{{{HP_NS}}}cellAddr", {"colAddr": str(c_idx), "rowAddr": str(r_idx)})
                ET.SubElement(tc, f"{{{HP_NS}}}cellSpan", {"colSpan": "1", "rowSpan": "1"})
                ET.SubElement(tc, f"{{{HP_NS}}}cellSz", {"width": str(col_widths[c_idx]), "height": str(2132 * max(1, len(clean_sub_lines)))})
                ET.SubElement(tc, f"{{{HP_NS}}}cellMargin", {"left": "141", "right": "141", "top": "141", "bottom": "141"})

        return p

    def _build_table_element(self, table_lines: list[str]) -> ET.Element | None:
        """마크다운 파이프 표를 파싱하여 HWPX <hp:tbl> 구조로 생성."""
        if not table_lines:
            return None

        parsed_rows: list[list[str]] = []
        for line in table_lines:
            cells = [c.strip() for c in line.strip("|").split("|")]
            if all(re.match(r"^:?-+:?$", c) for c in cells if c):
                continue
            parsed_rows.append(cells)

        return self._build_table_from_rows(parsed_rows)

    def _write_hwpx_package(self, output_path: Path, files: dict[str, bytes]) -> None:
        """HWPX OCF 패키지 규칙에 맞추어 ZIP 파일 생성 (mimetype 무압축 첫 번째 저장)."""
        with zipfile.ZipFile(output_path, "w") as zout:
            mimetype_bytes = files.get("mimetype", b"application/hwp+zip")
            zout.writestr("mimetype", mimetype_bytes, compress_type=zipfile.ZIP_STORED)

            for name, content in files.items():
                if name == "mimetype":
                    continue
                zout.writestr(name, content, compress_type=zipfile.ZIP_DEFLATED)


def convert_markdown_to_hwpx(
    markdown_path: str | Path,
    output_path: str | Path | None = None,
    template_path: str | Path = "krauv_template.hwpx",
    mapping_path: str | Path = "config/hwpx_style_mapping.yaml",
) -> str:
    """단일 함수 호출 인터페이스."""
    converter = MarkdownHWPXConverter(template_path=template_path, mapping_path=mapping_path)
    return converter.convert_file(markdown_path, output_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Pure Python Markdown to HWPX Converter")
    parser.add_argument("--input", "-i", required=True, help="입력 마크다운 파일 경로")
    parser.add_argument("--output", "-o", help="출력 HWPX 파일 경로")
    parser.add_argument("--template", "-t", default="krauv_template.hwpx", help="HWPX 템플릿 파일 경로")
    parser.add_argument("--mapping", "-m", default="config/hwpx_style_mapping.yaml", help="스타일 매핑 YAML 파일 경로")

    args = parser.parse_args()
    out = convert_markdown_to_hwpx(
        markdown_path=args.input,
        output_path=args.output,
        template_path=args.template,
        mapping_path=args.mapping,
    )
    print(f"HWPX 생성 완료: {out}")


if __name__ == "__main__":
    main()
