# 보고서 생성기

## 가상 환경 생성 및 활성화

python3 -m venv .venv
source .venv/bin/activate # Windows: .\.venv\Scripts\activate

## 필수 라이브러리 설치

pip install -r requirements.txt

## .env 설정 (프로바이더별)

```bash
# NVIDIA NIM
NIM_API_KEY=...

# Gemini
GEMINI_API_KEY=...

# OpenAI 호환 API를 쓸 경우
OPENAI_API_KEY=...
```

## 에이전트별 권장 모델(비용 최적화)

- Drafter: `gemini-2.5-flash-lite` (목차/초안)
- Researcher: `meta/llama-3.1-8b-instruct` on NVIDIA NIM (다회 조사/요약)
- Expander: `gemini-2.5-flash` (섹션 확장 본문)

## 재실행/재개 (체크포인트)

```bash
# 일반 실행
python main.py --thread-id test-run-001 --state-file config/initial_state.yaml --pipeline-config config/pipeline_config.yaml

# 실패 후 같은 thread-id로 이어서 재개
python main.py --thread-id test-run-001 --resume
```

## 초기 상태 파일 분리 (YAML/MD)

- 기본 파일: [config/initial_state.yaml](/Users/h4/Documents/workspace/report-generator/config/initial_state.yaml)
- Markdown을 쓰려면 YAML front matter 포함 파일 사용: [initial_state.example.md](/Users/h4/Documents/workspace/report-generator/config/initial_state.example.md)

### 설정 우선순위

1. [pipeline_config.yaml](/Users/h4/Documents/workspace/report-generator/config/pipeline_config.yaml) (전역 기본값)
2. `state-file`의 동일 키 (실행별 override)

예: `max_loops`, `max_concurrency`, `target_6_min_length`, `target_total_min_length`

## 디렉터리 구조

```text
📁report_generator_project/
├── 📁config/                   # 에이전트별 모델/파라미터 설정 (하드코딩 방지)
│   ├── agents_config.yaml      # (예) Drafter: GPT-4o, Expander: Claude-3.5-Sonnet 등
│   └── pipeline_config.yaml    # 최대 루프 횟수, 병렬 처리 동시성(Concurrency) 제한 등
├── 📁prompts/                  # 프롬프트 분리 관리 (튜닝 효율성 확보)
│   ├── drafter.md
│   ├── researcher.md
│   ├── expander.md             # 섹션 보강용 지침 (설명조/개조식 혼용 등)
│   └── reviewer.md
├── 📁src/                      # 파이프라인 핵심 로직
│   ├── 📁agents/               # 각 에이전트의 구동 모듈
│   │   ├── __init__.py
│   │   ├── drafter.py
│   │   ├── researcher.py
│   │   ├── expander.py         # 비동기 병렬 생성의 핵심 모듈
│   │   ├── reviewer.py
│   │   └── gatekeeper.py       # 방향성 이탈 검증 및 루프 제어
│   ├── 📁graph/                # LangGraph 워크플로우 제어부
│   │   ├── __init__.py
│   │   ├── state.py            # 병렬 처리를 지원하는 상태(State) 정의
│   │   └── workflow.py         # 노드 및 조건부 엣지(루프/병렬 분기) 연결
│   ├── 📁tools/                # 외부 연동 도구
│   │   └── web_search.py       # 기획보고서용 시장/트렌드 조사 도구 (Tavily/SerpAPI 등)
│   └── 📁utils/
│       ├── file_manager.py     # Append-Only 규칙 강제 및 파일 입출력 관리
│       └── chunking.py         # 컨텍스트 유실 방지를 위한 요약/청킹 유틸리티
├── 📁workspace/                # 입출력 데이터 격리 공간 (회장님 기획안 반영)
│   ├── 📁source/               # 사용자 제공 기초 자료 입력
│   ├── 📁reference/            # 키워드별 수집 원시 자료 및 조사보고서 (research_*.md)
│   └── 📁report/               # 버전별 생성물 및 최종본 (*_v1.md ~ *_final.md)
├── .env                        # API 키 및 환경변수
├── requirements.txt            # 필요 패키지 (langgraph, langchain, asyncio 등)
└── main.py                     # 시스템 실행 진입점 (CLI 또는 API 형태)
```
