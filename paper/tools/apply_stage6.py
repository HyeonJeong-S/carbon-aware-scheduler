"""
apply_stage6.py — E6(Discussion/한계 보강) + 7장 결론 갱신 일괄 적용
작성: 2026-09-21, carbon-aware-scheduler-4d(원고 트랙). 실행은 be가 한다.

내용: paper/E6_치환규칙.txt 그대로 (be 검토·확정, 노이즈 위반건수 오류 1건
수정 반영 — 오라클 873 -> σ20% 688 -> σ30% 401, LSTM 662와 직접 비교하지
않음). 정리.txt [36][37][38][40] 근거.
  1. 5.6절 "계산 비용" 문단(paraId 4B571D1D) 뒤에 B5 솔버 실측 문장 추가.
  2. 신규 "6.6 논의" 절 삽입 — 쏠림 패턴(핵심 논증) / 예측오차 vs 용량제약
     비용 비교 / 민감도 3종 요약.
  3. 7장 결론 문단 5개 재작성(헤드라인 62.94% 단일화, 무릎점 α 첫 문장,
     한계 4개, 향후과제 4개 — "용량 인지 구현"은 이미 끝났으므로 삭제)
     + 내부 메모 문단 1개 삭제.

** 앵커 설계 — stage4(그림 교체/삽입) 적용 순서와 무관하게 안전하도록 **
  "6.6 논의" 절은 6.5절의 마지막 프로즈 문단 뒤가 아니라 "7. 결론" 제목
  (paraId 16C37392) ** 바로 앞 ** 을 앵커로 쓴다. stage4가 그림6을 6.5절
  끝에 먼저 끼워 넣었든 아니든, "7. 결론" 제목은 stage4가 절대 건드리지
  않는 고정점이라 실행 순서와 무관하게 "6.6 논의"가 6.5절의 최종 내용
  (프로즈 또는 그림6) 바로 뒤, "7. 결론" 바로 앞에 온다. 나머지 항목은
  전부 w14:paraId 로 앵커해 위치 자체가 문제되지 않는다.

절차: apply_stage3.py/apply_stage4.py 와 동일 — 앵커 count==1 사전 검증 ->
전수 문단 diff 감사(의도한 paraId 집합과 1:1) -> well-formed/문단수 델타
검증 -> 스냅샷 -> 원자적 쓰기(.new 후 os.replace) -> python-docx 로드 검증.

사용법: python3 paper/tools/apply_stage6.py [--dry-run]
"""
import sys, os, shutil, zipfile, datetime, argparse, re
import xml.etree.ElementTree as ET

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOCX = os.path.join(REPO, "paper", "CAST.docx")
VERSIONS_DIR = os.path.join(REPO, "paper", "versions")

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

EXPECTED_MODIFIED = {'52CA3887', '7243578A', '6335737D', '18D3F1BF', '65F361F1'}
EXPECTED_DELETED = {'5BD8FFC3'}
EXPECTED_INSERTED = {'E6000001', 'E6000012', 'E6000016', 'E6000010', 'E6000011', 'E6000013', 'E6000015', 'E6000017', 'E6000014'}
EXPECTED_PARA_DELTA = 8  # 삽입 9 - 삭제 1

COMPCOST_ANCHOR = '<w:p w14:paraId="4B571D1D" w14:textId="77777777" w:rsidR="004D20D1" w:rsidRDefault="00000000"><w:r><w:t xml:space="preserve">슬롯당 계산 비용은 그 슬롯의 대기 작업 수와 예측 지평 H의 곱에 비례한다.</w:t></w:r></w:p>'
COMPCOST_ADD = '<w:p w14:paraId="E6000001" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/></w:pPr><w:r><w:t xml:space="preserve">실측으로는, 공간 이동의 무릎점 탐색(슬롯당 α 후보 11개에 대한 ILP)이 슬롯당 평균 174 ms, 최악 890 ms이며 1년 전체로는 약 25분이 걸린다. 시간 이동의 롤링 재평가는 이보다 훨씬 가벼워 1년치 146,000건 전체가 약 7.6초에 끝난다(단일 실행, 데이터 로딩 제외).</w:t></w:r></w:p>'
SEC7_HEADING = '<w:p w14:paraId="16C37392" w14:textId="3D4F682A" w:rsidR="00CA0C2E" w:rsidRPr="00843874" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:spacing w:line="276" w:lineRule="auto"/><w:jc w:val="left"/><w:rPr><w:rFonts w:eastAsia="Apple SD Gothic Neo"/><w:b/><w:bCs/><w:color w:val="EE0000"/><w:sz w:val="26"/><w:szCs w:val="26"/></w:rPr></w:pPr><w:r w:rsidRPr="00843874"><w:rPr><w:rFonts w:eastAsia="Apple SD Gothic Neo"/><w:b/><w:bCs/><w:color w:val="EE0000"/><w:sz w:val="26"/><w:szCs w:val="26"/></w:rPr><w:lastRenderedPageBreak/><w:t xml:space="preserve">7. </w:t></w:r><w:r w:rsidRPr="00843874"><w:rPr><w:rFonts w:eastAsia="Apple SD Gothic Neo"/><w:b/><w:bCs/><w:color w:val="EE0000"/><w:sz w:val="26"/><w:szCs w:val="26"/></w:rPr><w:t>결론</w:t></w:r></w:p>'
DISCUSSION_BLOCK = '<w:p w14:paraId="E6000017" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00CA0C2E" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/></w:pPr></w:p><w:p w14:paraId="E6000010" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/><w:rPr><w:rFonts w:eastAsia="Apple SD Gothic Neo"/><w:b/><w:bCs/><w:sz w:val="22"/><w:szCs w:val="22"/></w:rPr></w:pPr><w:r><w:rPr><w:rFonts w:eastAsia="Apple SD Gothic Neo"/><w:b/><w:bCs/><w:sz w:val="22"/><w:szCs w:val="22"/></w:rPr><w:t xml:space="preserve">6.6 논의</w:t></w:r></w:p><w:p w14:paraId="E6000011" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/></w:pPr><w:r><w:t xml:space="preserve">세 가지 독립적인 실험이 같은 방향을 가리킨다 — 예측이 정확할수록 쏠림이 커진다. 용량을 인지하지 않는 롤링 재평가는 배출을 거의 줄이지 못하면서(9,958.2 kg → 9,967.1 kg, 차이 8.9 kg) 최대 동시 실행은 41건에서 54건으로, 상한 위반 배정은 20,208건에서 32,046건으로 오히려 늘어난다. 미래를 완전히 아는 오라클 예측을 주입하면 위반이 662건에서 873건으로 늘어난다 — 용량을 인지하는 조건에서도 같은 방향이다. 이 오라클을 기준으로 예측에 노이즈를 얹어 갈수록 위반은 873건에서 688건(표준편차 20%), 401건(표준편차 30%)으로 줄어든다. 셋 다 같은 메커니즘이다. 예측이 정확할수록 "지금 이 슬롯이 최선"이라는 판단이 여러 작업에서 같은 저탄소 구간으로 더 일관되게 수렴하고, 그 수렴이 곧 용량 초과를 만든다. 따라서 용량 인지는 부가 기능이 아니라 정확한 예측과 반드시 함께 있어야 하는 구성 요소다 — 예측만 개선하고 용량을 무시하면, 개선한 만큼 오히려 위험해진다.</w:t></w:r></w:p><w:p w14:paraId="E6000015" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00CA0C2E" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/></w:pPr></w:p><w:p w14:paraId="E6000012" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/></w:pPr><w:r><w:t xml:space="preserve">두 비용을 직접 비교할 수 있다. 예측 오차의 비용은 실제 LSTM 예측(62.94%)과 완전예지 오라클(63.63%)의 차이인 0.69%포인트다. 용량 제약의 비용은 온라인 용량 인지(62.94%)와 용량을 무시한 반사실 상한(65.93%)의 차이인 3.0%포인트로, 예측 오차 비용의 4배가 넘는다. 즉 예측을 더 잘하는 것보다 용량을 다루는 것이 더 큰 문제다.</w:t></w:r></w:p><w:p w14:paraId="E6000016" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00CA0C2E" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/></w:pPr></w:p><w:p w14:paraId="E6000013" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/></w:pPr><w:r><w:t xml:space="preserve">세 가지 민감도 분석도 이 결론을 뒷받침한다. 작업량을 0.5배에서 2배까지 바꾸어도 마감 위반은 전 구간에서 0으로 유지된다 — 정리 2가 부하와 무관하게 성립함을 실측으로 확인한 것이다. 다만 2배 부하에서 용량 위반 배정은 662건에서 60,976건으로 92배 폭증한다. 용량 상한을 수요에 비례해 늘리지 않으면 이 알고리즘도 한계에 부딪힌다는 뜻이다. 예측 오차 민감도는 완만한 선형이다 — 노이즈 표준편차 10%포인트당 절감률이 약 0.65%포인트씩 줄어들며 절벽은 없다. 실제 LSTM의 절감률(62.94%)은 오라클(표준편차 0%, 63.64%)과 표준편차 20%(62.30%) 사이에 위치해, 이 모델의 실효 예측 오차가 대략 10~20% 수준임을 시사한다.</w:t></w:r></w:p><w:p w14:paraId="E6000014" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00CA0C2E" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/></w:pPr></w:p>'
P826_OLD = '<w:p w14:paraId="6335737D" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/></w:pPr><w:r><w:t>본</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>논문은</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>탄소</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>인지</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>스케줄링</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>시스템</w:t></w:r><w:r><w:t xml:space="preserve"> CAST</w:t></w:r><w:r><w:t>를</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>제안하고</w:t></w:r><w:r><w:t>, 8</w:t></w:r><w:r><w:t>개</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>리전의</w:t></w:r><w:r><w:t xml:space="preserve"> 1</w:t></w:r><w:r><w:t>년치</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>실측</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>탄소집약도</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>위에서</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>공간</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>이동과</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>시간</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>이동의</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>결합</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>효과를</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>측정하였다</w:t></w:r><w:r><w:t xml:space="preserve">. </w:t></w:r><w:r><w:t>예측</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>단계는</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>리전별</w:t></w:r><w:r><w:t xml:space="preserve"> LSTM</w:t></w:r><w:r><w:t>으로</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>향후</w:t></w:r><w:r><w:t xml:space="preserve"> 24</w:t></w:r><w:r><w:t>시간의</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>탄소집약도를</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>산출하고</w:t></w:r><w:r><w:t xml:space="preserve">, </w:t></w:r><w:r><w:t>공간</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>이동</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>단계는</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>슬롯마다</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>정수</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>계획으로</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>실행</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>리전을</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>결정하며</w:t></w:r><w:r><w:t xml:space="preserve">, </w:t></w:r><w:r><w:t>시간</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>이동</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>단계는</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>마감</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>이내에서</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>실행</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>시각을</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>결정한다</w:t></w:r><w:r><w:t>.</w:t></w:r></w:p>'
P826_NEW = '<w:p w14:paraId="6335737D" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/></w:pPr><w:r><w:t xml:space="preserve">본 논문은 탄소 인지 스케줄링 시스템 CAST를 제안한다. 탄소와 지연 사이의 가중치를 슬롯마다 파레토 무릎점에서 자동으로 결정하고, 8개 리전의 1년치 실측 탄소집약도 위에서 공간 이동과 시간 이동의 결합 효과를 측정하였다. 예측 단계는 리전별 LSTM으로 향후 24시간의 탄소집약도를 산출하고, 공간 이동 단계는 슬롯마다 정수 계획으로 실행 리전을 결정하며, 시간 이동 단계는 마감 이내에서 실행 시각을 결정한다.</w:t></w:r></w:p>'
P828_OLD = '<w:p w14:paraId="52CA3887" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/></w:pPr><w:r><w:t>공간</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>이동만으로</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>총</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>배출량이</w:t></w:r><w:r><w:t xml:space="preserve"> 56.85% </w:t></w:r><w:r><w:t>감소하였고</w:t></w:r><w:r><w:t xml:space="preserve">, </w:t></w:r><w:r><w:t>여기에</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>시간</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>이동을</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>더하면</w:t></w:r><w:r><w:t xml:space="preserve"> 65.93%</w:t></w:r><w:r><w:t>까지</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>감소한다</w:t></w:r><w:r><w:t xml:space="preserve">. </w:t></w:r><w:r><w:t>작업</w:t></w:r><w:r><w:t xml:space="preserve"> 146,000</w:t></w:r><w:r><w:t>건</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>전량이</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>마감</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>이내에</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>처리되어</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>마감</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>위반은</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>발생하지</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>않았다</w:t></w:r><w:r><w:t>.</w:t></w:r></w:p>'
P828_NEW = '<w:p w14:paraId="52CA3887" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/></w:pPr><w:r><w:t xml:space="preserve">공간 이동만으로 총 배출량이 56.85% 감소하고, 시간 이동만으로는 18.58% 감소한다. 리전 용량 제약을 지키면서 둘을 결합하는 온라인 용량 인지 알고리즘(Algorithm 1)은 62.94%를 달성하며, 작업 146,000건 전량이 마감 이내에 처리되어 마감 위반은 발생하지 않는다.</w:t></w:r></w:p>'
P830_OLD = '<w:p w14:paraId="7243578A" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/></w:pPr><w:r><w:t xml:space="preserve">그러나 이 값은 시간 이동 단계가 리전 용량을 고려하지 않은 조건에서 얻어진 것이다. 공간 이동만 적용한 상태에서는 8개 리전 전부가 여유율 상한을 지키나, 시간 이동을 적용하면 프랑스와 캘리포니아에서 동시 실행 수가 상한의 3.4배에 이른다. 배치가 결정된 뒤에 초과분을 되돌려 용량을 사후에 강제하면 총 절감은 59.37%로, 시간 이동의 한계 기여는 9.07%p에서 2.52%p로 줄어든다. 사후 강제는 배치 시점에 용량을 아는 스케줄러보다 항상 같거나 나쁜 결과를 내므로, 이 값은 하한이다. 실현 가능한 절감은 59.37%와 65.93% 사이에 있다.</w:t></w:r></w:p>'
P830_NEW = '<w:p w14:paraId="7243578A" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/></w:pPr><w:r><w:t xml:space="preserve">이 62.94%는 두 경계값 사이에 있다. 배치 시점에 용량을 전혀 고려하지 않으면 65.93%까지 오르지만, 이는 상한의 3.4배(41건)까지 동시 실행이 몰리는, 실현 불가능한 반사실 상한이다. 반대로 배치가 끝난 뒤 사후적으로 상한 초과분을 되돌리는 순진한 방식은 59.37%에 그친다 — 아무 것도 하지 않았을 때 감수해야 할 손해의 크기다. 온라인 용량 인지는 이 하한보다 3.57%포인트 더 절감하면서 상한 위반을 최대 동시 41건에서 19건으로 줄인다.</w:t></w:r></w:p>'
P834_OLD = '<w:p w14:paraId="18D3F1BF" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/></w:pPr><w:r><w:t>한계는</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>네</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>가지다</w:t></w:r><w:r><w:t xml:space="preserve">. </w:t></w:r><w:r><w:t>첫째</w:t></w:r><w:r><w:t xml:space="preserve">, </w:t></w:r><w:r><w:t>시간</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>이동</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>단계에</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>용량</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>제약을</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>온라인으로</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>반영하는</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>구현은</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>수행하지</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>않았다</w:t></w:r><w:r><w:t xml:space="preserve">. </w:t></w:r><w:r><w:t>본</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>논문은</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>용량을</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>무시했을</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>때와</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>사후에</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>강제했을</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>때의</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>결과를</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>모두</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>보고하는</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>데</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>그친다</w:t></w:r><w:r><w:t xml:space="preserve">. </w:t></w:r><w:r><w:t>둘째</w:t></w:r><w:r><w:t xml:space="preserve">, </w:t></w:r><w:r><w:t>리전</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>용량을</w:t></w:r><w:r><w:t xml:space="preserve"> 8</w:t></w:r><w:r><w:t>개</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>리전에</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>균일하게</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>부여하였고</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>탄력적</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>확장을</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>모델링하지</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>않았다</w:t></w:r><w:r><w:t xml:space="preserve">. </w:t></w:r><w:r><w:t>따라서</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>본</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>연구의</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>결과는</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>선행</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>연구의</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>결론이</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>틀렸음을</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>보인</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>것이</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>아니라</w:t></w:r><w:r><w:t xml:space="preserve">, </w:t></w:r><w:r><w:t>그</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>결론이</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>용량</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>가정에</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>얼마나</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>민감한지를</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>보인</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>것이다</w:t></w:r><w:r><w:t xml:space="preserve">. </w:t></w:r><w:r><w:t>셋째</w:t></w:r><w:r><w:t xml:space="preserve">, </w:t></w:r><w:r><w:t>소비</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>전력을</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>작업당</w:t></w:r><w:r><w:t xml:space="preserve"> 1kW </w:t></w:r><w:r><w:t>상수로</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>가정하였다</w:t></w:r><w:r><w:t xml:space="preserve">. </w:t></w:r><w:r><w:t>넷째</w:t></w:r><w:r><w:t xml:space="preserve">, </w:t></w:r><w:r><w:t>대상은</w:t></w:r><w:r><w:t xml:space="preserve"> 8</w:t></w:r><w:r><w:t>개</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>리전</w:t></w:r><w:r><w:t xml:space="preserve"> 1</w:t></w:r><w:r><w:t>년치이며</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>시뮬레이션이다</w:t></w:r><w:r><w:t>.</w:t></w:r></w:p>'
P834_NEW = '<w:p w14:paraId="18D3F1BF" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/></w:pPr><w:r><w:t xml:space="preserve">한계는 네 가지다. 첫째, 시뮬레이션 평가다 — 실측 데이터 위에서 트레이스 재생 방식으로 검증했으며, 실제 클러스터 배포는 하지 않았다. 배치 시점에 용량을 아는 경우와 모르는 경우, 사후에 강제하는 경우를 같은 작업 집합에 나란히 적용해 비교해야 하므로, 이는 한 시스템의 실배포로는 애초에 동시에 잴 수 없는 비교다. 둘째, 캘리포니아·텍사스·독일 세 리전의 기상 예보 입력은 실제 예보 API가 아니라 해당 시각에 실측된 기상값을 그대로 가져다 쓴 것이다(§5.3) — 예보 오차가 0인 이상적 상황을 가정한 셈이라, 이 세 리전의 예측 성능과 절감 효과는 실제보다 낙관적일 수 있다. 셋째, 예측 지평은 24시간까지만 시험했다 — 원자료가 24시간 예보까지만 있어 48시간 지평은 시험할 수 없었다. 넷째, 솔버의 동률 처리 비결정성(재실행 시 총배출이 최대 0.14% 차이)과 합성 워크로드 파라미터(도착률, 지연 등급 분포)의 근거는 완전하지 않다.</w:t></w:r></w:p>'
P836_OLD = '<w:p w14:paraId="65F361F1" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/></w:pPr><w:r><w:t>향후</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>과제는</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>셋이다</w:t></w:r><w:r><w:t xml:space="preserve">. </w:t></w:r><w:r><w:t>첫째</w:t></w:r><w:r><w:t xml:space="preserve">, </w:t></w:r><w:r><w:t>용량을</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>인지하는</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>온라인</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>시간</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>이동의</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>설계와</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>구현이다</w:t></w:r><w:r><w:t xml:space="preserve">. </w:t></w:r><w:r><w:t>슬롯별</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>리전</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>점유량을</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>추적하여</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>상한에</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>도달한</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>슬롯을</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>후보에서</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>배제하되</w:t></w:r><w:r><w:t xml:space="preserve">, </w:t></w:r><w:r><w:t>슬롯</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>경합</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>시</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>잔여</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>여유가</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>적은</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>작업을</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>우선하는</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>방식을</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>검토할</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>수</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>있다</w:t></w:r><w:r><w:t xml:space="preserve">. </w:t></w:r><w:r><w:t>둘째</w:t></w:r><w:r><w:t xml:space="preserve">, </w:t></w:r><w:r><w:t>리전별로</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>이질적인</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>용량과</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>탄력적</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>확장의</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>도입이다</w:t></w:r><w:r><w:t xml:space="preserve">. </w:t></w:r><w:r><w:t>본</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>연구는</w:t></w:r><w:r><w:t xml:space="preserve"> 8</w:t></w:r><w:r><w:t>개</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>리전에</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>동일한</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>용량을</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>부여하였는데</w:t></w:r><w:r><w:t xml:space="preserve">, </w:t></w:r><w:r><w:t>이</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>설정에서는</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>용량을</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>조일</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>때</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>부하가</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>고변동</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>리전으로</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>밀려나는</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>효과와</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>그</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>리전</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>안에서</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>실행</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>시각을</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>옮길</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>여지가</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>줄어드는</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>효과가</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>같은</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>부호로</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>동시에</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>일어난다</w:t></w:r><w:r><w:t xml:space="preserve">. </w:t></w:r><w:r><w:t>리전별</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>용량이</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>이질적이면</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>두</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>효과가</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>분리될</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>수</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>있으므로</w:t></w:r><w:r><w:t xml:space="preserve">, </w:t></w:r><w:r><w:t>이질</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>용량은</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>단순한</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>현실성</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>보강이</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>아니라</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>두</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>축의</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>상호작용을</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>규명하는</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>데</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>필요한</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>조건이다</w:t></w:r><w:r><w:t xml:space="preserve">. </w:t></w:r><w:r><w:t>셋째</w:t></w:r><w:r><w:t xml:space="preserve">, </w:t></w:r><w:r><w:t>실측</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>전력</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>프로파일의</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>반영이다</w:t></w:r><w:r><w:t>.</w:t></w:r></w:p>'
P836_NEW = '<w:p w14:paraId="65F361F1" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/></w:pPr><w:r><w:t xml:space="preserve">향후 과제는 넷이다. 첫째, 실제 기상 예보 API 연동으로 세 리전의 예보 누출을 제거하는 것이다. 둘째, 24시간을 넘는 예측 지평을 시험할 수 있도록 원자료를 확장하는 것이다. 셋째, 수요 증가에 맞춘 용량 산정이다 — 작업량이 2배로 늘면 본 알고리즘에서도 용량 위반 배정이 92배로 폭증하므로, 고정 상한이 아니라 수요에 비례해 조정되는 용량 모델이 필요하다. 넷째, 실제 클러스터 배포를 통한 검증이다.</w:t></w:r></w:p>'
P838_OLD = '<w:p w14:paraId="5BD8FFC3" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/><w:rPr></w:rPr></w:pPr><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>(</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>수치는</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t xml:space="preserve"> M3 </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>용량</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t xml:space="preserve"> </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>스윕</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t xml:space="preserve"> </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>결과</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t xml:space="preserve"> </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>나오면</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t xml:space="preserve"> </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>다시</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t xml:space="preserve"> </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>볼</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t xml:space="preserve"> </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>것</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t xml:space="preserve">. </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>특히</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t xml:space="preserve"> </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>셋째</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t xml:space="preserve"> </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>문단의</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t xml:space="preserve"> </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>범위</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t xml:space="preserve"> </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>표현</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>)</w:t></w:r></w:p>'

ANCHOR_STRINGS = {
    'COMPCOST_ANCHOR': COMPCOST_ANCHOR,
    'SEC7_HEADING': SEC7_HEADING,
    'P826_OLD': P826_OLD,
    'P828_OLD': P828_OLD,
    'P830_OLD': P830_OLD,
    'P834_OLD': P834_OLD,
    'P836_OLD': P836_OLD,
    'P838_OLD': P838_OLD,
}

def read_docx_xml(path):
    with zipfile.ZipFile(path) as z:
        return z.read("word/document.xml").decode("utf-8")


def root_open_tag(xml_str):
    start = xml_str.index("<w:document")
    end = xml_str.index(">", start) + 1
    return xml_str[start:end]


PARA_RE = re.compile(r'<w:p w14:paraId="([0-9A-Fa-f]{8})"[^>]*>(.*?)</w:p>', re.DOTALL)


def para_map(xml_str):
    """paraId -> full inner XML body (not just text) so structural-only changes
    are also detected. See apply_stage4.py for why this matters."""
    out = {}
    for m in PARA_RE.finditer(xml_str):
        pid, body = m.group(1), m.group(2)
        out[pid] = body
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
    for name, s in ANCHOR_STRINGS.items():
        c = orig_xml.count(s)
        if c != 1:
            problems.append(f"{name}: count != 1 (got {c})")
    if problems:
        print("FATAL: 앵커 검증 실패, 아무 것도 안 씀:")
        for p in problems:
            print("  -", p)
        sys.exit(2)
    print(f"앵커 검증 통과: {len(ANCHOR_STRINGS)}건 전부 count==1")

    # ---- 2) 적용 (메모리 안에서만) ----
    new_xml = orig_xml
    new_xml = new_xml.replace(COMPCOST_ANCHOR, COMPCOST_ANCHOR + COMPCOST_ADD, 1)
    new_xml = new_xml.replace(SEC7_HEADING, DISCUSSION_BLOCK + SEC7_HEADING, 1)
    new_xml = new_xml.replace(P826_OLD, P826_NEW, 1)
    new_xml = new_xml.replace(P828_OLD, P828_NEW, 1)
    new_xml = new_xml.replace(P830_OLD, P830_NEW, 1)
    new_xml = new_xml.replace(P834_OLD, P834_NEW, 1)
    new_xml = new_xml.replace(P836_OLD, P836_NEW, 1)
    new_xml = new_xml.replace(P838_OLD, "", 1)

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
        missing = EXPECTED_INSERTED - inserted_ids
        extra = inserted_ids - EXPECTED_INSERTED
        diff_problems.append(f"삽입된 paraId 불일치: 누락={missing} 예상외={extra}")
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
    print("  [OK] 변경된 paraId 집합이 의도한 것과 정확히 1:1 일치")

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
        "시간 이동 단계에 용량 제약을 온라인으로 반영하는 구현은 수행하지 않았다",
        "향후 과제는 셋이다. 첫째, 용량을 인지하는 온라인 시간 이동의 설계와 구현",
        "65.93%까지 감소한다",  # 옛 헤드라인 단독 서술(반사실 상한으로만 언급돼야 함)
        "(수치는 M3 용량 스윕 결과 나오면 다시 볼 것",
        "위반이 662건에서 401건으로",  # be가 지적한 오류 문장(수정 전)
    ]
    for s in must_be_absent:
        checks.append((f"부재 확인: {s[:35]}", s not in new_xml, "여전히 남아있음"))

    must_be_present = [
        "6.6 논의",
        "예측이 정확할수록 쏠림이 커진다",
        "873건", "688건", "401건",
        "예측 오차의 비용", "용량 제약의 비용",
        "62.94%를 달성",
        "무릎점에서 자동으로 결정",  # 결론 개요 문단, 무릎점 우선 서술
        "약 7.6초에 끝난다",
        "슬롯당 평균 174 ms",
    ]
    for s in must_be_present:
        checks.append((f"존재 확인: {s[:35]}", s in new_xml, "안 보임"))

    all_ok = all(ok for _, ok, _ in checks)
    print()
    print("결과 검증:")
    for name, ok, detail in checks:
        mark = "OK  " if ok else "FAIL"
        print(f"  [{mark}] {name}" + (f" — {detail}" if detail and not ok else ""))

    if not all_ok:
        print("\nFATAL: 검증 실패, 아무 파일도 안 씀.")
        sys.exit(4)

    if args.dry_run:
        print("\n--dry-run 이므로 여기서 멈춘다. 실제 파일은 하나도 안 바뀜.")
        sys.exit(0)

    # ---- 5) 스냅샷 ----
    os.makedirs(VERSIONS_DIR, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M")
    snapshot_path = os.path.join(VERSIONS_DIR, f"CAST_{ts}_E6결론갱신전.docx")
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
    print("Word로 열어 육안 확인 권장 — 특히 새 6.6절 위치(그림6과의 순서 포함)와 결론 문단.")


if __name__ == "__main__":
    main()
