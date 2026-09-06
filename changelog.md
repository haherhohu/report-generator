# Changelog

All notable changes to the **Report Generator** project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [v2.1.0] - 2026-09-06

### 🚀 Added

- **조사보고서 품질 게이트 (`src/utils/final_guard.py`)**:
  - `is_valid_quality_content` 도입: 본문 길이 150자 미만 단편, SSL 연결 에러/검색 실패 문구, 표만 덜렁 있고 서술 본문(80자 미만)이 결여된 불량 조사 문건 자동 판별.
  - `clean_junk_reference_files`: `workspace/reference/` 내 기존 함량미달 조사보고서를 자동 감지하여 `.junk_archive/`로 안전 격리 아카이빙하는 클리너 유틸리티 추가.
- **구조화된 웹 검색 결과 연계 (`src/tools/search.py`)**:
  - `perform_hybrid_research_structured` 추가: 단순 문자열 병합을 넘어 실제 수집된 레코드(URL, 제목, 스니펫, 출처 구분)를 구조화된 객체(`records`)로 반환.
  - 실제 검색 결과가 0건일 때 무의미한 가짜 더미 3줄을 날조하지 않고 `has_results=False`를 반환하여 안전한 폴백을 유도.
- **실증 3단계 참고문헌 빌더 (`src/agents/merger.py`)**:
  - `_build_grounded_bibliography` 구현:
    1. **1순위 (실제 수집된 웹 검색 자료)**: `state["verified_references"]`의 실제 URL 및 검증된 출처명 우선 등재.
    2. **2순위 (사용자 제공 원시자료)**: 웹 검색 부재 시 사용자가 직접 제공한 원본 파일명만 `제공 기초자료: [파일명]` 형태로 등재 (시스템 내부 생성 `research_*.md` 임시 파일은 철저히 배제).
    3. **3순위 (모든 자료 부재 시)**: 허위 출처를 일체 날조하지 않고 "별도 외부 참고문헌 없음"으로 투명하게 고지.
- **신규 단위 테스트 2종 추가**:
  - `tests/test_researcher_quality.py`: 표만 덜렁 있는 단편 감지, 불량품 Final 박제 방지, 검색 실패 시 사용자 제공 자료 연계 검증.
  - `tests/test_grounded_references.py`: 3단계 참고문헌 엄격 원칙 및 허위 출처(무인항공기 등) 생성 방지 검증.

### 🔄 Changed

- **5-Duplicate Guard Final 승격 조건 정합화 (`src/utils/final_guard.py`)**:
  - `should_reuse_or_create_final`: 품질 검증(`require_quality=True`)을 통과한 유효 아티팩트만 5회 카운트에 반영하도록 개선.
  - 기존에 생성된 Final 파일이 있더라도 내용이 부실(표만 덜렁 있거나 에러 텍스트)하면 재사용을 거부하고 정상화 유도.
  - `build_final_bundle_document`: 200자 미만 작은 조각 위주로 합쳐져 표 조각만 남던 로직을, 40자 이상의 온전한 서술 문단을 우선 결합하도록 개선.
- **조사 에이전트 다단계 안전망 강화 (`src/agents/researcher.py`)**:
  - 생성된 조사보고서가 표 위주이거나 분량 미달 시 1회 자동 심층 서술 보강 재시도.
  - 검색 실패 시 가짜 더미 대신 사용자가 제공한 원시 자료(`source_materials`)에서 팩트를 자동 발췌 연계.
- **섹션 팽창 에이전트 품질 지침 강화 (`src/agents/expander.py`)**:
  - 부록 장(`appendix_facts`)을 하드코딩 표가 아닌 실제 수집 데이터 기반 데이터시트로 생성하도록 정상화.
  - Sub-TOC 본문 작성 지침에 "표/도식만 1개 넣어두고 설명을 2~3줄로 끝내는 행위 엄격 금지 (최소 3개 이상의 상세 서술 문단 의무화)" 명시.
- **약어표(Glossary) 폴백 정규화 (`src/agents/merger.py`)**:
  - 본문에서 약어가 검출되지 않았을 때 특정 분야(UAV, UAS, FAA)의 하드코딩 약어가 무관한 보고서에 노출되던 문제를 차단하고, 분야 중립적인 표준 R&D 약어(`TRL`, `CAGR`, `R&D`, `KPI`, `M&A`, `API`, `IP`)만 선별 표기하도록 개선.
- **파이프라인 가이드라인 최신화 (`guideline.md`)**:
  - 실증 출처 3단계 원칙, 단편 표 방지 규격, 품질 게이트 및 `.junk_archive/` 버전 관리 규칙 반영.

### 🐛 Fixed

- **허위 참고문헌 하드코딩 완전 삭제 (`src/models/fallback_engine.py`)**:
  - 보고서 주제와 무관하게 삽입되던 무인항공기(UAV/FAA) 관련 5개 고정 가짜 참고문헌 코드 완전 제거.
- **본문 임의 문구 참고문헌 오염 차단 (`src/agents/merger.py`)**:
  - 본문 속 `※ 자료: 자체 분석 및 국책연구원...`, `※ 자료: 국가 공식 통계...` 등의 자동완성형 허구 문구가 정식 참고문헌 목록으로 긁어모아지던 버그 수정.
- **기존 함량미달 조사보고서 격리 완료**:
  - `workspace/reference/` 내 92개 조사 파일 중 SSL 인증 에러 문구 및 54자 극단적 단답형 더미 파일 8건을 `.junk_archive/` 디렉토리로 안전 격리 아카이빙.
