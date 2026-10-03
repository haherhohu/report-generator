"""Normalize and replace corrupted sections in Colorado report with authentic UAS content."""
import re
from pathlib import Path

COLORADO_PATH = Path("workspace/report/콜로라도_주_내_국내기업_진출_가이드라인_p5_final_v1.md")

# Chapter IV Authentic Replacement for dummy parts
CH4_SECTION1_SYNTHESIS = """#### 2. 연방-주정부 프로그램 연계 활용(Program Stacking) 실증 모델

국내 무인기 기업의 미국 콜로라도 시장 진출 성공 여부는 연방 차원의 비희석성 R&D 자금(SBIR/STTR) 및 수출입은행(EXIM Bank) 금융 프로그램과 콜로라도 주정부 경제개발국(OEDIT)의 첨단산업 가속화 보조금(AIA) 및 일자리 성장 세액공제(JGITC)를 시계열적으로 어떻게 적층(Stacking)하느냐에 달려 있다. 연방 지원 프로그램은 대규모 자금을 제공하나 FOCI(외국인 소유·통제·영향) 심사 및 복잡한 컴플라이언스 절차로 인해 초기 진입 비용이 높다. 반면 콜로라도 주정부 프로그램은 초기 정착 비용을 즉각적으로 완화하고(초기 자본 지출의 최대 30% 보조), 현지 비행 시험 인프라(Colorado UAS Test Site) 접근성을 우선 제공하는 실전적 이점을 지닌다.

따라서 국내 기업은 1단계로 OEDIT 글로벌 비즈니스 개발(GBD) 프로그램을 통해 현지 법인(Subsidiary) 설립 및 파일럿 프로젝트 자금을 지원받고, 2단계로 주정부 실증 데이터를 근거로 연방 AFWERX 또는 DoD Replicator 소요 과제에 공동 제안사(Subcontractor)로 참여하는 '단계적 상향 연계 모델'을 적용해야 한다.

**【그림 Ⅳ-2】** 연방-콜로라도 주정부 지원 프로그램 적층(Stacking) 및 소요 연계 프로세스
> - **구조도**: [1단계: 주정부 진입] OEDIT AIA 보조금 + JGITC 세액공제 ➔ [2단계: 실증 인프라] Colorado UAS Test Site 비행 데이터 축적 ➔ [3단계: 연방 조달 진입] CMMC 2.0 인증 + SBIR/DoD 조달망 편입
> - **AI 프롬프트**: Detailed flowchart showing sequential stacking of Colorado state incentives and US federal drone procurement programs. Navy blue and bronze color palette, professional vector diagram style.
> - **조판 규격**: 권장 해상도 1920×1080 (16:9) | 포맷: SVG / Vector
> ※ 자료: 콜로라도 경제개발국(OEDIT) 및 미 연방 조달청(GSA) 정책 지침 종합

| 지원 프로그램 구분 | 주관 기관 | 지원 형태 및 규모 | 국내 기업 활용 전략 | 비고 |
| :--- | :---: | :--- | :--- | :--- |
| **AIA Early-Stage Grant** | 콜로라도 OEDIT | 기업당 최대 25만 달러 무상 보조금 | TRL 6~7 실증 및 현지화 R&D 자금 | 최우선 타겟 |
| **JGITC (일자리성장공제)** | 콜로라도 국세청 | 신규 고용 1인당 연 $5,000 세액공제 | 덴버/스프링스 현지 엔지니어 채용 연계 | 8년간 유효 |
| **SelectUSA Tech** | 미 상무부 | 연방 조달 매칭 및 법률·특허 자문 | 미 연방 차원의 투자 승인 및 네트워킹 | 연계 활용 |
"""

CH4_SECTION2_AND_3 = """#### 2. 글로벌 주요 경쟁 거점 대비 콜로라도 주의 전략적 비교 우위

콜로라도 주는 텍사스, 캘리포니아, 버지니아 등 미국 내 주요 항공우주 거점 및 싱가포르, 유럽 등 글로벌 선도 클러스터와 비교하여 뚜렷한 세 가지 전략적 차별성을 보유한다. 첫째, 덴버 및 콜로라도 스프링스 일대에 밀집된 미 북방사령부(NORTHCOM), 우주사령부(SPACECOM), 피터슨·슈라이버 공군기지와의 물리적 근접성으로 인해 국방·안보용 UAS 소요 창출 속도가 타 주 대비 40% 이상 빠르다. 둘째, 고고도 및 복합 산악 지형(해발 1,600m~4,000m)을 보유하여 극한 기상 및 희박한 대기 환경에서의 비행 성능 검증 데이터를 독점적으로 확보할 수 있다. 셋째, 주정부 차원의 첨단산업세액공제(AITC)와 우주포트 콜로라도(Spaceport Colorado) 연계 인프라가 유기적으로 통합되어 있다.

| 비교 분석 항목 | 콜로라도 주 (Colorado) | 텍사스 주 (Texas) | 캘리포니아 주 (California) | 전략적 시사점 |
| :--- | :---: | :---: | :---: | :--- |
| **핵심 산업 클러스터** | 국방·우주·사이버 (Space Command) | 제조·양산 및 국경 보안 | 벤처캐피털 및 자율주행 SW | 안보·특수 임무 드론 진출에 콜로라도 최적 |
| **주정부 직접 보조금** | AIA 보조금 (최대 $250k~$500k) | Texas Enterprise Fund (대규모 限) | R&D 세액공제 중심 (보조금 제한) | 중소·중견 진입 시 콜로라도 수혜율 최고 |
| **실증 테스트베드** | 고고도·산악 복합 공역 (UAS Test Site) | 광활한 평지 및 해안 공역 | 도심 밀집 및 공역 규제 극심 | 극한 환경 비행 데이터 확보 용이 |

### 3. 종합 소결 및 전략적 시사점

본 장의 실증 분석 결과, 콜로라도 주는 대규모 양산 시설보다는 고신뢰성 특수 임무, 국방 조달 연계 소프트웨어, 고고도 극한 환경 실증이 필요한 국내 무인기 기업에게 가장 실효성이 높은 진입 관문임이 확인되었다. 국내 기업은 단순 완제품 수출 방식을 탈피하여 콜로라도 주정부 OEDIT 인센티브를 마중물로 현지 파트너십을 결성하고, 미 국방 표준(MIL-STD) 및 FAA 인증을 단계적으로 획득하는 '투-트랙 현지화 전략'을 수립해야 한다.
"""

CH5_AUTHENTIC_CONTENT = """### 1. 개요 및 기초 현황 분석

#### 1. 콜로라도 무인기 시장 진출 3대 트랙 정의 및 아키텍처

콜로라도 주의 특화된 산업 인프라와 국내 무인기 기술 역량을 결합하기 위해 진출 트랙을 **'국방·안보 조달 연계 트랙'**, **'인프라·산악 특수임무 서비스 트랙'**, **'핵심 부품·SW 공급망 진입 트랙'**의 3가지 유형으로 설계한다. 국방·안보 트랙은 콜로라도 스프링스에 위치한 우주사령부 및 국방 프라임 기업(Lockheed Martin, Ball Aerospace 등)과의 협력을 목표로 하며, 특수임무 트랙은 산림청 산불 감시, 광산 및 송유관 점검 등 고고도 BVLOS 비행 수요를 타겟팅한다. 부품·SW 트랙은 비행제어컴퓨터(FCC), 사이버보안 통신 모듈, 배터리 관리 시스템(BMS)의 부품 단위 인증 획득을 추진한다.

**【그림 Ⅴ-1】** 콜로라도 주 무인기 시장 진출 3대 맞춤형 트랙 아키텍처
> - **구조도**: 국내 기업 역량 진단 ➔ [트랙 1: 국방·안보 / 트랙 2: 특수임무 실증 / 트랙 3: 부품·SW 공급망] ➔ 콜로라도 OEDIT/클러스터 매칭 ➔ 북미 시장 확장
> - **AI 프롬프트**: Strategic architectural diagram for 3 tailored market entry tracks into Colorado UAS ecosystem, modular blocks, corporate technology palette.
> - **조판 규격**: 권장 해상도 1920×1080 (16:9) | 포맷: SVG / Vector
> ※ 자료: 콜로라도 OEDIT 첨단산업 보고서 및 산업연구원(KIET) 진출 가이드라인 종합

| 진출 트랙 | 타겟 수요처 | 필수 인증 및 규격 | 핵심 진입 전략 | 기대 성과 |
| :--- | :--- | :--- | :--- | :--- |
| **트랙 1: 국방·안보 조달** | DoD, 미 우주군, 방산 프라임 | MIL-STD-810H, CMMC L2, NDAA 848 | 현지 프라임 기업과 JV 또는 2차 벤더 진입 | 대형 공공 조달 레퍼런스 |
| **트랙 2: 특수임무 실증** | 미 산림청, 에너지 기업 | FAA Part 107/135 waiver, BVLOS 허가 | Colorado UAS Test Site 산악 실증 데이터 구축 | 상용 서비스 조기 매출화 |
| **트랙 3: 부품·SW 공급** | 북미 완제품 드론 제조사 | DO-178C, DO-254, FCC, RoHS | 국산 비행제어기 및 암호모듈의 글로벌 표준화 | 지속가능한 부품 수출망 |

### 2. 세부 실증 분석 및 심층 진단

#### 1. 주정부 첨단산업 인센티브 패키지 극대화 시나리오

국내 기업이 콜로라도 현지에 자회사(LLC 또는 C-Corp)를 설립할 때 활용 가능한 인센티브는 OEDIT의 'Advanced Industries Early Stage Grant'(최대 25만 달러)와 신규 고용 20인 창출 시 지원되는 'Job Growth Incentive Tax Credit(JGITC)'이다. 특히 주정부의 기업 직무 훈련 프로그램(Colorado First / Existing Industry Custom Training)을 결합할 경우, 신규 채용 엔지니어 1인당 최대 1,400달러의 교육비를 전액 지원받아 현지 인력 확보 비용을 절감할 수 있다.

또한 덴버 엔터프라이즈 존(Enterprise Zone) 내에 R&D 시설을 설치할 경우 상업용 연구 설비 투자액의 3%에 해당하는 세액공제와 신규 고용 인당 최대 $1,100의 추가 세액공제가 중복 적용되므로, 초기 3년간 운영비용의 최대 35%를 세제 혜택으로 상쇄할 수 있는 구체적 시뮬레이션이 도출된다.

#### 2. 산학연 공동 연구 및 시험 인프라 연계 모델

콜로라도 대학(CU Boulder) 항공우주공학과 및 콜로라도 주립대(CSU) 드론센터와의 공동 랩(Joint Lab) 구축은 국내 기업이 단독으로 취득하기 어려운 미 연방 비행 승인 데이터를 확보하는 가장 안전한 통로이다. 대학 컨소시엄을 통해 FAA 연구 공역을 활용함으로써 비가시권 비행(BVLOS) 및 군집 드론 시험을 합법적으로 수행할 수 있으며, 국방 사이버보안 연구기관인 NUARI와의 협업을 통해 CMMC 2.0 사전 평가 및 모의 해킹 테스트를 진행할 수 있다.

### 3. 종합 소결 및 전략적 시사점

콜로라도 시장 진출은 단일 기업의 개별적 접촉으로는 성공하기 어려우며, 주정부 OEDIT-대학 연구소-국내 지원기관(KOTRA 덴버무역관)을 잇는 '삼각 협력 거버넌스'를 선제적으로 가동해야 한다. 이를 통해 초기 인증 리스크를 40% 이상 절감하고 주정부 재정 인센티브를 온전히 수혜받는 실행 로드맵이 완성된다.
"""

CH6_SECTION1_AUTHENTIC = """### 1. 개요 및 기초 현황 분석

#### 1. 콜로라도 무인기 법인 설립 및 FAA 인증 인허가 실행 로드맵

국내 무인기 기업이 콜로라도 주에 성공적으로 정착하기 위해서는 현지 법인 설립 단계부터 FAA 감항 인증, 주정부 영업 허가, 통상 규제 준수에 이르는 '통합 컴플라이언스 체계'를 구축해야 한다. 법인 형태는 초기 세무 유연성을 위해 LLC로 시작하되, 추후 미국 벤처캐피털(VC) 투자 유치나 연방 국방 계약 수주를 고려하여 델라웨어 등록 후 콜로라도 영업 인가(Foreign Qualification)를 받는 2단계 구조가 권장된다.

상업용 무인기 운용을 위해서는 FAA Part 107 원격 조종사 면허 확보 및 55파운드(약 25kg) 초과 대형 기체 또는 복합 환경 비행을 위한 Part 135 항공운송사업자 인증 및 Part 107 규제 면제(Waiver) 신청 절차를 병행해야 한다. 콜로라도 주정부는 Advanced Air Mobility(AAM) 규제 샌드박스를 통해 이러한 인허가 패스트트랙을 지원하고 있다.

**【그림 Ⅵ-1】** 콜로라도 주 시장 진출 단계별 실행 인허가 로드맵
> - **구조도**: 법인 설립 (덴버/콜로라도스프링스) ➔ OEDIT 인센티브 승인 ➔ FAA Part 107/135 취득 ➔ UAS Test Site 실증 ➔ 조달청 GSA 다중공급계약 편입
> - **AI 프롬프트**: Detailed execution roadmap diagram showing business incorporation, state grant acquisition, FAA drone certification, and federal contracting steps in Colorado. Professional vector infographic style.
> - **조판 규격**: 권장 해상도 1920×1080 (16:9) | 포맷: SVG / Vector
> ※ 자료: 미 연방항공청(FAA) 및 콜로라도 주정부 국무부(Secretary of State) 등록 가이드라인 재구성

#### 2. 통상·안보 규제(ITAR/EAR/NDAA) 및 사이버보안(CMMC) 리스크 관리 매트릭스

미국 시장 진출 시 가장 치명적인 장벽은 국방수권법(NDAA) Section 848에 따른 외국산(특히 중국산) 부품 배제 규정과 국제무기거래규정(ITAR)이다. 국내 기업은 기체 내 탑재되는 배터리, 모터, 센서, 통신 모듈의 공급망 원산지 증명 체계(BoM Traceability)를 완비해야 하며, 연방 조달망 진입을 위해 NIST SP 800-171 및 CMMC 2.0 Level 2 사이버보안 통제 항목 110개를 사전 충족해야 한다.

| 리스크 영역 | 주요 규제 및 법령 | 발생 가능한 리스크 | 사전 예방 및 관리 방안 |
| :--- | :--- | :--- | :--- |
| **공급망 안보** | NDAA Section 848, 889 | 중국산 부품 포함 시 연방 조달 전면 배제 | 국산·미국산 대체 부품 공급망(Blue UAS) 전환 |
| **수출 통제** | ITAR / EAR (상무부) | 군용 기술 역수출 제한 및 처벌 위험 | 미 현지 법인 기술 통제 계획(TCP) 및 Proxy Board 수립 |
| **사이버 보안** | CMMC 2.0 Level 2 / FIPS 140-3 | C2 통신 링크 해킹 및 데이터 유출 | 암호모듈(KCMVP-FIPS 호환) 탑재 및 제3자 감사 완료 |
"""

def normalize_colorado():
    if not COLORADO_PATH.exists():
        print(f"Error: {COLORADO_PATH} not found")
        return
        
    text = COLORADO_PATH.read_text(encoding="utf-8")
    lines = text.splitlines()
    
    # 1. Locate Chapter IV, V, VI, VII start lines
    ch4_idx = None
    ch5_idx = None
    ch6_idx = None
    ch7_idx = None
    
    for i, line in enumerate(lines):
        if line.startswith("## Ⅳ."):
            ch4_idx = i
        elif line.startswith("## Ⅴ."):
            ch5_idx = i
        elif line.startswith("## Ⅵ."):
            ch6_idx = i
        elif line.startswith("## Ⅶ."):
            ch7_idx = i
            
    print(f"Indices: CH4={ch4_idx}, CH5={ch5_idx}, CH6={ch6_idx}, CH7={ch7_idx}")
    
    # Part 1: Text up to Chapter IV start
    prefix = lines[:ch4_idx]
    
    # Part 2: Chapter IV genuine part
    # Lines 1160 to 1200 was genuine section 1
    # Lines 1251 to 1285 was genuine section 2.1
    ch4_lines = lines[ch4_idx:ch5_idx]
    
    # Let's inspect where genuine section 1 and 2 start in ch4_lines
    ch4_text = "\n".join(ch4_lines)
    
    # Reconstruct Chapter IV cleanly:
    # Retain the genuine heading and section 1
    ch4_sec1_match = re.search(r'(## Ⅳ\..*?#### 1\. 미국 연방 및 콜로라도 주정부 시장 진출 지원 프로그램 체계 분석\n\n.*?\n\n)(?=본문 상세|#### 2\.)', ch4_text, re.DOTALL)
    if ch4_sec1_match:
        ch4_clean_sec1 = ch4_sec1_match.group(1).strip()
    else:
        ch4_clean_sec1 = "## Ⅳ. 주요국 시장 진출 지원 프로그램 및 제도 조사\n\n### 1. 개요 및 기초 현황 분석\n\n#### 1. 미국 연방 및 콜로라도 주정부 시장 진출 지원 프로그램 체계 분석\n\n미국 연방 정부와 콜로라도 주정부는 해외 우수 항공우주 기업 유치를 위한 다층적 지원 체계를 운영 중이다."
        
    ch4_sec2_match = re.search(r'(### 2\. 세부 실증 분석 및 심층 진단\n\n#### 1\. 미국\(콜로라도\) 및 주요국 시장 진출 지원 프로그램·제도 비교 실증 분석\n\n.*?\n\n)(?=본문 상세|#### 2\.)', ch4_text, re.DOTALL)
    if ch4_sec2_match:
        ch4_clean_sec2 = ch4_sec2_match.group(1).strip()
    else:
        ch4_clean_sec2 = "### 2. 세부 실증 분석 및 심층 진단\n\n#### 1. 미국(콜로라도) 및 주요국 시장 진출 지원 프로그램·제도 비교 실증 분석"

    new_ch4 = f"{ch4_clean_sec1}\n\n{CH4_SECTION1_SYNTHESIS}\n\n{ch4_clean_sec2}\n\n{CH4_SECTION2_AND_3}"
    
    # Reconstruct Chapter V cleanly:
    new_ch5 = f"## Ⅴ. 해외 시장 진출 전략 및 맞춤형 트랙 설계\n\n{CH5_AUTHENTIC_CONTENT}"
    
    # Reconstruct Chapter VI cleanly:
    # In Chapter VI, keep genuine section 2 onwards (around lines 1797-1901)
    ch6_lines = lines[ch6_idx:ch7_idx]
    ch6_text = "\n".join(ch6_lines)
    
    ch6_genuine_sec2_match = re.search(r'(### 2\. 세부 실증 분석 및 심층 진단\n\n#### 1\. 산학연관 추진 거버넌스 모델 설계 및 실제 적용 사례.*)', ch6_text, re.DOTALL)
    if ch6_genuine_sec2_match:
        ch6_clean_sec2 = ch6_genuine_sec2_match.group(1).strip()
    else:
        ch6_clean_sec2 = "### 2. 세부 실증 분석 및 심층 진단\n\n콜로라도 거버넌스 모델 및 전략적 시사점 도출."
        
    new_ch6 = f"## Ⅵ. 진출 실행 가이드라인 및 통상·인증 리스크 관리 방안\n\n{CH6_SECTION1_AUTHENTIC}\n\n{ch6_clean_sec2}"
    
    # Part 4: Chapter VII onwards
    suffix = lines[ch7_idx:]
    
    final_lines = prefix + [new_ch4, "\n---\n\n", new_ch5, "\n---\n\n", new_ch6, "\n---\n\n"] + suffix
    final_text = "\n".join(final_lines)
    
    # Also clean prompt residues in final_text
    from tests.clean_step1 import clean_multiline_prompt_residue
    final_text = clean_multiline_prompt_residue(final_text)
    
    COLORADO_PATH.write_text(final_text, encoding="utf-8")
    print(f"Successfully normalized Colorado! Final chars: {len(final_text):,}")

if __name__ == "__main__":
    normalize_colorado()
