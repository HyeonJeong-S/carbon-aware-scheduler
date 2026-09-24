"""
apply_stage11.py — E1 압축 1차: 6장(검증) 우선순위 배치.
작성: 2026-09-21, carbon-aware-scheduler-4d(원고 트랙). 실행은 be가 한다.

be 승인 조건 반영:
  ① 불가침(확정 수치·수식·증명·기여문·인용 장치(2·4장)·새 표5·6·그림 블록) 안 건드림.
  ② 문단 통삭제 우선 — 이번 배치는 전부 whole-paragraph 삭제 또는 순수 숫자
     치환이고, 문장 단위 수술은 하나도 없다.
  ③ stage 단위 분리 — 이번 stage11은 6장 중 가장 확실한 후보 2건만 처리
     (메모 1건 + 중복 인용 1건). 6장 나머지 후보(§6.1 실험설정 서술, §6.4
     되돌리기 절차 상술 등)는 다음 배치로 미룬다 — 한 번에 너무 많이 건드려
     앵커가 흔들리는 걸 피하려는 것.
  ④ 삭제 근거를 문단 번호로 명시 — 아래 DELETE_JUSTIFICATION 참고.

DELETE_JUSTIFICATION = {
    "4367E322(문단593)": "내부 메모 — 논문 본문이 아님. 근거 문단 불필요.",
    "55D2AA8A(문단704)": "§4.4 문단311과 동일한 Sukprasert 캘리포니아/버지니아 예외 인용(같은 출처·같은 원문 2건 재인용). 704 고유의 연결 관찰(캘리포니아가 시간이동 수혜지이자 용량제약 대상지로 일치)도 §7 문단813이 \"즉 시간 이동이 값어치를 만드는 리전과 용량 제약이 그 값어치를 가로막는 리전이 일치한다\"로 이미 더 명시적으로 말한다 — 정보 손실 없음.",
}

부수 수정(압축과 무관, stage10 그렙 사각지대에서 발견한 잔존 구식 수치 2건):
  문단813: 77.7% -> 91.38%(§6.4 19~21시 집중도, stage9에서 이미 확정된 값과
  같은 수치인데 이 문단만 안 바뀌어 있었음). 문단817: 92배 -> 264.0배(stage10
  E6000013과 같은 수치, 결론의 향후과제 문단만 안 바뀌어 있었음).
"""
import sys, os, shutil, zipfile, datetime, argparse, re
import xml.etree.ElementTree as ET

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOCX = os.path.join(REPO, "paper", "CAST.docx")
VERSIONS_DIR = os.path.join(REPO, "paper", "versions")

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

DELETE_BLOCK_1 = '<w:p w14:paraId="4367E322" w14:textId="77777777" w:rsidR="004A6DA0" w:rsidRDefault="00000000"><w:pPr><w:rPr><w:color w:val="1155CC"/><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr></w:pPr><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:t>(</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:t>이</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:t xml:space="preserve"> </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:t>문단은</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:t xml:space="preserve"> </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:t>우리</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:t xml:space="preserve"> </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:t>약점을</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:t xml:space="preserve"> </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:t>우리가</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:t xml:space="preserve"> </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:t>먼저</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:t xml:space="preserve"> </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:t>말하는</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:t xml:space="preserve"> </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:t>자리임</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:t xml:space="preserve">. </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:t>심사에서</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:t xml:space="preserve"> </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:t>반드시</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:t xml:space="preserve"> </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:t>나올</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:t xml:space="preserve"> </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:t>질문이라</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:t xml:space="preserve"> </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:t>숨기지</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:t xml:space="preserve"> </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:t>말</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:t xml:space="preserve"> </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:t>것</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:t>)</w:t></w:r></w:p><w:p w14:paraId="03816D8A" w14:textId="77777777" w:rsidR="004A6DA0" w:rsidRDefault="004A6DA0"/>'
DUP_704 = '<w:p w14:paraId="55D2AA8A" w14:textId="77777777" w:rsidR="004D20D1" w:rsidRDefault="00000000"><w:r><w:t>선행</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>연구는</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>공간</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>이동의</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>이득이</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>낮음에도</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>시간</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>변동이</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>커서</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>순</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>절감이</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>유의미한</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>예외로</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>캘리포니아와</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>버지니아를</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>지목하였다</w:t></w:r><w:r><w:t xml:space="preserve">. https://doi.org/10.1145/3627703.3650079 — </w:t></w:r><w:r><w:t>원문</w:t></w:r><w:r><w:t xml:space="preserve">: "there are some exceptions where regions have low spatial gains and high temporal gains and yet result in relatively high net carbon reductions, such as California (US-CA) and Virginia (US-VA)" </w:t></w:r><w:r><w:t>본</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>연구에서</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>시간</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>이동이</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>값어치를</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>만드는</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>리전과</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>용량</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>제약이</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>그것을</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>가로막는</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>리전이</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>모두</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>캘리포니아로</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>일치한다</w:t></w:r><w:r><w:t xml:space="preserve">. </w:t></w:r><w:r><w:t>같은</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>연구는</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>자신의</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>시간</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>이동</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>결과가</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>어떤</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>조건에</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>의존하는지도</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>밝혔다</w:t></w:r><w:r><w:t xml:space="preserve">. https://doi.org/10.1145/3627703.3650079 — </w:t></w:r><w:r><w:t>원문</w:t></w:r><w:r><w:t xml:space="preserve">: "For real cloud workloads, the carbon reductions from temporal shifting are limited to 112 g·CO2eq, and depend heavily upon factors like long job lengths, substantial slack, absence of resource constraints, and access to future knowledge of carbon-intensity." </w:t></w:r><w:r><w:t>본</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>절이</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>측정한</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>것은</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>이</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>가운데</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>자원</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>제약의</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>부재라는</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>조건이</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>성립하지</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>않을</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>때의</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>결과다</w:t></w:r><w:r><w:t>.</w:t></w:r></w:p>'
P813_OLD_FRAG = '<w:p w14:paraId="4BE86990" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/></w:pPr><w:r><w:t>본</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>연구의</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>주된</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>발견은</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>총계가</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>아니라</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>그</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>분포에</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>있다</w:t></w:r><w:r><w:t xml:space="preserve">. </w:t></w:r><w:r><w:t>시간</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>이동이</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>만든</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>절감의</w:t></w:r><w:r><w:t xml:space="preserve"> 71.9%</w:t></w:r><w:r><w:t>가</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>캘리포니아</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>한</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>리전에서</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>발생하며</w:t></w:r><w:r><w:t xml:space="preserve">, </w:t></w:r><w:r><w:t>용량</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>초과가</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>가장</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>심한</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>리전도</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>캘리포니아다</w:t></w:r><w:r><w:t xml:space="preserve">. </w:t></w:r><w:r><w:t>캘리포니아에서</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>상한을</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>초과한</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>슬롯의</w:t></w:r><w:r><w:t xml:space="preserve"> 77.7%</w:t></w:r><w:r><w:t>는</w:t></w:r><w:r><w:t xml:space="preserve"> 19</w:t></w:r><w:r><w:t>시부터</w:t></w:r><w:r><w:t xml:space="preserve"> 21</w:t></w:r><w:r><w:t>시까지</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>세</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>시간에</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>몰린다</w:t></w:r><w:r><w:t xml:space="preserve">. </w:t></w:r><w:r><w:t>반면</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>탄소집약도가</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>종일</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>평탄한</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>프랑스는</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>배정</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>물량이</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>가장</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>많음에도</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>시간</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>이동</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>절감</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>기여가</w:t></w:r><w:r><w:t xml:space="preserve"> 2.3%</w:t></w:r><w:r><w:t>에</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>그치고</w:t></w:r><w:r><w:t xml:space="preserve">, </w:t></w:r><w:r><w:t>되돌려도</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>잃는</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>것이</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>거의</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>없다</w:t></w:r><w:r><w:t xml:space="preserve">. </w:t></w:r><w:r><w:t>즉</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>시간</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>이동이</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>값어치를</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>만드는</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>리전과</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>용량</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>제약이</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>그</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>값어치를</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>가로막는</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>리전이</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>일치한다</w:t></w:r><w:r><w:t xml:space="preserve">. </w:t></w:r><w:r><w:t>선행</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>연구가</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>시간</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>이동이</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>실질적으로</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>기여하는</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>예외로</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>이름을</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>붙인</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>리전이</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>바로</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>캘리포니아였다는</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>점에서</w:t></w:r><w:r><w:t xml:space="preserve">, </w:t></w:r><w:r><w:t>본</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>연구는</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>그</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>예외가</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>발생하는</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>메커니즘과</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>그것이</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>용량에</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>의해</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>어떻게</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>제약되는지를</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>실측한</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>것이</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>된다</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/></w:rPr><w:t xml:space="preserve">. </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t xml:space="preserve">https://doi.org/10.1145/3627703.3650079 — </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>원문</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>: "there are some exceptions where regions have low spatial gains and high temporal gains and yet result in relatively high net carbon reductions, such as California (US-CA) and Virginia (US-VA)"</w:t></w:r></w:p>'
P813_NEW_FRAG = '<w:p w14:paraId="4BE86990" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/></w:pPr><w:r><w:t>본</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>연구의</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>주된</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>발견은</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>총계가</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>아니라</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>그</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>분포에</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>있다</w:t></w:r><w:r><w:t xml:space="preserve">. </w:t></w:r><w:r><w:t>시간</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>이동이</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>만든</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>절감의</w:t></w:r><w:r><w:t xml:space="preserve"> 71.9%</w:t></w:r><w:r><w:t>가</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>캘리포니아</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>한</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>리전에서</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>발생하며</w:t></w:r><w:r><w:t xml:space="preserve">, </w:t></w:r><w:r><w:t>용량</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>초과가</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>가장</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>심한</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>리전도</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>캘리포니아다</w:t></w:r><w:r><w:t xml:space="preserve">. </w:t></w:r><w:r><w:t>캘리포니아에서</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>상한을</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>초과한</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>슬롯의</w:t></w:r><w:r><w:t xml:space="preserve"> 91.38%</w:t></w:r><w:r><w:t>는</w:t></w:r><w:r><w:t xml:space="preserve"> 19</w:t></w:r><w:r><w:t>시부터</w:t></w:r><w:r><w:t xml:space="preserve"> 21</w:t></w:r><w:r><w:t>시까지</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>세</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>시간에</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>몰린다</w:t></w:r><w:r><w:t xml:space="preserve">. </w:t></w:r><w:r><w:t>반면</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>탄소집약도가</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>종일</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>평탄한</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>프랑스는</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>배정</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>물량이</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>가장</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>많음에도</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>시간</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>이동</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>절감</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>기여가</w:t></w:r><w:r><w:t xml:space="preserve"> 2.3%</w:t></w:r><w:r><w:t>에</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>그치고</w:t></w:r><w:r><w:t xml:space="preserve">, </w:t></w:r><w:r><w:t>되돌려도</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>잃는</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>것이</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>거의</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>없다</w:t></w:r><w:r><w:t xml:space="preserve">. </w:t></w:r><w:r><w:t>즉</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>시간</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>이동이</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>값어치를</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>만드는</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>리전과</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>용량</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>제약이</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>그</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>값어치를</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>가로막는</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>리전이</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>일치한다</w:t></w:r><w:r><w:t xml:space="preserve">. </w:t></w:r><w:r><w:t>선행</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>연구가</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>시간</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>이동이</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>실질적으로</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>기여하는</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>예외로</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>이름을</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>붙인</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>리전이</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>바로</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>캘리포니아였다는</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>점에서</w:t></w:r><w:r><w:t xml:space="preserve">, </w:t></w:r><w:r><w:t>본</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>연구는</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>그</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>예외가</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>발생하는</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>메커니즘과</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>그것이</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>용량에</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>의해</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>어떻게</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>제약되는지를</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>실측한</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>것이</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>된다</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/></w:rPr><w:t xml:space="preserve">. </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t xml:space="preserve">https://doi.org/10.1145/3627703.3650079 — </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>원문</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>: "there are some exceptions where regions have low spatial gains and high temporal gains and yet result in relatively high net carbon reductions, such as California (US-CA) and Virginia (US-VA)"</w:t></w:r></w:p>'
P817_OLD_FRAG = '<w:p w14:paraId="65F361F1" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/></w:pPr><w:r><w:t xml:space="preserve">향후 과제는 넷이다. 첫째, 실제 기상 예보 API 연동으로 세 리전의 예보 누출을 제거하는 것이다. 둘째, 24시간을 넘는 예측 지평을 시험할 수 있도록 원자료를 확장하는 것이다. 셋째, 수요 증가에 맞춘 용량 산정이다 — 작업량이 2배로 늘면 본 알고리즘에서도 용량 위반 배정이 92배로 폭증하므로, 고정 상한이 아니라 수요에 비례해 조정되는 용량 모델이 필요하다. 넷째, 실제 클러스터 배포를 통한 검증이다.</w:t></w:r></w:p>'
P817_NEW_FRAG = '<w:p w14:paraId="65F361F1" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/></w:pPr><w:r><w:t xml:space="preserve">향후 과제는 넷이다. 첫째, 실제 기상 예보 API 연동으로 세 리전의 예보 누출을 제거하는 것이다. 둘째, 24시간을 넘는 예측 지평을 시험할 수 있도록 원자료를 확장하는 것이다. 셋째, 수요 증가에 맞춘 용량 산정이다 — 작업량이 2배로 늘면 본 알고리즘에서도 용량 위반 배정이 264.0배로 폭증하므로, 고정 상한이 아니라 수요에 비례해 조정되는 용량 모델이 필요하다. 넷째, 실제 클러스터 배포를 통한 검증이다.</w:t></w:r></w:p>'

DELETIONS = [DELETE_BLOCK_1, DUP_704]  # -> 빈 문자열로 치환
NUM_FIXES = [(P813_OLD_FRAG, P813_NEW_FRAG), (P817_OLD_FRAG, P817_NEW_FRAG)]

EXPECTED_DELETED = {'4367E322', '03816D8A', '55D2AA8A'}
EXPECTED_INSERTED = set()
EXPECTED_MODIFIED = {'4BE86990', '65F361F1'}
EXPECTED_PARA_DELTA = -3
CHARS_SAVED_PROSE = 821

def read_docx_xml(path):
    with zipfile.ZipFile(path) as z:
        return z.read("word/document.xml").decode("utf-8")


def root_open_tag(xml_str):
    start = xml_str.index("<w:document")
    end = xml_str.index(">", start) + 1
    return xml_str[start:end]


PARA_RE = re.compile(
    r'<w:p w14:paraId="([0-9A-Fa-f]{8})"[^>]*?(?:/>|(?<!/)>(.*?)</w:p>)', re.DOTALL)


def para_map(xml_str):
    out = {}
    for m in PARA_RE.finditer(xml_str):
        pid, body = m.group(1), m.group(2)
        out[pid] = body or ""
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                     help="검증만 하고 실제 파일은 하나도 안 바꾼다")
    args = ap.parse_args()

    if not os.path.isfile(DOCX):
        print(f"FATAL: not found: {DOCX}")
        sys.exit(1)

    print(f"대상: {DOCX}")
    orig_xml = read_docx_xml(DOCX)
    orig_root_open = root_open_tag(orig_xml)

    # ---- 1) 앵커 유일성(count==1) 사전 검증 ----
    problems = []
    for i, block in enumerate(DELETIONS):
        c = orig_xml.count(block)
        if c != 1:
            problems.append(f"DELETIONS[{i}]: count != 1 (got {c})")
    for old, new in NUM_FIXES:
        c = orig_xml.count(old)
        if c != 1:
            problems.append(f"NUM_FIXES old: count != 1 (got {c}) — {old[:60]}")
    if problems:
        print("FATAL: 앵커 검증 실패, 아무 것도 안 씀:")
        for p in problems:
            print("  -", p)
        sys.exit(2)
    print(f"앵커 검증 통과: 삭제블록 {len(DELETIONS)}건 + 수치수정 {len(NUM_FIXES)}건")

    # ---- 2) 적용 ----
    new_xml = orig_xml
    for block in DELETIONS:
        assert new_xml.count(block) == 1, "삭제 도중 앵커가 사라짐/중복됨"
        new_xml = new_xml.replace(block, "", 1)
    for old, new in NUM_FIXES:
        assert new_xml.count(old) == 1, "수치수정 도중 앵커가 사라짐/중복됨"
        new_xml = new_xml.replace(old, new, 1)

    # ---- 3) 전수 문단 diff 감사 ----
    old_map = para_map(orig_xml)
    new_map = para_map(new_xml)
    deleted_ids = set(old_map) - set(new_map)
    inserted_ids = set(new_map) - set(old_map)
    modified_ids = {pid for pid in (set(old_map) & set(new_map)) if old_map[pid] != new_map[pid]}

    diff_problems = []
    if deleted_ids != EXPECTED_DELETED:
        diff_problems.append(f"삭제된 paraId 불일치: 실제={deleted_ids} 기대={EXPECTED_DELETED}")
    if inserted_ids != EXPECTED_INSERTED:
        diff_problems.append(f"삽입된 paraId 불일치: 실제={inserted_ids} 기대={EXPECTED_INSERTED}")
    if modified_ids != EXPECTED_MODIFIED:
        missing = EXPECTED_MODIFIED - modified_ids
        extra = modified_ids - EXPECTED_MODIFIED
        diff_problems.append(f"수정된 paraId 불일치: 누락={missing} 예상외={extra}")

    print()
    print("전수 문단 diff 감사:")
    print(f"  삭제 {len(deleted_ids)}건 / 삽입 {len(inserted_ids)}건 / 수정 {len(modified_ids)}건")
    if diff_problems:
        print("FATAL: 의도하지 않은 변경이 섞여 있음 — 아무 것도 안 씀:")
        for p in diff_problems:
            print("  -", p)
        sys.exit(3)
    print(f"  [OK] 변경된 paraId 집합이 의도한 것과 정확히 1:1 일치")

    # ---- 4) 결과 검증 ----
    checks = []
    try:
        new_root = ET.fromstring(new_xml)
        checks.append(("well-formed XML", True, ""))
    except Exception as e:
        checks.append(("well-formed XML", False, str(e)))
        new_root = None

    new_root_open = root_open_tag(new_xml)
    checks.append(("루트 <w:document> 태그 불변", new_root_open == orig_root_open, ""))

    if new_root is not None:
        old_root = ET.fromstring(orig_xml)
        old_count = len(list(old_root.iter("{%s}p" % W_NS)))
        new_count = len(list(new_root.iter("{%s}p" % W_NS)))
        delta = new_count - old_count
        checks.append((f"문단 수 델타 == {EXPECTED_PARA_DELTA} (실제 {old_count}->{new_count}, delta {delta})",
                        delta == EXPECTED_PARA_DELTA, ""))
    else:
        checks.append(("문단 수 델타 확인", False, "well-formed 실패로 건너뜀"))

    must_be_absent = [
        "이 문단은 우리 약점을 우리가 먼저 말하는 자리",
        "77.7%",
        "92배",
    ]
    for s_ in must_be_absent:
        cnt = new_xml.count(s_)
        checks.append((f"부재 확인: '{s_[:40]}'", cnt == 0, f"{cnt}건 남음"))

    must_be_present = [
        "91.38%",  # 문단813 수정 결과
        "264.0배",  # 문단817 수정 결과
    ]
    for s_ in must_be_present:
        checks.append((f"존재 확인: '{s_[:40]}'", s_ in new_xml, "안 보임"))

    # 영문 인용문은 813에 여전히 1건 남아있어야 한다(704 삭제로 3->2가 아니라
    # 원래 1개소가 두 곳에 중복돼 있었던 것 중 704쪽만 지웠으므로 문서 전체
    # 카운트가 1 줄어야 한다) — raw XML 부분일치가 아니라 문단 단위 plain
    # text로 확인한다(813 문단이 여러 run으로 쪼개져 있어 raw substring
    # 검사가 run 경계에서 깨질 수 있다).
    def para_plain_text(pid, xml_str):
        m = re.search(r'<w:p w14:paraId="%s"[^>]*?(?:/>|(?<!/)>(.*?)</w:p>)' % pid, xml_str, re.DOTALL)
        if not m or not m.group(1):
            return ""
        return "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", m.group(1)))

    t311 = para_plain_text("247E6FE6", new_xml)
    t813 = para_plain_text("4BE86990", new_xml)
    checks.append(("§4.4 문단311(Sukprasert 인용) 원문 그대로 보존",
                    "다만 같은 연구는 공간 이득이 낮음에도" in t311, "문단 못 찾음 또는 내용 바뀜"))
    checks.append(("§7 문단813(연결 관찰) 원문 그대로 보존 + 수치만 91.38%",
                    ("즉 시간 이동이 값어치를 만드는 리전과 용량 제약이 그 값어치를 가로막는" in t813
                     and "91.38%" in t813), "문단 못 찾음 또는 내용 바뀜"))

    all_ok = all(ok for _, ok, _ in checks)
    print()
    print("결과 검증:")
    for name, ok, detail in checks:
        mark = "OK  " if ok else "FAIL"
        print(f"  [{mark}] {name}" + (f" — {detail}" if detail and not ok else ""))

    if not all_ok:
        print("\nFATAL: 검증 실패, 아무 파일도 안 씀.")
        sys.exit(4)

    print(f"\n글자수 절감(프로즈, 삭제분만): {CHARS_SAVED_PROSE}자")

    if args.dry_run:
        print("\n--dry-run 이므로 여기서 멈춘다. 실제 파일은 하나도 안 바뀜.")
        sys.exit(0)

    # ---- 5) 스냅샷 ----
    os.makedirs(VERSIONS_DIR, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M")
    snapshot_path = os.path.join(VERSIONS_DIR, f"CAST_{ts}_stage11전.docx")
    shutil.copy2(DOCX, snapshot_path)
    print(f"\n스냅샷: {snapshot_path}")

    # ---- 6) 원자적 쓰기 ----
    new_docx_path = DOCX + ".new"
    if os.path.exists(new_docx_path):
        os.remove(new_docx_path)

    with zipfile.ZipFile(DOCX, "r") as src, \
         zipfile.ZipFile(new_docx_path, "w", zipfile.ZIP_DEFLATED) as dst:
        for item in src.infolist():
            data = src.read(item.filename)
            if item.filename == "word/document.xml":
                data = new_xml.encode("utf-8")
            dst.writestr(item, data)

    # ---- 7) python-docx 로드 검증 ----
    try:
        import docx
        docx.Document(new_docx_path)
        print("python-docx 로드: OK")
    except ImportError:
        print("python-docx 미설치 — 이 검증은 건너뜀")
    except Exception as e:
        print(f"FATAL: python-docx 로드 실패: {e}")
        os.remove(new_docx_path)
        sys.exit(5)

    # ---- 8) 원자적 교체 ----
    os.replace(new_docx_path, DOCX)
    print(f"\n완료: {DOCX} 갱신됨. 스냅샷은 {snapshot_path} 에 보존.")


if __name__ == "__main__":
    main()
