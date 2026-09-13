# Changelog

All notable changes to the **Report Generator** project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [v2.1.2] - 2026-09-13

### 🚀 Added

- **사용 불가 모델 동적 제외 및 자동 영속화 (`src/models/client.py`)**:
  - `load_unavailable_models`: `config/unavailable_models.json`을 읽어 provider별 차단 모델 목록 자동 로드.
  - `persist_unavailable_model`: 런타임에 404(Model not found) 또는 영구적 파라미터 불가 오류 발생 시 차단 목록에 실시간 기록.
  - `UnifiedModelClient`: 모델 후보군(`candidate_targets`) 구성 시 차단 목록의 모델을 자동 제외하고 차단되지 않은 첫 번째 가용 모델을 Primary로 자동 승격.
- **Gemini 슬라이딩 윈도우 Rate Limiter (`src/models/client.py`)**:
  - `rate_limits` 설정(RPM, TPM) 기반의 정밀 요청/토큰 사전 예약 대기 메커니즘 도입으로 쿼터 고갈 차단.
- **모델 클라이언트 회귀 검증 단위 테스트 추가 (`tests/test_model_client_unavailable.py`)**:
  - 모델 참조 정규화, 영구 오류 식별, 사용 불가 모델 사전 필터링 검증 3종 테스트 추가 (총 27개 테스트 100% 통과).
- **문서 심볼릭 링크 복원 (`changelogs.md`)**:
  - `changelogs.md -> changelog.md` 링크 복원으로 파일명 접근 호환성 유지.

### 🔄 Changed

- **에이전트 모델 설정 전면 정비 (`config/agents_config.yaml`)**:
  - 6대 에이전트(`drafter`, `researcher`, `expander`, `reviewer`, `gatekeeper`, `merger`) 설정 완전 복원.
  - 현재 지원 중단 및 차단된 모델(`google/gemma-4-31b-it`, `meta/llama-3.1-70b-instruct`, `nvidia/llama-3.1-nemotron-70b-instruct`, `gemini-2.5-flash-lite`)을 활성 목록에서 완전 배제.
  - 안정성이 검증된 모델(`nvidia/nemotron-3.5-lightning-30b-a3b`, `nvidia/nemotron-3-super-120b-a12b`, `openai/gpt-oss-20b`, `openai/gpt-oss-120b`, `gemini-2.5-flash`)로 재배치.
- **Drafter 및 Researcher 최신 아키텍처 복원 (`src/agents/`)**:
  - 구버전 브랜치 병합 과정에서 덮어써졌던 `src/agents/drafter.py` 및 `src/agents/researcher.py`를 `main`의 최신 구조(`src.core.*`, `src.models.client.UnifiedModelClient`, `src.tools.search`)로 전면 복원하여 모듈 임포트 에러 완전 해소.

### 🗑️ Removed

- **구버전 레거시 파일 4종 완전 삭제**:
  - `src/utils/model_client.py` (`src/models/client.py`로 기능 통합 완료)
  - `src/utils/preprocessor.py` (`src/tools/preprocessor.py`로 대체 완료)
  - `src/utils/prompting.py` (프롬프트 템플릿 및 통합 클라이언트로 대체 완료)
  - `src/utils/summarize_refs.py` (`src/tools/preprocessor.py`로 대체 완료)

## [v2.1.1] - 2026-09-08

### 🚀 Added

- **다중 과제 작업 의뢰 스펙 체계화 (`works/*.yaml`, `report_list.md`)**:
  - `works/` 디렉터리 내 개별 보고서 의뢰 설정 파일(`report_type`, `topic`, `direction`, `target_perspective`, `tone`, `target_pages`, `target_chars`) 규격화.
  - `main.py`의 `--state-file` 인자를 통한 과제별 분기 실행 및 독립 세션(`--thread-id`) 지원.
  - 전체 과제 진행 현황 및 납기/명의자 관리를 위한 `report_list.md` 연동 지원.
- **문서 접근성 동기화 (`changelogs.md`)**:
  - `changelog.md`와 `changelogs.md` 간 심볼릭 링크를 구성하여 단일 원본 기반의 파일명 호환성 보장.

### 🔄 Changed

- **조사보고서 실질 서술 분량 측정 정교화 (`src/utils/final_guard.py`)**:
  - `is_valid_quality_content`의 서술형 텍스트 길이 측정 시, 마크다운 불릿(`*`, `-`, `>`) 및 번호형 글머리 기호의 선행 기호만 정규식(`^[\*\-\>\d\.\s]+`)으로 정제하고 실제 서술 텍스트는 정상 분량으로 온전히 산정하도록 개선 (유효 불릿형 보고서의 오탐 탈락 방지).
- **macOS 유니코드 NFD/NFC 정규화 대응**:
  - macOS 환경에서 자모 분리(NFD) 방식으로 저장된 레퍼런스 파일명을 표준 NFC로 자동 정규화(`unicodedata.normalize('NFC', ...)`)하여 `.junk_archive/` 격리 및 참조 시 파일 탐색 누락 방지.
- **파이프라인 가이드라인 전면 개정 (`guideline.md`)**:
  - 다중 과제 명세서(`works/*.yaml`) 작성 및 CLI 실행 가이드, 3대 실증 출처 원칙, 조사보고서 품질 게이트 및 `.junk_archive/` 격리 기준 상세 반영.

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
    3. **3순위 (모든 자료 부재 시)**: 허위 출처를 일체 날조하지 않고 "별도의 외부 인용 문헌이 존재하지 않습니다"로 투명하게 고지.
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
