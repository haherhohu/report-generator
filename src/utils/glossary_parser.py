"""Extraction tools for acronyms, terms, and citations from generated markdown texts."""
from __future__ import annotations

import re

# 자주 등장하는 표준 기술/정책/산업 약어 사전
KNOWN_ACRONYMS: dict[str, tuple[str, str]] = {
    "UAV": ("Unmanned Aerial Vehicle", "무인항공기"),
    "UAS": ("Unmanned Aircraft System", "무인항공시스템"),
    "C2": ("Command and Control", "지휘통제 및 원격제어 통신"),
    "TRL": ("Technology Readiness Level", "기술성숙도 (1~9단계)"),
    "CAGR": ("Compound Annual Growth Rate", "연평균 복합 성장률"),
    "FAA": ("Federal Aviation Administration", "미국 연방항공청"),
    "BVLOS": ("Beyond Visual Line of Sight", "가시권 밖 비행"),
    "GCS": ("Ground Control Station", "지상통제소"),
    "AI": ("Artificial Intelligence", "인공지능"),
    "ML": ("Machine Learning", "머신러닝/기계학습"),
    "R&D": ("Research and Development", "연구개발"),
    "OEM": ("Original Equipment Manufacturer", "주문자 상표 부착 생산"),
    "IP": ("Intellectual Property", "지식재산권/원천특허"),
    "K-UAS": ("Korea Unmanned Aircraft System", "한국형 무인항공시스템"),
    "ICAO": ("International Civil Aviation Organization", "국제민간항공기구"),
    "EASA": ("European Union Aviation Safety Agency", "유럽 항공안전청"),
    "M&A": ("Mergers and Acquisitions", "기업 인수합병"),
    "WBS": ("Work Breakdown Structure", "작업 분류 체계"),
    "API": ("Application Programming Interface", "애플리케이션 프로그래밍 인터페이스"),
    "NTN": ("Non-Terrestrial Network", "비지상 통신 네트워크 (위성통신 연계)"),
    "GEO": ("Geostationary Earth Orbit", "정지궤도 위성"),
    "LEO": ("Low Earth Orbit", "저궤도 위성"),
    "RAMS": ("Reliability, Availability, Maintainability, and Safety", "신뢰도·가용도·정비도·안전성 통합 신뢰성 분석"),
    "UAM": ("Urban Air Mobility", "도심항공교통"),
    "AAM": ("Advanced Air Mobility", "미래항공모빌리티"),
    "eVTOL": ("electric Vertical Take-Off and Landing", "전기 수직이착륙 항공기"),
    "MRO": ("Maintenance, Repair, and Overhaul", "유지·보수·운영 정비 서비스"),
    "SLAM": ("Simultaneous Localization and Mapping", "동시적 위치추정 및 지도작성 기술"),
    "ROS": ("Robot Operating System", "로봇 운영체제"),
    "RAG": ("Retrieval-Augmented Generation", "검색 증강 생성"),
    "LLM": ("Large Language Model", "대형 언어 모델"),
    "GPU": ("Graphics Processing Unit", "그래픽 처리 장치"),
    "NPU": ("Neural Processing Unit", "신경망 처리 장치"),
    "HPC": ("High-Performance Computing", "고성능 컴퓨팅"),
    "SW": ("Software", "소프트웨어"),
    "HW": ("Hardware", "하드웨어"),
    "ICT": ("Information and Communications Technology", "정보통신기술"),
    "IoT": ("Internet of Things", "사물인터넷"),
    "B2B": ("Business-to-Business", "기업 간 거래"),
    "B2G": ("Business-to-Government", "기업-정부 간 공공 조달 거래"),
    "V2X": ("Vehicle-to-Everything", "차량-사물 간 통신 기술"),
    "OTA": ("Over-The-Air", "무선 원격 소프트웨어 업데이트"),
    "SIL": ("Software-in-the-Loop", "소프트웨어 연동 시뮬레이션"),
    "HIL": ("Hardware-in-the-Loop", "하드웨어 연동 시뮬레이션"),
    "FTZ": ("Foreign Trade Zone", "자유무역지대"),
    "UTM": ("Unmanned Aircraft System Traffic Management", "무인기 저고도 교통관리 체계"),
    "DoD": ("Department of Defense", "미국 국방부"),
    "NDAA": ("National Defense Authorization Act", "미국 국방수권법"),
    "AFB": ("Air Force Base", "공군기지"),
    "AFLCMC": ("Air Force Life Cycle Management Center", "미 공군 생애주기 관리센터"),
    "AFRL": ("Air Force Research Laboratory", "미 공군 연구소"),
    "AMMI": ("Advanced Materials and Manufacturing Initiative", "첨단소재 및 제조 이니셔티브"),
    "UTTR": ("Utah Test and Training Range", "유타 테스트 및 훈련 범위"),
    "UAMMI": ("Utah Advanced Materials and Manufacturing Initiative", "유타 첨단소재·제조 이니셔티브"),
    "GOED": ("Governor's Office of Economic Development", "유타 주지사 경제개발국"),
    "DIU": ("Defense Innovation Unit", "미 국방혁신단"),
    "AFWERX": ("Air Force Innovation Hub", "미 공군 혁신 허브"),
    "MBSE": ("Model-Based Systems Engineering", "모델 기반 시스템 공학"),
    "ITAR": ("International Traffic in Arms Regulations", "국제무기거래규정"),
    "EAR": ("Export Administration Regulations", "미국 수출관리규정"),
    "FMS": ("Foreign Military Sales", "대외군사판매"),
    "SBIR": ("Small Business Innovation Research", "중소기업 혁신 연구 프로그램"),
    "STTR": ("Small Business Technology Transfer", "중소기업 기술이전 프로그램"),
    "KURA": ("Korea-Utah UAS RAMS Alliance", "한-유타 무인기 신뢰성 실증 얼라이언스"),
    "NIST": ("National Institute of Standards and Technology", "미국 국립표준기술원"),
    "NATO": ("North Atlantic Treaty Organization", "북대서양조약기구"),
    "NASA": ("National Aeronautics and Space Administration", "미국 항공우주국"),
    "MARL": ("Multi-Agent Reinforcement Learning", "다중 에이전트 강화학습"),
    "PHM": ("Prognostics and Health Management", "건전성 예측 및 관리"),
    "XAI": ("Explainable Artificial Intelligence", "설명 가능한 인공지능"),
    "GBSD": ("Ground Based Strategic Deterrent", "지상 기반 전략 억제체계 (센티넬)"),
    "OO-ALC": ("Ogden Air Logistics Complex", "오그던 항공군수복합단지"),
    "AC": ("Advisory Circular", "FAA 자문원형 (항공 표준 지침서)"),
    "ACO": ("Aircraft Certification Office", "FAA 항공기 인증 사무소"),
    "ADD": ("Agency for Defense Development", "국방과학연구소"),
    "AIRC": ("Acquisition Innovation Research Center", "국방 획득 혁신 연구센터"),
    "AML": ("Advanced Manufacturing Logistics / Tax Credit", "첨단 제조 물류 및 세액공제"),
    "ASRL": ("Autonomous Systems Research Laboratory", "자율시스템 연구소"),
    "ATLA": ("Acquisition, Technology & Logistics Agency", "일본 방위장비청"),
    "ATO": ("Authority to Operate", "연방 정보시스템 운용 인가 권한"),
    "BASA": ("Bilateral Aviation Safety Agreement", "양자 간 항공안전협정"),
    "BEI": ("Business Expansion and Incentive", "비즈니스 확장 인센티브"),
    "BMS": ("Battery Management System", "배터리 관리 시스템"),
    "BRC": ("Business Ready Community", "비즈니스 레디 커뮤니티 지원 프로그램"),
    "BYU": ("Brigham Young University", "브리검영 대학교"),
    "C3PAO": ("Certified Third-Party Assessment Organization", "CMMC 제3자 공인평가기관"),
    "CA": ("California", "미국 캘리포니아 주"),
    "CAAI": ("Civil Aviation Authority of Israel", "이스라엘 민간항공청"),
    "CAPEX": ("Capital Expenditures", "자본적 지출 및 설비투자비용"),
    "CCATS": ("Commodity Classification Automated Tracking System", "미 상무부 품목분류 자동추적시스템"),
    "CEO": ("Chief Executive Officer", "최고경영자"),
    "CFR": ("Code of Federal Regulations", "미국 연방규정집"),
    "CIR": ("Cyber Incident Response", "사이버 침해사고 대응"),
    "CMMC": ("Cybersecurity Maturity Model Certification", "미 국방부 사이버보안 성숙도 모델 인증"),
    "CO": ("Colorado", "미국 콜로라도 주"),
    "COA": ("Certificate of Waiver or Authorization", "FAA 비행 승인 및 특별인가증"),
    "CONOPS": ("Concept of Operations", "작전 운용 개념"),
    "CPARS": ("Contractor Performance Assessment Reporting System", "미 연방 계약자 성과평가 시스템"),
    "CPS": ("Cyber-Physical Systems", "사이버-물리 시스템"),
    "CRADA": ("Cooperative Research and Development Agreement", "민군 공동 연구개발 협약"),
    "CVE": ("Common Vulnerabilities and Exposures", "공통 보안 취약점 식별자"),
    "DAA": ("Detect and Avoid", "충돌 감지 및 회피 기술"),
    "DAL": ("Development Assurance Level", "항공 소프트웨어 개발 보증 등급"),
    "DFARS": ("Defense Federal Acquisition Regulation Supplement", "미 국방부 연방조달규정 보충판"),
    "DGA": ("Direction Générale de l'Armement", "프랑스 병기총국"),
    "DLA": ("Defense Logistics Agency", "미 국방군수국"),
    "DO-178C": ("Software Considerations in Airborne Systems and Equipment Certification", "항공기 탑재 소프트웨어 안전성 인증 기준"),
    "DOA": ("Design Organization Approval", "항공기 설계 조직 승인"),
    "DOE": ("Department of Energy", "미국 에너지부"),
    "DPA": ("Defense Production Act", "미국 국방물자생산법"),
    "DTIC": ("Defense Technical Information Center", "미 국방기술정보센터"),
    "DUTR": ("Dugway Proving Ground UAS Test Range", "유타 더그웨이 시험장"),
    "ECO": ("Engineering Change Order", "설계 변경 지시서"),
    "EDA": ("Economic Development Administration", "미국 경제개발청"),
    "EDC": ("Economic Development Corporation", "경제개발공사"),
    "EDCUT": ("Economic Development Corporation of Utah", "유타 경제개발공사"),
    "EDTC": ("Economic Development Tax Credit", "유타 경제개발 세액공제"),
    "EDTIF": ("Economic Development Tax Increment Financing", "유타 주 조세감면 인센티브 금융 지원제도"),
    "EEN": ("Enterprise Europe Network", "유럽 기업 네트워크"),
    "EMC": ("Electromagnetic Compatibility", "전자파 적합성"),
    "ESG": ("Environmental, Social, and Governance", "환경·사회·지배구조"),
    "ESOP": ("Employee Stock Ownership Plan", "우리사주제도"),
    "EU": ("European Union", "유럽연합"),
    "EW": ("Electronic Warfare", "전자전"),
    "EWS": ("Early Warning System", "조기경보체계"),
    "FAL": ("Final Assembly Line", "최종 조립 라인"),
    "FCC": ("Federal Communications Commission", "미국 연방통신위원회"),
    "FCL": ("Facility Security Clearance", "시설 보안인가 등급"),
    "FDI": ("Foreign Direct Investment", "외국인 직접투자"),
    "FDIR": ("Fault Detection, Isolation, and Recovery", "고장 감지, 격리 및 복구 체계"),
    "FL": ("Florida", "미국 플로리다 주"),
    "FMU": ("Flight Management Unit", "비행 관리 장치"),
    "FPDS": ("Federal Procurement Data System", "미국 연방 조달 데이터 시스템"),
    "FSDO": ("Flight Standards District Office", "FAA 지역 비행표준사무소"),
    "G2G": ("Government-to-Government", "정부 간 협력 및 정책 교류"),
    "GCO": ("Global Compliance Office", "글로벌 규제준수 사무국"),
    "GRDP": ("Gross Regional Domestic Product", "지역내 총생산"),
    "GVC": ("Global Value Chain", "글로벌 가치사슬"),
    "HAPS": ("High-Altitude Platform Station", "성층권 장기체공 무인 플랫폼"),
    "IAF": ("Industrial Assistance Fund", "유타 주 산업지원기금"),
    "IIA": ("Israel Innovation Authority", "이스라엘 혁신청"),
    "ILS": ("Integrated Logistics Support", "종합 군수지원 체계"),
    "IMOD": ("Israel Ministry of Defense", "이스라엘 국방부"),
    "IPP": ("Integration Pilot Program", "FAA 무인기 통합 시범사업"),
    "IRA": ("Inflation Reduction Act", "미국 인플레이션 감축법"),
    "JCIDS": ("Joint Capabilities Integration and Development System", "합동 역량 통합 및 개발 체계"),
    "JV": ("Joint Venture", "합작투자법인"),
    "KAI": ("Korea Aerospace Industries", "한국항공우주산업"),
    "KAIA": ("Korea Association for Aerospace Industry", "한국항공우주산업진흥협회"),
    "KAIAA": ("Korea Aerospace Industries Association", "한국항공우주산업진흥협회"),
    "KAIST": ("Korea Advanced Institute of Science and Technology", "한국과학기술원"),
    "KARI": ("Korea Aerospace Research Institute", "한국항공우주연구원"),
    "KARUS": ("Korea Airworthiness Requirements for Unmanned Systems", "한국형 무인기 감항인증 기준"),
    "KATS": ("Korean Agency for Technology and Standards", "국가기술표준원"),
    "KOLAS": ("Korea Laboratory Accreditation Scheme", "한국인정기구"),
    "KOTRA": ("Korea Trade-Investment Promotion Agency", "대한무역투자진흥공사"),
    "KPI": ("Key Performance Indicator", "핵심 성과 지표"),
    "KRIT": ("Korea Research Institute for Defense Technology Planning and Advancement", "국방기술진흥연구소"),
    "KSF": ("Key Success Factors", "핵심 성공 요인"),
    "KTL": ("Korea Testing Laboratory", "한국산업기술시험원"),
    "LCC": ("Life Cycle Cost", "수명주기비용"),
    "LOI": ("Letter of Intent", "투자의향서 및 구매의향서"),
    "LQ": ("Location Quotient", "입지계수 (산업 집적도 지표)"),
    "MAE": ("Mechanical and Aerospace Engineering", "기계항공공학부"),
    "MIB": ("Military Industrial Base", "군수 방산기반 체계"),
    "MIL-STD": ("Military Standard", "미국 군용 표준 규격"),
    "MLSA": ("Mutual Logistics Support Agreement", "상호군수지원협정"),
    "MOSA": ("Modular Open Systems Approach", "모듈러 개방형 시스템 접근법"),
    "MOU": ("Memorandum of Understanding", "업무협약 및 양해각서"),
    "MR": ("Mission Reliability", "임무 신뢰도"),
    "MRA": ("Mutual Recognition Agreement", "상호인정협정"),
    "MSA": ("Middle Tier of Acquisition", "미 국방부 신속 중기 획득 경로"),
    "MTBF": ("Mean Time Between Failures", "평균 고장 간격 시간"),
    "MTTR": ("Mean Time to Repair", "평균 수리 소요 시간"),
    "ND": ("North Dakota", "미국 노스다코타 주"),
    "NDSL": ("National Digital Science Library", "국가과학기술정보서비스(NDSL) 학술 연구 데이터베이스"),
    "NIAS": ("Nevada Institute for Autonomous Systems", "네바다 자율시스템 연구소"),
    "NORAD": ("North American Aerospace Defense Command", "북미 항공우주방위사령부"),
    "NPUAS": ("Northern Plains UAS Test Site", "노스다코타 북부 평원 UAS 시험장"),
    "NPV": ("Net Present Value", "순현재가치"),
    "NSF": ("National Science Foundation", "미국 국립과학재단"),
    "NV": ("Nevada", "미국 네바다 주"),
    "NVIDIA": ("NVIDIA Corporation", "엔비디아 (글로벌 AI 컴퓨팅 기업)"),
    "NY": ("New York", "미국 뉴욕 주"),
    "OC": ("Operations Certificate", "항공 운항증명"),
    "ODA": ("Organization Designation Authorization", "조직 위임 인증 권한 (FAA 인정)"),
    "OG-ALC": ("Ogden Air Logistics Complex", "오그던 항공군수복합단지 (힐 공군기지)"),
    "OT": ("Operational Testing", "군 운용 시험평가"),
    "PAC-3": ("Patriot Advanced Capability-3", "패트리어트 지대공 미사일 체계"),
    "PBI": ("Performance-Based Incentive", "성과 기반 인센티브"),
    "PBL": ("Performance-Based Logistics", "성과기반 군수지원"),
    "PC": ("Production Certificate", "FAA 제작증명"),
    "PE": ("Professional Engineer", "공인 전문 엔지니어 및 기술사"),
    "PESCO": ("Permanent Structured Cooperation", "유럽연합 영구구조적협력"),
    "POA": ("Production Organization Approval", "항공기 제작 조직 승인"),
    "PTAC": ("Procurement Technical Assistance Center", "미 정부조달 기술지원센터"),
    "QML": ("Qualified Manufacturers List", "미 국방부 적격 제조업체 목록"),
    "QMS": ("Quality Management System", "항공우주 품질경영시스템 (AS9100)"),
    "RACI": ("Responsible, Accountable, Consulted, and Informed", "업무 역할 및 책임 분담 매트릭스"),
    "RMF": ("Risk Management Framework", "미 연방 위험관리프레임워크 (NIST SP 800-37)"),
    "ROC": ("Required Operational Capability", "작전 운용 성능 요구도"),
    "ROI": ("Return on Investment", "투자 대비 수익률"),
    "SATCOM": ("Satellite Communications", "위성통신"),
    "SCA": ("Supply Chain Assessment", "공급망 보안성 평가"),
    "SDD": ("Software-Defined Drone", "소프트웨어 정의 드론"),
    "SDL": ("Space Dynamics Laboratory", "유타 주립대 우주역학연구소"),
    "SDU": ("Software-Defined UAS", "소프트웨어 정의 무인기"),
    "SDV": ("Software-Defined Vehicle", "소프트웨어 정의 모빌리티"),
    "SHORAD": ("Short-Range Air Defense", "단거리 대공방어체계"),
    "SI": ("Strategic Investor", "전략적 투자자"),
    "SLC": ("Salt Lake City", "솔트레이크시티 (유타 주도)"),
    "SMS": ("Safety Management System", "항공 안전관리시스템"),
    "SOC": ("Security Operations Center", "보안관제센터"),
    "SOCOM": ("United States Special Operations Command", "미국 특수작전사령부"),
    "SQA": ("Software Quality Assurance", "소프트웨어 품질보증"),
    "SSA": ("System Safety Assessment", "시스템 안전성 평가"),
    "STRIDE": ("Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege", "마이크로소프트 표준 위협 모델링 기법"),
    "TAM": ("Total Addressable Market", "전체 시장 규모"),
    "TC": ("Type Certificate", "FAA 형식증명"),
    "TDP": ("Technical Data Package", "기술 자료 패키지"),
    "TEC": ("Technical Exchange Conference", "기술 교류 콘퍼런스"),
    "TF": ("Task Force", "태스크포스 (전담 실무추진단)"),
    "TIF": ("Tax Increment Financing", "조세감면 연계 금융지원"),
    "TS": ("Test Site / Transportation Security", "비행시험장 또는 교통안전"),
    "TTO": ("Technology Transfer Office", "대학 및 연구소 기술이전센터"),
    "TVC": ("Technology Venture Commercialization", "유타대 기술벤처상용화센터"),
    "TX": ("Texas", "미국 텍사스 주"),
    "UAA": ("Utah Aerospace Association", "유타 항공우주협회"),
    "UAC": ("Utah Aeronautics Commission", "유타 항공위원회"),
    "UAVTB": ("Unmanned Aerial Vehicle Test Bed", "유타 무인기 테스트베드 실증단지"),
    "UDI": ("Utah Defense Initiative", "유타 방위산업 육성 이니셔티브"),
    "UDIA": ("Utah Defense Industry Association", "유타 국방산업협회"),
    "UDIH": ("Utah Defense Innovation Hub", "유타 국방혁신허브"),
    "UDOT": ("Utah Department of Transportation", "유타 주 교통국"),
    "UED": ("Utah Economic Development", "유타 주 경제개발국 (GOED)"),
    "UIA": ("Utah Industry Association", "유타 주 산업협회"),
    "UQ": ("Uncertainty Quantification", "불확실성 정량화 기법"),
    "US": ("United States", "미합중국 (미국)"),
    "USC": ("Utah Space Consortium", "유타 우주 컨소시엄"),
    "USS": ("UAS Service Supplier", "저고도 무인기 교통관리 서비스 제공자"),
    "USTAR": ("Utah Science Technology and Research Initiative", "유타 과학기술연구 이니셔티브"),
    "USU": ("Utah State University", "유타 주립대학교"),
    "UT": ("State of Utah", "미국 유타 주"),
    "UTA": ("Utah Transit Authority / Test Area", "유타 교통국 또는 시험구역"),
    "UTAG": ("Utah Technology Alliance Group", "유타 기술 얼라이언스 그룹"),
    "UTNG": ("Utah National Guard", "유타 주방위군"),
    "UUAS": ("Utah UAS Test Site", "유타 주 무인항공시스템 시험장"),
    "UUSU": ("Utah State University", "유타 주립대학교"),
    "VA": ("Virginia", "미국 버지니아 주"),
    "VC": ("Venture Capital", "벤처 캐피털"),
    "VLOS": ("Visual Line of Sight", "가시권 내 비행"),
    "WAIVER": ("Part 107 Operational Waiver", "FAA 규정 적용 면제 승인"),
}


def extract_acronyms_from_markdown(text: str) -> list[dict[str, str]]:
    """본문에서 2글자 이상의 영문 약어(Acronym)를 감지하고 영문 원어 및 한글 정의 목록을 구성."""
    if not text:
        return []

    detected_eng: dict[str, str] = {}
    detected_kor: dict[str, str] = {}

    # 1-A. 한글(영문원어, ACRONYM) 패턴 (예: 도심항공교통(Urban Air Mobility, UAM))
    kor_eng_acr = re.compile(r"([가-힣\s]{2,30})\s*\(([A-Za-z\s,\-]+?),\s*([A-Z][A-Z0-9]{1,9}(?:-[A-Z0-9]+)?)\)")
    for m in kor_eng_acr.finditer(text):
        kor_term = m.group(1).strip()
        eng_term = m.group(2).strip()
        acronym = m.group(3).strip()
        if len(eng_term) < 60:
            detected_eng[acronym] = eng_term
            detected_kor[acronym] = kor_term

    # 1-B. 영문원어(ACRONYM) 패턴 (예: Urban Air Mobility (UAM), Command and Control (C2))
    eng_paren = re.compile(r"\b([A-Za-z][A-Za-z\s,\-]{2,50})\s*\(([A-Z][A-Z0-9]{1,9}(?:-[A-Z0-9]+)?)\)")
    for m in eng_paren.finditer(text):
        eng_term = m.group(1).strip()
        acronym = m.group(2).strip()
        if acronym not in detected_eng and len(eng_term) < 60:
            detected_eng[acronym] = eng_term

    # 1-C. 한글(ACRONYM) 패턴 (예: 도심항공교통(UAM), 인공지능(AI))
    kor_paren = re.compile(r"([가-힣]{2,30})\s*\(([A-Z][A-Z0-9]{1,9}(?:-[A-Z0-9]+)?)\)")
    for m in kor_paren.finditer(text):
        kor_term = m.group(1).strip()
        acronym = m.group(2).strip()
        if acronym not in detected_kor:
            detected_kor[acronym] = kor_term

    # 1-D. ACRONYM(영문원어) 패턴 (예: UAM(Urban Air Mobility))
    acr_eng_paren = re.compile(r"\b([A-Z][A-Z0-9]{1,9}(?:-[A-Z0-9]+)?)\s*\(([A-Za-z][A-Za-z\s,\-]{2,50})\)")
    for m in acr_eng_paren.finditer(text):
        acronym = m.group(1).strip()
        eng_term = m.group(2).strip()
        if acronym not in detected_eng:
            detected_eng[acronym] = eng_term

    # 2. 대문자 시작 약어 단어 탐색 (예: UAV, C2, TRL, CAGR, RAMS)
    token_pattern = re.compile(r"\b([A-Z][A-Z0-9]{1,9}(?:-[A-Z0-9]+)?)\b")
    found_acronyms = set(token_pattern.findall(text))

    results: list[dict[str, str]] = []
    ignored_words = {
        "THE", "AND", "FOR", "WITH", "FROM", "PAGE", "NOTE", "STEP", "CASE", "PART",
        "HTML", "JSON", "HTTP", "HTTPS", "SECTION", "TABLE", "FIGURE", "TRUE", "FALSE"
    }

    for acr in sorted(found_acronyms):
        if acr in ignored_words or len(acr) < 2:
            continue

        if acr in KNOWN_ACRONYMS:
            full_eng, def_kor = KNOWN_ACRONYMS[acr]
            results.append({
                "acronym": acr,
                "full_term": full_eng,
                "definition": detected_kor.get(acr, def_kor),
            })
        elif acr in detected_eng or acr in detected_kor:
            full_term = detected_eng.get(acr, "-")
            kor_def = detected_kor.get(acr, "")
            definition = f"{kor_def} (본문 기술 용어)" if kor_def else f"{acr} 관련 핵심 기술 및 실증 규격"
            results.append({
                "acronym": acr,
                "full_term": full_term,
                "definition": definition,
            })

    return results


def extract_in_text_citations(text: str) -> list[str]:
    """본문에서 [1], [2] 인용 부호 및 '※ 자료: ...' 출처 표기를 수집."""
    if not text:
        return []

    citations = []
    # 1. ※ 자료: ... 패턴
    source_pattern = re.compile(r"※\s*자료\s*:\s*(.+?)(?:\n|$)", re.MULTILINE)
    for m in source_pattern.finditer(text):
        src = m.group(1).strip()
        if src and src not in citations:
            citations.append(src)

    # 2. 학술 인용 부호 [1], [2] 뒤에 붙은 각주 패턴
    footnote_pattern = re.compile(r"\[\^?(\d+)\]\s*(.+?)(?:\n|$)", re.MULTILINE)
    for m in footnote_pattern.finditer(text):
        fn = f"[{m.group(1)}] {m.group(2).strip()}"
        if fn not in citations:
            citations.append(fn)

    return citations
