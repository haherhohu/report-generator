"""Unit tests for the pure Python Markdown to HWPX Converter."""
from __future__ import annotations

import os
from pathlib import Path
import re
import tempfile
import xml.etree.ElementTree as ET
import zipfile

from src.tools.hwpx_converter import MarkdownHWPXConverter, convert_markdown_to_hwpx
from src.tools.hwpx_exporter import export_markdown_to_hwpx


def test_hwpx_converter_minimal_document():
    sample_md = """# 테스트 보고서 제목

> **【Executive Summary: 요약】**
> 본 문서는 파이썬 HWPX 변환기 단위 테스트를 위한 문서입니다.

---

## Ⅰ. 추진 배경 및 개요

### 1. 세부 개요 분석

○ **첫 번째 핵심 항목**: 본문 내용입니다.
   - 세부 하위 항목 A
   - 세부 하위 항목 B

**[표 Ⅰ-1]** 시험평가 현황 비교표

| 구분 | 주요 규격 | 인증 여부 | 비고 |
| :--- | :--- | :--- | :--- |
| **소형 무인기** | FAA Part 107 | 획득 완료 | 상업용 비행 |
| **중대형 무인기** | FAA Part 135 | 심사 중 | BVLOS 비행 |

**【그림 Ⅰ-1】** 시험평가 절차 체계도

※ 자료: 국토교통부 및 항공안전기술원 공인 통계 DB
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_md = Path(tmpdir) / "test_report.md"
        tmp_hwpx = Path(tmpdir) / "test_report.hwpx"
        tmp_md.write_text(sample_md, encoding="utf-8")

        result_path = convert_markdown_to_hwpx(
            markdown_path=tmp_md,
            output_path=tmp_hwpx,
            template_path="krauv_template.hwpx",
        )

        assert os.path.exists(result_path)
        assert result_path == str(tmp_hwpx)

        with zipfile.ZipFile(result_path, "r") as z:
            # 1. mimetype 검증
            infolist = z.infolist()
            assert infolist[0].filename == "mimetype"
            assert infolist[0].compress_type == 0
            assert z.read("mimetype") == b"application/hwp+zip"

            # 2. section0.xml 구조 및 내용 검증
            sec_bytes = z.read("Contents/section0.xml")
            root = ET.fromstring(sec_bytes)

            paras = root.findall("{http://www.hancom.co.kr/hwpml/2011/paragraph}p")
            # 표지 타이틀 검증: 템플릿 기본 문구(UAV 교육주제...) 완전 삭제 및 문서 제목 반영 확인
            p8_text = "".join(paras[8].itertext()).strip()
            assert "UAV 교육주제" not in p8_text
            assert p8_text == "", f"템플릿 타이틀 잔여 문구가 남아있습니다: {repr(p8_text)}"

            title_elem = paras[9].find(".//{http://www.hancom.co.kr/hwpml/2011/paragraph}t")
            assert title_elem is not None
            assert title_elem.text == "테스트 보고서 제목"
            assert "최신 기술동향" not in title_elem.text

            h2_paras = [p for p in paras if p.attrib.get("styleIDRef") == "2"]
            assert len(h2_paras) >= 1
            h2_text = "".join(h2_paras[0].itertext()).strip()
            assert "Ⅰ. 추진 배경 및 개요" in h2_text

            tables = root.findall(".//{http://www.hancom.co.kr/hwpml/2011/paragraph}tbl")
            assert len(tables) >= 1


def test_hwpx_converter_11_layout_improvements():
    """11가지 서식 및 조판 개선 요구사항 통합 검증."""
    test_md = """# 조판 품질 개선 종합 검증 보고서

> **【Executive Summary: 핵심 요약】**
> 본 문서는 HWPX 변환기의 11가지 레이아웃 개선 요구사항을 검증합니다.

---

## Ⅰ. 실증 테스트 본문

### 1. 세부 분석 항목

본문 단락 1입니다. 문단 중간에 **강조 단어 1**과 **강조 단어 2**가 포함되어 있습니다.

##### 소제목 5단계 검증용 헤더

○ **개조식 1단계 볼드**: 본문 설명 텍스트입니다.
- **볼드 복수 개 겹침 검증**: 첫 번째 **강조** 및 두 번째 **강조** 항목
- 일반 대시 항목 텍스트

**【그림 Ⅰ-1】** 1x1 박스 변환 검증 그림
> - **구조도**: [A] -> [B] -> [C]
> - **프롬프트**: Infographic prompt text
> - **조판 규격**: 1920x1080

**[표 Ⅰ-1]** 긴 다단 표 및 페이지 분할 검증표

| 구분 | 규격 | 인증 | 비고 |
| :--- | :--- | :--- | :--- |
| **항목 1** | FAA 107 | 완료 | 상업 비행 |
| **항목 2** | FAA 135 | 심사 | BVLOS |

```html
<table>
  <thead>
    <tr>
      <th>HTML 구분</th>
      <th>HTML 규격</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><strong>HTML 주요 대상</strong></td>
      <td>인라인 변환 테스트</td>
    </tr>
  </tbody>
</table>
```
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_md = Path(tmpdir) / "test_11_reqs.md"
        tmp_hwpx = Path(tmpdir) / "test_11_reqs.hwpx"
        tmp_md.write_text(test_md, encoding="utf-8")

        result_path = convert_markdown_to_hwpx(
            markdown_path=tmp_md,
            output_path=tmp_hwpx,
            template_path="krauv_template.hwpx",
        )

        assert os.path.exists(result_path)

        with zipfile.ZipFile(result_path, "r") as z:
            # 1. header.xml 검증
            h_root = ET.fromstring(z.read("Contents/header.xml"))
            HH = "{http://www.hancom.co.kr/hwpml/2011/head}"
            HC = "{http://www.hancom.co.kr/hwpml/2011/core}"
            HP = "{http://www.hancom.co.kr/hwpml/2011/paragraph}"

            # 요구사항 11: base charPr 클론(id >= 1000) 존재 확인 (폰트/크기 동일 유지)
            c_props = h_root.find(f".//{HH}charProperties")
            cloned_bolds = [cp for cp in c_props if int(cp.attrib.get("id", 0)) >= 1000]
            assert len(cloned_bolds) >= 40

            # 요구사항 8: Level 2 bullet Shift-Tab 내어쓰기 paraPr 1030 존재 확인
            p1030 = h_root.find(f".//{HH}paraPr[@id='1030']")
            assert p1030 is not None
            left_elem = p1030.find(f".//{HC}left")
            intent_elem = p1030.find(f".//{HC}intent")
            assert left_elem.attrib["value"] == "3800"
            assert intent_elem.attrib["value"] == "-1469"

            # 요구사항 5: 캡션 paraPr 자동 넘버링 끄기 확인
            p28 = h_root.find(f".//{HH}paraPr[@id='28']")
            p35 = h_root.find(f".//{HH}paraPr[@id='35']")
            assert p28.find(f"{HH}heading").attrib["type"] == "NONE"
            assert p35.find(f"{HH}heading").attrib["type"] == "NONE"

            # 2. section0.xml 검증
            s_root = ET.fromstring(z.read("Contents/section0.xml"))
            paras = s_root.findall(f".//{HP}p")

            # 요구사항 1: '-' 뒤의 '**bold**' 보존 및 분리 확인
            bullet2_paras = [p for p in paras if p.attrib.get("paraPrIDRef") == "1030"]
            assert len(bullet2_paras) >= 2
            # 첫 번째 bullet2 검증: **볼드 복수 개 겹침 검증**
            b2_runs = bullet2_paras[0].findall(f"{HP}run")
            bold_run_texts = [
                "".join(r.itertext())
                for r in b2_runs
                if int(r.attrib.get("charPrIDRef", 0)) >= 1000
            ]
            assert "볼드 복수 개 겹침 검증" in bold_run_texts
            assert "강조" in bold_run_texts

            # 요구사항 2: 한 줄 띄기 빈 문단 존재 확인
            empty_paras = [
                p for p in paras
                if not "".join(p.itertext()).strip() and p.find(f".//{HP}tbl") is None
            ]
            assert len(empty_paras) >= 3

            # 요구사항 3: 그림 파트 1x1 테두리 표 변환 확인
            fig_boxes = [
                t for t in s_root.findall(f".//{HP}tbl")
                if t.attrib.get("rowCnt") == "1" and t.attrib.get("colCnt") == "1"
            ]
            assert len(fig_boxes) >= 1
            assert fig_boxes[0].attrib.get("borderFillIDRef") == "8"
            assert fig_boxes[0].attrib.get("numberingType") == "NONE"

            # 요구사항 6 & 9: 표 너비(49000), 들여쓰기 제거(0), 글자처럼 취급 해제(0), 셀 분할(CELL)
            data_tbls = [
                t for t in s_root.findall(f".//{HP}tbl")
                if not (t.attrib.get("rowCnt") == "1" and t.attrib.get("colCnt") == "1")
            ]
            assert len(data_tbls) >= 2  # 마크다운 표 1개 + HTML 변환 표 1개
            for dt in data_tbls:
                assert dt.attrib.get("numberingType") == "NONE"
                assert dt.attrib.get("pageBreak") == "CELL"
                pos = dt.find(f"{HP}pos")
                assert pos.attrib.get("treatAsChar") == "0"
                sz = dt.find(f"{HP}sz")
                assert sz.attrib.get("width") == "49000"

            # 부모 문단 들여쓰기 0 확인
            table_parents = [
                p for p in paras if p.find(f".//{HP}tbl") is not None
            ]
            for tp in table_parents:
                assert tp.attrib.get("paraPrIDRef") == "0"

            # 요구사항 7: ##### 헤더가 볼드 본문 문단으로 변환되었는지 확인
            h5_converted = [
                p for p in paras
                if "소제목 5단계 검증용 헤더" in "".join(p.itertext())
            ]
            assert len(h5_converted) >= 1
            # 헤더 # 표시 제거 및 볼드 run 확인
            h5_p = h5_converted[0]
            assert "#" not in "".join(h5_p.itertext())
            h5_bold_runs = [
                r for r in h5_p.findall(f"{HP}run")
                if int(r.attrib.get("charPrIDRef", 0)) >= 1000
            ]
            assert len(h5_bold_runs) >= 1

            # 요구사항 10: HTML <table>이 표로 변환되었는지 확인
            html_table_found = False
            for dt in data_tbls:
                txt = "".join(dt.itertext())
                if "HTML 구분" in txt and "HTML 주요 대상" in txt:
                    html_table_found = True
                    break
            assert html_table_found, "HTML <table> 태그가 HWPX 표로 정상 변환되지 않았습니다."


def test_hwpx_converter_6_final_refinements():
    """6가지 추가 서식 및 조판 정제 요구사항 단위 검증:
    1. 표 셀 내부 <br> -> <hp:subList> 내 복수 <hp:p> 분할
    2. 일반 본문 문단 맨 앞 1칸(10pt) 들여쓰기 (paraPr 1040)
    3. 표 셀 내부 중앙정렬 (paraPr 19)
    4. 문단 중간 한문(Hanja) 및 괄호 없는 외래어 정제
    5. \\* 로 시작하는 각주/출처를 당구장 표시(※)로 변환
    6. 참고문헌 섹션 좌측정렬 및 자간 깨짐 방지 (paraPr 1050)
    """
    test_md = """# 최종 서식 정제 검증 보고서

## Ⅰ. 실증 본문 분석

일반 본문 문단입니다. 관공서 표준에 따라 첫 줄 1칸 들여쓰기 10pt가 적용되어야 합니다.

문단 중간에서 全美 시장 및 美 국방부와 委員會의 결정이며 固定費 절감과 ecosystem 구축, Tooele 육군창 협력이 필요하다.

**[표 Ⅰ-1]** 다중 행 및 정렬 검증 표

| 구분 | 주요 내용 및 세부 규격 | 상태 |
| :--- | :--- | :--- |
| **인증 항목** | 1단계 사전 신청 접수<br>**2단계 서류 기술 심사**<br>3단계 최종 비행 시험 | 승인 완료 |

\\* 주: 본 표의 시험 규격은 FAA 기준을 준수함.
\\* 자료: 미국 교통부 공식 통계 보고서

## Ⅱ. 참고문헌 및 출처

1. FAA, "Urban Air Mobility Concept of Operations v2.0", https://www.faa.gov/uas/advanced_aviation/long_url_sample_string_12345/
2. US DOT, "Advanced Air Mobility National Strategy", https://www.transportation.gov/aam-strategy-document-download/
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_md = Path(tmpdir) / "test_6_refinements.md"
        tmp_hwpx = Path(tmpdir) / "test_6_refinements.hwpx"
        tmp_md.write_text(test_md, encoding="utf-8")

        result_path = convert_markdown_to_hwpx(
            markdown_path=tmp_md,
            output_path=tmp_hwpx,
            template_path="krauv_template.hwpx",
        )

        assert os.path.exists(result_path)

        with zipfile.ZipFile(result_path, "r") as z:
            h_root = ET.fromstring(z.read("Contents/header.xml"))
            s_root = ET.fromstring(z.read("Contents/section0.xml"))
            HH = "{http://www.hancom.co.kr/hwpml/2011/head}"
            HC = "{http://www.hancom.co.kr/hwpml/2011/core}"
            HP = "{http://www.hancom.co.kr/hwpml/2011/paragraph}"

            # 1. header.xml 검증
            # 1-1. paraPr 1040 제거 확인 (문단 모양 들여쓰기가 아닌 텍스트 앞 ' ' 방식 적용)
            p1040 = h_root.find(f".//{HH}paraPr[@id='1040']")
            assert p1040 is None, "인위적 문단 여백 들여쓰기 paraPr 1040이 존재하면 안 됩니다."

            # 1-2. paraPr 1050 (참고문헌 좌측정렬 및 단어 줄바꿈)
            p1050 = h_root.find(f".//{HH}paraPr[@id='1050']")
            assert p1050 is not None, "paraPr 1050 (참고문헌)이 header.xml에 없습니다."
            align_1050 = p1050.find(f".//{HH}align")
            break_1050 = p1050.find(f".//{HH}breakSetting")
            assert align_1050 is not None and align_1050.attrib.get("horizontal") == "LEFT", "참고문헌 정렬이 LEFT가 아닙니다."
            assert break_1050 is not None and break_1050.attrib.get("breakLatinWord") == "BREAK_WORD", "참고문헌 라틴 문자 줄바꿈이 BREAK_WORD가 아닙니다."

            # 2. section0.xml 검증
            paras = s_root.findall(f".//{HP}p")
            sec_raw = z.read("Contents/section0.xml").decode("utf-8")

            # 검증 0: 표지 템플릿 기본 문구 완전 삭제 및 문서 제목 단독 노출 확인
            p8_text = "".join(paras[8].itertext()).strip()
            assert "UAV 교육주제" not in p8_text
            assert p8_text == "", f"템플릿 타이틀 잔여 문구가 남아있습니다: {repr(p8_text)}"
            p9_text = "".join(paras[9].itertext()).strip()
            assert "최신 기술동향" not in p9_text
            assert p9_text == "최종 서식 정제 검증 보고서"

            # 검증 1: 표 셀 내부 <br> -> <hp:subList> 내 복수 <hp:p> 분할 및 <br> 태그 미노출
            assert "<br>" not in sec_raw and "<br/>" not in sec_raw and "</br>" not in sec_raw, "section0.xml에 잔여 <br> 태그가 존재합니다."
            tables = s_root.findall(f".//{HP}tbl")
            assert len(tables) >= 1
            sample_tbl = tables[0]
            # 1단계, 2단계, 3단계가 포함된 subList 찾기
            multiline_cell_found = False
            for tc in sample_tbl.findall(f".//{HP}tc"):
                sub = tc.find(f"{HP}subList")
                if sub is not None:
                    cell_ps = sub.findall(f"{HP}p")
                    cell_texts = ["".join(p.itertext()).strip() for p in cell_ps]
                    if any("1단계" in t for t in cell_texts) and any("2단계" in t for t in cell_texts) and any("3단계" in t for t in cell_texts):
                        assert len(cell_ps) == 3, f"3개 줄바꿈 행이 3개의 <hp:p>로 생성되지 않았습니다: {len(cell_ps)}"
                        multiline_cell_found = True
                        # 검증 3: 표 셀 내부 paraPrIDRef="19" (중앙정렬) 확인
                        for cp in cell_ps:
                            assert cp.attrib.get("paraPrIDRef") == "19", "표 셀 문단의 paraPrIDRef가 19(중앙정렬)가 아닙니다."
                        # 2단계 볼드 확인
                        bold_runs = [r for r in cell_ps[1].findall(f"{HP}run") if int(r.attrib.get("charPrIDRef", 0)) >= 1000]
                        assert len(bold_runs) >= 1, "표 셀 내부 볼드가 정상 적용되지 않았습니다."
                        break
            assert multiline_cell_found, "<br>로 분할된 셀을 찾을 수 없습니다."

            # 검증 2: 일반 본문 문단 맨 앞 빈칸 하나(" ") 들여쓰기 및 기본 바탕글 paraPr 0 유지
            body_paras = [
                p for p in paras
                if p.attrib.get("paraPrIDRef") == "0" and p.attrib.get("styleIDRef") == "0" and "일반 본문 문단입니다" in "".join(p.itertext())
            ]
            assert len(body_paras) >= 1, "본문 문단에 기본 바탕글 paraPrIDRef='0'이 적용되지 않았습니다."
            first_t = body_paras[0].find(f".//{HP}t")
            assert first_t is not None and first_t.text.startswith(" "), f"본문 시작 맨 앞에 빈칸 하나(' ')가 들어가지 않았습니다: {repr(first_t.text[:5])}"

            # 검증 4: 문단 중간 한문 및 외래어 정제
            all_text = "".join(s_root.itertext())
            assert "全美" not in all_text, "全美 한문이 정제되지 않았습니다."
            assert "전미" in all_text, "전미 한글로 변환되지 않았습니다."
            assert "美 국방부" not in all_text, "美 국방부가 정제되지 않았습니다."
            assert "미국 국방부" in all_text, "미국 국방부로 변환되지 않았습니다."
            assert "委員會" not in all_text, "委員會 한문이 정제되지 않았습니다."
            assert "위원회" in all_text, "위원회 한글로 변환되지 않았습니다."
            assert "固定費" not in all_text, "固定費 한문이 정제되지 않았습니다."
            assert "고정비" in all_text, "고정비 한글로 변환되지 않았습니다."
            assert "ecosystem" not in all_text, "ecosystem 외래어가 정제되지 않았습니다."
            assert "생태계" in all_text, "생태계 한글로 변환되지 않았습니다."
            assert "Tooele 육군창" not in all_text, "Tooele 육군창이 병기되지 않았습니다."
            assert "투엘(Tooele) 육군창" in all_text, "투엘(Tooele) 육군창으로 변환되지 않았습니다."

            # 검증 5: \* -> ※ 당구장 표시 변환
            assert "\\*" not in all_text, "이스케이프된 \\*가 남아있습니다."
            note_paras = [p for p in paras if "※ 주:" in "".join(p.itertext()) or "※ 자료:" in "".join(p.itertext())]
            assert len(note_paras) >= 2, "\\* 주/자료가 ※ 당구장 표시로 변환되지 않았습니다."

            # 검증 6: 참고문헌 섹션 좌측정렬 (paraPrIDRef="1050")
            ref_paras = [p for p in paras if p.attrib.get("paraPrIDRef") == "1050"]
            assert len(ref_paras) >= 2, "참고문헌 문단에 paraPrIDRef='1050'이 적용되지 않았습니다."
            ref_texts = ["".join(p.itertext()) for p in ref_paras]
            assert any("Urban Air Mobility Concept of Operations" in t for t in ref_texts)


def test_hwpx_exporter_integration():
    sample_md = "# 통합 테스트 문서\n\n## Ⅰ. 개요\n\n본문 내용"
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_md = Path(tmpdir) / "export_test.md"
        tmp_md.write_text(sample_md, encoding="utf-8")

        exported_path = export_markdown_to_hwpx(tmp_md)
        assert exported_path is not None
        assert os.path.exists(exported_path)
        assert exported_path.endswith(".hwpx")


if __name__ == "__main__":
    test_hwpx_converter_minimal_document()
    test_hwpx_converter_11_layout_improvements()
    test_hwpx_converter_6_final_refinements()
    test_hwpx_exporter_integration()
    print("ALL HWPX CONVERTER TESTS PASSED!")

