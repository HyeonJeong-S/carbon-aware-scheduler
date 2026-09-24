# -*- coding: utf-8 -*-
"""10쪽 마감 감축 (2026-09-24 야간 최종).

기준: 그림이 이미 보여주는 수치, 앞 절이 이미 선언한 것, 절차를 되짚는 문장.
"""
import shutil
import sys

sys.path.insert(0, "/Users/jongha/Desktop/GitHub/carbon-aware-scheduler/paper/tools")
import docx_edit as D

DOC = "/Users/jongha/Desktop/GitHub/carbon-aware-scheduler/paper/CAST_압축본.docx"

EDITS = [
    # (3.1 개요 문단은 단 구분(sectPr)을 품어 편집 불가 — 세 번째로 확인)

    # 1절 기여 — 3.5절이 같은 수치를 다시 말한다
    ("본 논문의 기여는 두 가지다.",
     "본 논문의 기여는 두 가지다. 첫째, 공간 축의 탄소–지연 가중치를 고정하지 않고 매 슬롯 "
     "파레토 무릎점에서 자동으로 정하며, 시간 축의 가중치는 작업이 신고한 지연 등급의 "
     "함수로 둔다. 둘째, 시간 이동이 리전 용량을 고려하지 않으면 동시 실행 수가 여유율 "
     "상한의 3.4배에 이른다는 것을 실측한 뒤, 이를 온라인으로 강제하는 Algorithm 1을 "
     "제시한다. 이 알고리즘은 슬롯마다 리전 점유량을 추적해 상한에 도달한 슬롯을 후보에서 "
     "빼며, 어떤 작업도 무한히 연기되지 않고 마감 위반이 생기지 않음을 증명한다. 선행 "
     "연구는 이 현상을 단일 클러스터 맥락에서 지적했을 뿐 정량화하지 않았고, 리전 간 "
     "이동과 결합한 온라인 강제 기법도 제시하지 않았다."),

    # 4.3 사후강제 — 절차 설명을 줄인다(추가자료가 담는다)
    ("이 초과가 얼마나 손해로 이어지는지 가늠하기 위해",
     "이 초과가 얼마나 손해로 이어지는지 가늠하기 위해, 배치 시점에 용량을 전혀 모르는 "
     "대조군을 만들었다. 상한을 넘긴 작업을 되돌리기를 초과가 사라질 때까지 반복하는 "
     "규칙이며, 용량을 아는 스케줄러보다 항상 같거나 나쁘므로 그 결과는 아무 것도 하지 "
     "않았을 때 감수할 손해의 하한이 된다. 전체의 21.4%인 31,250건이 되돌려지고 총 "
     "절감률은 65.93%에서 59.37%로 내려간다. 손실은 고르지 않아 94.3%가 캘리포니아에서 "
     "나오며, 시간 이동이 만든 절감의 71.9%도 그 리전 몫이다. 탄소집약도가 종일 평탄한 "
     "리전에서는 실행 시각을 옮겨도 얻을 것이 없기 때문이다. 대조군의 절차와 리전별 손실 "
     "분해는 추가자료에 싣는다."),
]


def main():
    shutil.copy2(DOC, DOC.replace("CAST_압축본.docx",
                 "versions/2026-09-24/CAST_압축본_trim7전.docx"))
    z, xml = D.load(DOC)
    n0 = len(D.paragraphs(xml))
    before = sum(len(t) for *_, t in D.paragraphs(xml) if t)
    for head, new in EDITS:
        xml, o, n = D.replace_text(xml, head, new)
        print(f"  {o:>4} → {n:>4}자 ({n-o:+5})  {head[:30]}…")
    after = sum(len(t) for *_, t in D.paragraphs(xml) if t)
    assert len(D.paragraphs(xml)) == n0 and xml.count("<w:drawing>") == 10
    D.save(DOC, z, xml, 0)
    print(f"\n프로즈 {before:,} → {after:,}자 ({after-before:+,})")


if __name__ == "__main__":
    main()
