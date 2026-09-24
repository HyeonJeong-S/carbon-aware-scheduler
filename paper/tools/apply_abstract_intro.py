# -*- coding: utf-8 -*-
"""초록 재작성 + 서론 압축 (2026-09-24, 사용자 승인).

초록: 모의심사 편집위원 지적 — "논문이 자기 입으로 '주된 발견은 총계가 아니라
그 분포에 있다'고 써놓고, 초록에서는 71.9%/91.38%를 한 글자도 안 내세우고
심사자가 반박하기 딱 좋은 총계(63.03%)만 판다."

서론: 16개 문단 중 상당수가 64~118자짜리 조각이라 개조식을 산문으로 옮긴
것처럼 읽힌다. 국내 논문 관례대로 합쳐 흐르게 만들고, 기여 네 가지는
모의심사 지적("실질은 하나 반이다")대로 둘로 줄인다.
"""
import sys
sys.path.insert(0, "/Users/jongha/Desktop/GitHub/carbon-aware-scheduler/paper/tools")
import docx_edit as D

P = "/Users/jongha/Desktop/GitHub/carbon-aware-scheduler/paper/CAST_압축본.docx"

ABSTRACT = (
    "초록  데이터센터의 탄소 배출량은 같은 작업이라도 어느 리전에서 언제 실행하느냐에 "
    "따라 크게 달라진다. 선행 연구는 이 잠재력을 측정했으나 대부분 리전 용량을 무제한으로 "
    "두었다. 용량을 빼면 최적해는 가장 깨끗한 리전 한 곳으로 쏠린다. 본 연구의 데이터에서도 "
    "그 조건에서는 작업의 99.75%가 프랑스 한 곳으로 몰렸는데, 이는 실제로 실행할 수 없는 "
    "배치다. 본 연구는 LSTM으로 예측한 탄소집약도 위에서 정수 계획법으로 리전을 정하고, "
    "마감 시한 안에서 실행 시각을 옮기되 리전별 용량 상한을 매 슬롯 강제하는 CAST를 "
    "제안한다. 탄소와 지연의 가중치는 고정하지 않고 슬롯마다 파레토 곡선의 무릎점에서 "
    "자동으로 정한다. 8개 리전, 1년치 실측 탄소 데이터, 합성 작업 146,000건으로 실험한 "
    "결과 배출량을 63.03% 줄였고 마감 위반은 없었다. 용량을 무시하면 65.93%까지 내려가지만, "
    "그 2.9%포인트의 대가로 상한 위반이 227건에서 20,208건으로 89배 늘어난다. 가장 중요한 "
    "발견은 총계가 아니라 분포에 있다. 시간 이동이 만든 절감의 71.9%가 캘리포니아 한 "
    "리전에서 나오고, 그 리전에서 상한을 넘긴 슬롯의 91.38%가 저녁 19시부터 21시까지 세 "
    "시간에 몰린다. 시간 이동이 값어치를 만드는 리전과 용량이 그 값어치를 가로막는 리전이 같다."
)

ABSTRACT_EN = (
    "Abstract  The carbon footprint of a cloud workload varies substantially with where and "
    "when it runs. Prior work has measured this potential but has mostly assumed unlimited "
    "regional capacity. Without a capacity limit the optimum collapses onto the single "
    "cleanest region: on our data that policy sends 99.75% of all jobs to France, a placement "
    "that cannot actually be executed. We present CAST, which forecasts carbon intensity with "
    "an LSTM, places jobs across regions by integer programming, and shifts them in time "
    "within each deadline while enforcing a per-region capacity ceiling at every slot. The "
    "weight between carbon and latency is not fixed but chosen at each slot from the knee "
    "point of the Pareto curve. On 146,000 synthetic jobs driven by one year of measured "
    "carbon-intensity data across 8 regions, CAST cuts emissions by 63.03% with no deadline "
    "violations. Ignoring capacity reaches 65.93%, but that 2.9 percentage points costs an "
    "89-fold rise in ceiling violations, from 227 to 20,208. The principal finding is not the "
    "total but its distribution: 71.9% of the savings from temporal shifting arise in "
    "California alone, and 91.38% of that region's over-capacity slots fall in the three "
    "evening hours from 19:00 to 21:00. The region where temporal shifting creates value is "
    "the same region where capacity blocks it."
)

# 서론 — 조각 문단을 합치고 기여를 둘로 줄인다
INTRO = [
    ("데이터센터가 소비하는 전력이 빠르게 늘고 있다.",
     "데이터센터가 소비하는 전력이 빠르게 늘고 있다. 국제에너지기구는 2024년 약 "
     "415TWh였던 전 세계 데이터센터 전력 소비가 2030년 945TWh에 이를 것으로 전망했으며, "
     "AI를 가장 큰 요인으로 지목했다. 에너지 사용의 투명성이 규제 대상이 된 이상 소비 "
     "전력과 그에 따른 탄소 배출을 줄이는 일은 운영상의 과제가 되었고, 이미 가동 중인 "
     "인프라에 신규 설비 투자 없이 적용할 수 있는 감축 수단이 필요하다."),
    ("에너지 사용의 투명성이 규제 대상이 된 이상", None),
    ("따라서 이미 가동 중인 인프라를 대상으로", None),
    ("그러나 배출량을 결정하는 것은 소비 전력량만이 아니다.",
     "그런데 배출량을 결정하는 것은 소비 전력량만이 아니다. 전력 1kWh를 생산할 때 "
     "배출되는 탄소량, 곧 탄소집약도는 그 순간 전력망의 발전원 구성에 따라 정해진다. "
     "본 연구가 다루는 8개 리전에서도 2025년 실측 연평균이 인도 544.1 gCO₂/kWh, 프랑스 "
     "13.6 gCO₂/kWh로 39.9배 벌어진다. 시간적으로도 하루 최댓값과 최솟값의 비가 "
     "캘리포니아 3.53배, 독일 2.39배에 이르는 반면 한국은 1.17배에 그친다. 클라우드 "
     "서비스는 이미 여러 리전에 흩어져 있고 AI 학습이나 로그 처리 같은 배치 작업은 완료 "
     "시점에 여유가 있으므로, 이 격차를 쓸 조건은 갖추어져 있다."),
    ("본 연구가 대상으로 삼은 8개 리전에서도", None),
    ("이 차이를 활용할 조건은 이미 갖추어져 있다.", None),
    ("두 축의 결합 효과는 공간 이동의 목적지가", None),
    ("시간 축에서는 구글의 CICS가, 공간 축에서는",
     "선행 연구는 두 축 중 하나에 머물러 있다. 시간 축에서는 구글의 CICS가, 공간 축에서는 "
     "CASPER와 VMware GSLB가 대표적인데, 이들은 한 축만 다룰 뿐 아니라 탄소와 그 밖의 "
     "목적 사이의 가중치를 고정 상수로 둔다. 리전 간 격차는 시각에 따라 변하므로 옮길 "
     "이득이 큰 시간과 그렇지 않은 시간에 같은 가중치를 쓰는 것은 최적이라 보기 어렵다. "
     "두 축을 함께 다룬 Sukprasert 등의 상한 분석은 공간 이동이 지배적이고 시간 이동의 "
     "추가 이득은 제한적이라고 결론지었다. 같은 연구가 전 리전 50% 가동률에서 공간 이동 "
     "절감이 이상적 조건 대비 1.9배 줄어든다는 것을 보여 용량이 결정적 변수임을 확인했음에도, "
     "정작 두 축을 결합한 분석에서는 용량 제약을 두지 않았다. 용량을 명시적으로 다룬 "
     "CarbonFlex는 단일 클러스터 내 시간 이동에 한정된다."),
    ("두 축을 함께 다룬 Sukprasert 등의 상한 분석은", None),
    ("클러스터 용량 제약을 명시적으로 다룬 CarbonFlex는", None),
    ("본 논문은 탄소 인지 스케줄링 시스템 CAST를 제안한다. CAST는 LSTM",
     "본 논문은 탄소 인지 스케줄링 시스템 CAST를 제안한다. CAST는 LSTM으로 8개 리전의 "
     "향후 24시간 탄소집약도를 예측하고, 정수 선형 계획법 기반 로드밸런서가 실행 리전을 "
     "결정한 뒤, 스케줄러가 각 작업의 마감 이내에서 실행 시각을 결정한다. 배치 결정은 "
     "예측값으로 하되 배출량 산정은 실측값으로 하여 예측 오차의 대가가 결과에 반영되도록 했다."),
    ("첫째, 공간 축의 탄소–지연 가중치를 매 슬롯",
     "본 논문의 기여는 두 가지다. 첫째, 공간 축의 탄소–지연 가중치를 고정하지 않고 매 슬롯 "
     "파레토 무릎점에서 자동으로 정하며, 시간 축의 가중치는 작업이 신고한 지연 등급의 "
     "함수로 둔다. 둘째, 시간 이동 단계가 리전 용량을 고려하지 않으면 프랑스와 "
     "캘리포니아에서 동시 실행 수가 여유율 상한의 3.4배인 41건에 이르고 연중 각각 622시간과 "
     "867시간 동안 상한을 넘는다는 것을 실측한 뒤, 이를 온라인으로 강제하는 Algorithm 1을 "
     "제시한다. 이 알고리즘은 슬롯마다 리전 점유량을 추적해 상한에 도달한 슬롯을 후보에서 "
     "빼며, 어떤 작업도 무한히 연기되지 않고 마감 위반이 생기지 않음을 증명한다. 선행 "
     "연구는 이 현상을 단일 클러스터 맥락에서 지적했을 뿐 정량화하지 않았고, 리전 간 "
     "이동과 결합한 온라인 강제 기법도 제시하지 않았다."),
    ("둘째, 공간 이동과 시간 이동을 단일 파이프라인으로", None),
    ("셋째, 시간 이동 단계가 리전 용량을 고려하지 않을 때", None),
    ("넷째, 배치 결정은 예측값으로 수행하되", None),
]


def main():
    z, xml = D.load(P)
    n0 = len(D.paragraphs(xml))
    before = sum(len(t) for *_, t in D.paragraphs(xml) if t)

    xml, o, n = D.replace_text(xml, "초록", ABSTRACT)
    print(f"  초록      {o:>5} → {n:>5}자")
    xml, o, n = D.replace_text(xml, "Abstract", ABSTRACT_EN)
    print(f"  Abstract  {o:>5} → {n:>5}자")

    removed = 0
    for head, new in INTRO:
        if new is None:
            xml, o = D.delete(xml, head)
            removed += 1
            print(f"  삭제 {o:>4}자  {head[:30]}…")
        else:
            xml, o, n = D.replace_text(xml, head, new)
            print(f"  수정 {o:>4} → {n:>4}자  {head[:26]}…")

    after = sum(len(t) for *_, t in D.paragraphs(xml) if t)
    n1 = len(D.paragraphs(xml))
    assert n1 == n0 - removed, f"문단 수 이상: {n0} → {n1} (삭제 {removed})"
    assert xml.count("<w:drawing>") == 6, "그림 손실"
    D.save(P, z, xml, -removed)
    print(f"\n프로즈 {before:,} → {after:,}자 ({before-after:+,})")
    print(f"문단 {n0} → {n1}개")


if __name__ == "__main__":
    main()
