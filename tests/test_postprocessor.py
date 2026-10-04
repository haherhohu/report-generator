"""Unit tests for unified ReportPostProcessor."""
from __future__ import annotations

import unittest
from src.processors.postprocessor import process_report_markdown


class TestReportPostProcessor(unittest.TestCase):
    def test_postprocessor_pipeline(self):
        sample_md = """# UAV 산업 활성화를 위한 글로벌 인증 표준 및 기술 동향 (영국)

<think>
internal cot monologue
</think>

## Ⅰ. 조사 배경

본 연구팀의 자체 분석 결과에 따르면 신뢰성이 확인되었다.
또한 새만금/Physical AI 기반 RAMS 시험·평가센터 구축(안)이 운영 중이다.

| 항목 | 내용 |
| --- | --- |
| 규제 | CAP 722 |

**[표 Ⅰ-1]** 영국의 무인기 규제 체계
"""
        cleaned = process_report_markdown(sample_md, topic="영국")

        # 1. CoT 태그 박멸 확인
        self.assertNotIn("<think>", cleaned)
        self.assertNotIn("internal cot monologue", cleaned)

        # 2. 사실성 핫픽스: 자체 분석 교정 확인
        self.assertNotIn("자체 분석 결과", cleaned)

        # 3. 사실성 핫픽스: 새만금 가상 센터 기정사실화 차단 확인
        self.assertNotIn("새만금/Physical AI 기반 RAMS 시험·평가센터 구축(안)", cleaned)

        # 4. Executive Summary 탑재 확인
        self.assertIn("> **【Executive Summary: 핵심 요약】**", cleaned)

        # 5. 표 캡션 앞 빈 줄(개행) 분리 확인
        self.assertIn("\n\n**[표 Ⅰ-1]**", cleaned)


if __name__ == "__main__":
    unittest.main()
