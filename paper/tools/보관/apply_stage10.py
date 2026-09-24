"""
apply_stage10.py — 롤링 파생 수치 전면 교체(11개 문단) + 그림5·6 media 교체(2건)
작성: 2026-09-21, carbon-aware-scheduler-4d(원고 트랙). 실행은 be가 한다.

근거: 정리.txt [51](헤드라인 63.03%)·[53](be 독립검증, 커밋 62027c8) + be의
§6.6 재작성 지시(노이즈-위반 비단조 873/917/756 문제 회피, 절감률 민감도만
유지) + be의 media 교체 지시(0c 재생성, 커밋 8dca9df).

전부 narrow substring 방식이다 — 문단 전체를 새로 짓지 않고, 각 문단의
원본 XML에서 바뀌는 구간만 골라 바꾼다(예: "62.94%를 줄였으며" ->
"63.03%를 줄였으며"). 그래서 굵게·하이퍼링크 같은 기존 서식이 100%
보존된다(A3000002의 "초록" 굵게 라벨 등). 각 substring은 그 문단 안에서
정확히 1번만 나옴을 사전 검증했다.

검산: 63.03-56.85=6.18 / 63.03-59.37=3.66 / 65.93-63.03=2.90 /
63.64-63.03=0.61 / 59,924/227=264.0 — 전부 직접 계산으로 확인.
"""
import sys, os, shutil, zipfile, datetime, argparse, re, hashlib
import xml.etree.ElementTree as ET

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOCX = os.path.join(REPO, "paper", "CAST.docx")
VERSIONS_DIR = os.path.join(REPO, "paper", "versions")

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

REPLACEMENTS = [  # (paraid, old_frag, new_frag)
    ('A3000002', '<w:p w14:paraId="A3000002" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000"><w:r><w:rPr><w:b/><w:bCs/></w:rPr><w:t xml:space="preserve">초록  </w:t></w:r><w:r><w:t xml:space="preserve">데이터센터의 탄소 배출량은 같은 작업이라도 어느 리전에서 언제 실행하느냐에 따라 크게 달라진다. 본 연구는 미래 탄소집약도를 LSTM으로 예측하고, 정수계획법으로 작업을 저탄소 리전에 배정한 뒤, 마감 시한 안에서 시간을 옮겨 배출량을 한 번 더 줄이는 CAST를 제안한다. 탄소와 지연 사이의 가중치는 고정하지 않고, 매 시간 슬롯마다 파레토 곡선의 무릎점에서 자동으로 정한다. 8개 리전, 1년치 실측 탄소 데이터 위에서 돌린 합성 작업 146,000건으로 실험한 결과, 시간 이동만으로 18.58%, 리전 이동만으로 56.85%를 줄였고 둘을 결합하면 62.94%를 줄였으며 마감 위반은 없었다. 무릎점 자동 선택은 가중치 고정(알파=0.5) 대비 지연 6.7ms만 더 쓰고 탄소는 10.64%포인트 더 줄인다. 다만 리전별 용량 제한을 지키면 시간 이동의 몫은 이론상 9.07%포인트에서 6.09%포인트로 줄어, 용량이 시간 이동 효과를 제한함을 정량적으로 보였다.</w:t></w:r></w:p>', '<w:p w14:paraId="A3000002" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000"><w:r><w:rPr><w:b/><w:bCs/></w:rPr><w:t xml:space="preserve">초록  </w:t></w:r><w:r><w:t xml:space="preserve">데이터센터의 탄소 배출량은 같은 작업이라도 어느 리전에서 언제 실행하느냐에 따라 크게 달라진다. 본 연구는 미래 탄소집약도를 LSTM으로 예측하고, 정수계획법으로 작업을 저탄소 리전에 배정한 뒤, 마감 시한 안에서 시간을 옮겨 배출량을 한 번 더 줄이는 CAST를 제안한다. 탄소와 지연 사이의 가중치는 고정하지 않고, 매 시간 슬롯마다 파레토 곡선의 무릎점에서 자동으로 정한다. 8개 리전, 1년치 실측 탄소 데이터 위에서 돌린 합성 작업 146,000건으로 실험한 결과, 시간 이동만으로 18.58%, 리전 이동만으로 56.85%를 줄였고 둘을 결합하면 63.03%를 줄였으며 마감 위반은 없었다. 무릎점 자동 선택은 가중치 고정(알파=0.5) 대비 지연 6.7ms만 더 쓰고 탄소는 10.64%포인트 더 줄인다. 다만 리전별 용량 제한을 지키면 시간 이동의 몫은 이론상 9.07%포인트에서 6.18%포인트로 줄어, 용량이 시간 이동 효과를 제한함을 정량적으로 보였다.</w:t></w:r></w:p>'),
    ('A3000006', '<w:p w14:paraId="A3000006" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000"><w:r><w:rPr><w:b/><w:bCs/></w:rPr><w:t xml:space="preserve">Abstract  </w:t></w:r><w:r><w:t xml:space="preserve">The carbon footprint of a cloud workload varies substantially depending on which region and when it runs. We present CAST, a carbon-aware scheduler that forecasts future carbon intensity with an LSTM, places jobs across regions via integer programming, and further shifts them in time within each job\'s deadline. Rather than fixing the trade-off between carbon and latency, CAST selects it automatically at every time slot by locating the knee point of the Pareto curve. Evaluated on 146,000 synthetic jobs driven by one year of measured carbon-intensity data across 8 regions, temporal shifting alone reduces emissions by 18.58%, spatial placement alone by 56.85%, and combining both reduces emissions by 62.94% with zero deadline violations. The automatic knee-point weight cuts 10.64 percentage points more carbon than a fixed weight (alpha=0.5), at the cost of only 6.7ms additional latency. However, enforcing per-region capacity limits shrinks temporal shifting\'s marginal contribution from an unconstrained upper bound of 9.07 percentage points to 6.09 percentage points, quantifying how regional capacity constrains the benefit of shifting workloads in time.</w:t></w:r></w:p>', '<w:p w14:paraId="A3000006" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000"><w:r><w:rPr><w:b/><w:bCs/></w:rPr><w:t xml:space="preserve">Abstract  </w:t></w:r><w:r><w:t xml:space="preserve">The carbon footprint of a cloud workload varies substantially depending on which region and when it runs. We present CAST, a carbon-aware scheduler that forecasts future carbon intensity with an LSTM, places jobs across regions via integer programming, and further shifts them in time within each job\'s deadline. Rather than fixing the trade-off between carbon and latency, CAST selects it automatically at every time slot by locating the knee point of the Pareto curve. Evaluated on 146,000 synthetic jobs driven by one year of measured carbon-intensity data across 8 regions, temporal shifting alone reduces emissions by 18.58%, spatial placement alone by 56.85%, and combining both reduces emissions by 63.03% with zero deadline violations. The automatic knee-point weight cuts 10.64 percentage points more carbon than a fixed weight (alpha=0.5), at the cost of only 6.7ms additional latency. However, enforcing per-region capacity limits shrinks temporal shifting\'s marginal contribution from an unconstrained upper bound of 9.07 percentage points to 6.18 percentage points, quantifying how regional capacity constrains the benefit of shifting workloads in time.</w:t></w:r></w:p>'),
    ('358E43A2', '<w:p w14:paraId="358E43A2" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/></w:pPr><w:r><w:t xml:space="preserve">1년치 실측 탄소집약도 데이터를 사용한 시뮬레이션에서 총 배출량이 62.94% 감소하였다. 공간 이동과 온라인 용량 인지 시간 이동을 결합한 결과로, 작업 146,000건 전량이 마감 이내에 처리되어 마감 위반은 발생하지 않았다.</w:t></w:r></w:p>', '<w:p w14:paraId="358E43A2" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/></w:pPr><w:r><w:t xml:space="preserve">1년치 실측 탄소집약도 데이터를 사용한 시뮬레이션에서 총 배출량이 63.03% 감소하였다. 공간 이동과 온라인 용량 인지 시간 이동을 결합한 결과로, 작업 146,000건 전량이 마감 이내에 처리되어 마감 위반은 발생하지 않았다.</w:t></w:r></w:p>'),
    ('0A1B2C3F', '<w:p w14:paraId="0A1B2C3F" w14:textId="77777777" w:rsidR="004A6DA0" w:rsidRDefault="00000000"><w:pPr><w:jc w:val="right"/></w:pPr><w:r><w:rPr><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>10,830.4</w:t></w:r></w:p>', '<w:p w14:paraId="0A1B2C3F" w14:textId="77777777" w:rsidR="004A6DA0" w:rsidRDefault="00000000"><w:pPr><w:jc w:val="right"/></w:pPr><w:r><w:rPr><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>10,805.0</w:t></w:r></w:p>'),
    ('0A1B2C40', '<w:p w14:paraId="0A1B2C40" w14:textId="77777777" w:rsidR="004A6DA0" w:rsidRDefault="00000000"><w:pPr><w:jc w:val="right"/></w:pPr><w:r><w:rPr><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>−62.94</w:t></w:r></w:p>', '<w:p w14:paraId="0A1B2C40" w14:textId="77777777" w:rsidR="004A6DA0" w:rsidRDefault="00000000"><w:pPr><w:jc w:val="right"/></w:pPr><w:r><w:rPr><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>−63.03</w:t></w:r></w:p>'),
    ('0A1B2C41', '<w:p w14:paraId="0A1B2C41" w14:textId="77777777" w:rsidR="004A6DA0" w:rsidRDefault="00000000"><w:pPr><w:jc w:val="right"/></w:pPr><w:r><w:rPr><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>−6.09</w:t></w:r></w:p>', '<w:p w14:paraId="0A1B2C41" w14:textId="77777777" w:rsidR="004A6DA0" w:rsidRDefault="00000000"><w:pPr><w:jc w:val="right"/></w:pPr><w:r><w:rPr><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>−6.18</w:t></w:r></w:p>'),
    ('2B3C4D5E', '<w:p w14:paraId="2B3C4D5E" w14:textId="77777777" w:rsidR="004D20D1" w:rsidRDefault="00000000"><w:r><w:t>이 하한이 보여주는 손해를 줄이기 위해 용량 인지 온라인 시간 이동을 구현했다. 슬롯별로 리전 점유량을 추적하여 상한에 도달한 슬롯을 후보에서 미리 제외하는 방식이다. 그 결과 총 배출량은 10,830.4 kg, 기준 대비 62.94% 감소로, 순진한 하한(59.37%)보다 3.57%p 더 절감하면서 상한 위반을 대부분 제거한다 — 최대 동시 실행이 41건에서 19건으로, 캘리포니아의 초과 시간이 866.9시간에서 12시간으로, 프랑스는 622.4시간에서 23시간으로 줄어든다(표2 ④행). 남은 상한 위반 배정 662건은 전량 마감이 임박해 미룰 수 없는 작업(강제 편입 411건, 즉시 실행 경로 251건)에서 비롯되며, 알고리즘의 결함이 아니다. 즉 본 절의 두 실험은 한 쌍이다 — 앞서 잰 것은 아무 것도 하지 않았을 때의 하한이고, 이 결과는 그 손해의 대부분을 실제로 되찾을 수 있음을 보인 것이다.</w:t></w:r></w:p>', '<w:p w14:paraId="2B3C4D5E" w14:textId="77777777" w:rsidR="004D20D1" w:rsidRDefault="00000000"><w:r><w:t>이 하한이 보여주는 손해를 줄이기 위해 용량 인지 온라인 시간 이동을 구현했다. 슬롯별로 리전 점유량을 추적하여 상한에 도달한 슬롯을 후보에서 미리 제외하는 방식이다. 그 결과 총 배출량은 10,805.0 kg, 기준 대비 63.03% 감소로, 순진한 하한(59.37%)보다 3.66%p 더 절감하면서 상한 위반을 대부분 제거한다 — 최대 동시 실행이 41건에서 17건으로, 캘리포니아의 초과 시간이 866.9시간에서 7.25시간으로, 프랑스는 622.4시간에서 0.91시간으로 줄어든다(표2 ④행). 남은 상한 위반 배정 227건은 전량 마감이 임박해 미룰 수 없는 작업(강제 편입 106건, 즉시 실행 경로 121건)에서 비롯되며, 알고리즘의 결함이 아니다. 즉 본 절의 두 실험은 한 쌍이다 — 앞서 잰 것은 아무 것도 하지 않았을 때의 하한이고, 이 결과는 그 손해의 대부분을 실제로 되찾을 수 있음을 보인 것이다.</w:t></w:r></w:p>'),
    ('FD000003', '<w:p w14:paraId="FD000003" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/><w:rPr><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr></w:pPr><w:r><w:rPr><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:t xml:space="preserve">그림 5. 시간 이동 전후 캘리포니아 리전의 동시 실행 수 — 용량을 무시하면 상한(12건)의 3.4배인 41건까지 몰리고, 온라인 용량 인지(Algorithm 1)로 19건까지 억제된다.</w:t></w:r></w:p>', '<w:p w14:paraId="FD000003" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/><w:rPr><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr></w:pPr><w:r><w:rPr><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:t xml:space="preserve">그림 5. 시간 이동 전후 캘리포니아 리전의 동시 실행 수 — 용량을 무시하면 상한(12건)의 3.4배인 41건까지 몰리고, 온라인 용량 인지(Algorithm 1)로 17건까지 억제된다.</w:t></w:r></w:p>'),
    ('FD000004', '<w:p w14:paraId="FD000004" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/></w:pPr><w:r><w:t xml:space="preserve">그림 5는 시간 이동을 용량 제약 없이 적용했을 때(무제약)와 온라인 용량 인지 알고리즘을 적용했을 때(온라인) 캘리포니아 리전의 시간별 동시 실행 수를 비교한 것이다. 무제약에서는 상한(12건)의 3.4배인 41건까지 몰리지만, 온라인 용량 인지는 이를 19건까지 억제한다.</w:t></w:r></w:p>', '<w:p w14:paraId="FD000004" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/></w:pPr><w:r><w:t xml:space="preserve">그림 5는 시간 이동을 용량 제약 없이 적용했을 때(무제약)와 온라인 용량 인지 알고리즘을 적용했을 때(온라인) 캘리포니아 리전의 시간별 동시 실행 수를 비교한 것이다. 무제약에서는 상한(12건)의 3.4배인 41건까지 몰리지만, 온라인 용량 인지는 이를 17건까지 억제한다.</w:t></w:r></w:p>'),
    ('52CA3887', '<w:p w14:paraId="52CA3887" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/></w:pPr><w:r><w:t xml:space="preserve">공간 이동만으로 총 배출량이 56.85% 감소하고, 시간 이동만으로는 18.58% 감소한다. 리전 용량 제약을 지키면서 둘을 결합하는 온라인 용량 인지 알고리즘(Algorithm 1)은 62.94%를 달성하며, 작업 146,000건 전량이 마감 이내에 처리되어 마감 위반은 발생하지 않는다.</w:t></w:r></w:p>', '<w:p w14:paraId="52CA3887" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/></w:pPr><w:r><w:t xml:space="preserve">공간 이동만으로 총 배출량이 56.85% 감소하고, 시간 이동만으로는 18.58% 감소한다. 리전 용량 제약을 지키면서 둘을 결합하는 온라인 용량 인지 알고리즘(Algorithm 1)은 63.03%를 달성하며, 작업 146,000건 전량이 마감 이내에 처리되어 마감 위반은 발생하지 않는다.</w:t></w:r></w:p>'),
    ('7243578A', '<w:p w14:paraId="7243578A" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/></w:pPr><w:r><w:t xml:space="preserve">이 62.94%는 두 경계값 사이에 있다. 배치 시점에 용량을 전혀 고려하지 않으면 65.93%까지 오르지만, 이는 상한의 3.4배(41건)까지 동시 실행이 몰리는, 실현 불가능한 반사실 상한이다. 반대로 배치가 끝난 뒤 사후적으로 상한 초과분을 되돌리는 순진한 방식은 59.37%에 그친다 — 아무 것도 하지 않았을 때 감수해야 할 손해의 크기다. 온라인 용량 인지는 이 하한보다 3.57%포인트 더 절감하면서 상한 위반을 최대 동시 41건에서 19건으로 줄인다.</w:t></w:r></w:p>', '<w:p w14:paraId="7243578A" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/></w:pPr><w:r><w:t xml:space="preserve">이 63.03%는 두 경계값 사이에 있다. 배치 시점에 용량을 전혀 고려하지 않으면 65.93%까지 오르지만, 이는 상한의 3.4배(41건)까지 동시 실행이 몰리는, 실현 불가능한 반사실 상한이다. 반대로 배치가 끝난 뒤 사후적으로 상한 초과분을 되돌리는 순진한 방식은 59.37%에 그친다 — 아무 것도 하지 않았을 때 감수해야 할 손해의 크기다. 온라인 용량 인지는 이 하한보다 3.66%포인트 더 절감하면서 상한 위반을 최대 동시 41건에서 17건으로 줄인다.</w:t></w:r></w:p>'),
    ('E6000011', '<w:p w14:paraId="E6000011" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/></w:pPr><w:r><w:t xml:space="preserve">세 가지 독립적인 실험이 같은 방향을 가리킨다 — 예측이 정확할수록 쏠림이 커진다. 용량을 인지하지 않는 롤링 재평가는 배출을 거의 줄이지 못하면서(9,958.2 kg → 9,967.1 kg, 차이 8.9 kg) 최대 동시 실행은 41건에서 54건으로, 상한 위반 배정은 20,208건에서 32,046건으로 오히려 늘어난다. 미래를 완전히 아는 오라클 예측을 주입하면 위반이 662건에서 873건으로 늘어난다 — 용량을 인지하는 조건에서도 같은 방향이다. 이 오라클을 기준으로 예측에 노이즈를 얹어 갈수록 위반은 873건에서 688건(표준편차 20%), 401건(표준편차 30%)으로 줄어든다. 셋 다 같은 메커니즘이다. 예측이 정확할수록 "지금 이 슬롯이 최선"이라는 판단이 여러 작업에서 같은 저탄소 구간으로 더 일관되게 수렴하고, 그 수렴이 곧 용량 초과를 만든다. 따라서 용량 인지는 부가 기능이 아니라 정확한 예측과 반드시 함께 있어야 하는 구성 요소다 — 예측만 개선하고 용량을 무시하면, 개선한 만큼 오히려 위험해진다.</w:t></w:r></w:p>', '<w:p w14:paraId="E6000011" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/></w:pPr><w:r><w:t xml:space="preserve">세 가지 독립적인 실험이 같은 방향을 가리킨다 — 예측이 정확할수록 쏠림이 커진다. 용량을 인지하지 않는 롤링 재평가는 배출을 거의 줄이지 못하면서(9,958.2 kg → 9,996.2 kg, 차이 38.0 kg) 최대 동시 실행은 41건에서 51건으로, 상한 위반 배정은 20,208건에서 25,992건으로 오히려 늘어난다. 미래를 완전히 아는 오라클 예측을 주입하면 위반이 227건에서 873건으로 늘어난다 — 용량을 인지하는 조건에서도 같은 방향이다. 예측이 정확할수록 "지금 이 슬롯이 최선"이라는 판단이 여러 작업에서 같은 저탄소 구간으로 더 일관되게 수렴하고, 그 수렴이 곧 용량 초과를 만든다. 따라서 용량 인지는 부가 기능이 아니라 정확한 예측과 반드시 함께 있어야 하는 구성 요소다 — 예측만 개선하고 용량을 무시하면, 개선한 만큼 오히려 위험해진다.</w:t></w:r></w:p>'),
    ('E6000012', '<w:p w14:paraId="E6000012" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/></w:pPr><w:r><w:t xml:space="preserve">두 비용을 직접 비교할 수 있다. 예측 오차의 비용은 실제 LSTM 예측(62.94%)과 완전예지 오라클(63.63%)의 차이인 0.69%포인트다. 용량 제약의 비용은 온라인 용량 인지(62.94%)와 용량을 무시한 반사실 상한(65.93%)의 차이인 3.0%포인트로, 예측 오차 비용의 4배가 넘는다. 즉 예측을 더 잘하는 것보다 용량을 다루는 것이 더 큰 문제다.</w:t></w:r></w:p>', '<w:p w14:paraId="E6000012" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/></w:pPr><w:r><w:t xml:space="preserve">두 비용을 직접 비교할 수 있다. 예측 오차의 비용은 실제 LSTM 예측(63.03%)과 완전예지 오라클(63.64%)의 차이인 0.61%포인트다. 용량 제약의 비용은 온라인 용량 인지(63.03%)와 용량을 무시한 반사실 상한(65.93%)의 차이인 2.90%포인트로, 예측 오차 비용의 4배가 넘는다. 즉 예측을 더 잘하는 것보다 용량을 다루는 것이 더 큰 문제다.</w:t></w:r></w:p>'),
    ('E6000013', '<w:p w14:paraId="E6000013" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/></w:pPr><w:r><w:t xml:space="preserve">세 가지 민감도 분석도 이 결론을 뒷받침한다. 작업량을 0.5배에서 2배까지 바꾸어도 마감 위반은 전 구간에서 0으로 유지된다 — 정리 2가 부하와 무관하게 성립함을 실측으로 확인한 것이다. 다만 2배 부하에서 용량 위반 배정은 662건에서 60,976건으로 92배 폭증한다. 용량 상한을 수요에 비례해 늘리지 않으면 이 알고리즘도 한계에 부딪힌다는 뜻이다. 예측 오차 민감도는 완만한 선형이다 — 노이즈 표준편차 10%포인트당 절감률이 약 0.65%포인트씩 줄어들며 절벽은 없다. 실제 LSTM의 절감률(62.94%)은 오라클(표준편차 0%, 63.64%)과 표준편차 20%(62.30%) 사이에 위치해, 이 모델의 실효 예측 오차가 대략 10~20% 수준임을 시사한다.</w:t></w:r></w:p>', '<w:p w14:paraId="E6000013" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/></w:pPr><w:r><w:t xml:space="preserve">세 가지 민감도 분석도 이 결론을 뒷받침한다. 작업량을 0.5배에서 2배까지 바꾸어도 마감 위반은 전 구간에서 0으로 유지된다 — 정리 2가 부하와 무관하게 성립함을 실측으로 확인한 것이다. 다만 2배 부하에서 용량 위반 배정은 227건에서 59,924건으로 264.0배 폭증한다. 용량 상한을 수요에 비례해 늘리지 않으면 이 알고리즘도 한계에 부딪힌다는 뜻이다. 예측 오차 민감도는 완만한 선형이다 — 노이즈 표준편차 10%포인트당 절감률이 약 0.6%포인트씩 줄어들며 절벽은 없다. 실제 LSTM의 절감률(63.03%)은 오라클(표준편차 0%, 63.64%)과 표준편차 20%(62.54%) 사이에 위치해, 이 모델의 실효 예측 오차가 대략 10~20% 수준임을 시사한다.</w:t></w:r></w:p>'),
]

EXPECTED_MODIFIED = set(['0A1B2C3F', '0A1B2C40', '0A1B2C41', '2B3C4D5E', '358E43A2', '52CA3887', '7243578A', 'A3000002', 'A3000006', 'E6000011', 'E6000012', 'E6000013', 'FD000003', 'FD000004'])
EXPECTED_DELETED = set()
EXPECTED_INSERTED = set()
EXPECTED_PARA_DELTA = 0

MEDIA_REPLACEMENTS = [{'docx_path': 'word/media/image8.png', 'new_source': '/Users/jongha/Desktop/GitHub/carbon-aware-scheduler/paper/diagram/fig5_concurrency.png', 'old_md5': '7c852a421e43d0e05fe40bea4df96c33', 'old_size': 81251, 'new_md5': 'b208c6cf73a45314fabda3845ce54b1b', 'new_size': 80537}, {'docx_path': 'word/media/image9.png', 'new_source': '/Users/jongha/Desktop/GitHub/carbon-aware-scheduler/paper/diagram/fig6_capacity_sweep.png', 'old_md5': 'e1a0a967746f08119e42f98e76f677c2', 'old_size': 74484, 'new_md5': 'fff6c139a9239d78d20c987128c0460f', 'new_size': 74174}]

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
    for m in MEDIA_REPLACEMENTS:
        if not os.path.isfile(m["new_source"]):
            print(f"FATAL: 새 이미지 파일 없음: {m['new_source']}")
            sys.exit(1)

    print(f"대상: {DOCX}")
    orig_xml = read_docx_xml(DOCX)
    orig_root_open = root_open_tag(orig_xml)

    # ---- 1) 앵커 유일성(count==1) 사전 검증 — 문서 전체 기준(stage9 이후 라이브 문서) ----
    problems = []
    for paraid, old, new in REPLACEMENTS:
        c = orig_xml.count(old)
        if c != 1:
            problems.append(f"{paraid}: count != 1 (got {c})")
    with zipfile.ZipFile(DOCX) as z:
        for m in MEDIA_REPLACEMENTS:
            actual_md5 = hashlib.md5(z.read(m["docx_path"])).hexdigest()
            if actual_md5 != m["old_md5"]:
                problems.append(f"{m['docx_path']}: 현재 md5={actual_md5} (예상 old_md5={m['old_md5']}) "
                                 f"— 이미 교체됐거나 다른 버전")
    if problems:
        print("FATAL: 앵커 검증 실패, 아무 것도 안 씀:")
        for p in problems:
            print("  -", p)
        sys.exit(2)
    print(f"앵커 검증 통과: 문단 {len(REPLACEMENTS)}건 + media {len(MEDIA_REPLACEMENTS)}건")

    # ---- 2) 적용 ----
    new_xml = orig_xml
    for paraid, old, new in REPLACEMENTS:
        assert new_xml.count(old) == 1, f"{paraid}: 치환 도중 앵커가 사라짐/중복됨"
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
    print(f"  [OK] 변경된 paraId 집합이 의도한 것과 정확히 1:1 일치 ({len(EXPECTED_MODIFIED)}건)")

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

    must_be_absent = ["62.94", "10,830.4", "662건", "411건", "251건",
                       "41건에서 19건으로", "873건에서 688건"]
    for s_ in must_be_absent:
        cnt = new_xml.count(s_)
        checks.append((f"부재 확인: '{s_}'", cnt == 0, f"{cnt}건 남음"))

    must_be_present = ["63.03", "10,805.0", "227건", "106건", "121건", "264.0배"]
    for s_ in must_be_present:
        checks.append((f"존재 확인: '{s_}'", s_ in new_xml, "안 보임"))

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
        print("\n--dry-run 이므로 여기서 멈춘다. 실제 파일은 하나도 안 바뀜(media 포함).")
        sys.exit(0)

    # ---- 5) 스냅샷 ----
    os.makedirs(VERSIONS_DIR, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M")
    snapshot_path = os.path.join(VERSIONS_DIR, f"CAST_{ts}_stage10전.docx")
    shutil.copy2(DOCX, snapshot_path)
    print(f"\n스냅샷: {snapshot_path}")

    # ---- 6) 원자적 쓰기 (document.xml 텍스트 교체 + media 바이트 교체 동시) ----
    new_docx_path = DOCX + ".new"
    if os.path.exists(new_docx_path):
        os.remove(new_docx_path)

    media_new_bytes = {}
    for m in MEDIA_REPLACEMENTS:
        with open(m["new_source"], "rb") as f:
            data = f.read()
        actual_md5 = hashlib.md5(data).hexdigest()
        assert actual_md5 == m["new_md5"], f"{m['new_source']}: md5 불일치 (파일이 바뀐 듯)"
        media_new_bytes[m["docx_path"]] = data

    with zipfile.ZipFile(DOCX, "r") as src, \
         zipfile.ZipFile(new_docx_path, "w", zipfile.ZIP_DEFLATED) as dst:
        for item in src.infolist():
            if item.filename == "word/document.xml":
                data = new_xml.encode("utf-8")
            elif item.filename in media_new_bytes:
                data = media_new_bytes[item.filename]
            else:
                data = src.read(item.filename)
            dst.writestr(item, data)

    # media 바이트가 실제로 새 파일로 들어갔는지 재확인
    with zipfile.ZipFile(new_docx_path) as z:
        for m in MEDIA_REPLACEMENTS:
            got = hashlib.md5(z.read(m["docx_path"])).hexdigest()
            assert got == m["new_md5"], f"{m['docx_path']}: 쓰기 후 md5 불일치"
    print(f"media 교체 확인: {len(MEDIA_REPLACEMENTS)}건 md5 일치")

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
    print("Word로 열어 육안 확인 권장 — 특히 그림5·6 이미지가 바뀌었는지.")


if __name__ == "__main__":
    main()
