# -*- coding: utf-8 -*-
"""[3][9] 공식·알고리즘의 세부 설명을 추가자료로 옮긴다.

사용자: "공식에 대한 아주 세부적인 설명은 추가자료에 넣는 것도 좋을듯"
        "이러한 알고리즘에 대한 설명도 추가자료에 디테일하게 넣는것도 좋을듯"

본편에 남길 것과 옮길 것의 기준
  남긴다 — 그 식이 **무엇을 뜻하는가**, 그리고 **왜 이 논문에서 중요한가**.
  옮긴다 — 식을 한 줄씩 되짚는 해설, 다른 표기와의 대응 관계, 채택하지 않은
           대안의 사유, 증명의 중간 단계.

이렇게 하면 본편은 "이 식이 무슨 일을 하는가"만 읽고 넘어갈 수 있고, 검증하려는
독자는 추가자료에서 한 줄씩 따라갈 수 있다. 분량도 그만큼 벌린다.
"""
import shutil
import sys

sys.path.insert(0, "/Users/jongha/Desktop/GitHub/carbon-aware-scheduler/paper/tools")
import docx_edit as D

DOC = "/Users/jongha/Desktop/GitHub/carbon-aware-scheduler/paper/CAST_압축본.docx"

EDITS = [
    # 3.2 — 식 (2)~(5) 한 줄씩 되짚기 + 대안 미채택 사유 → 추가자료
    ("식 (2)는 모든 작업이 정확히 한 리전에 배정됨을,",
     "식 (2)는 배정의 유일성, 식 (4)는 실행이 제출 이후이고 마감 이내임, 식 (5)는 지연 "
     "예산을 뜻한다. 각 식의 항별 의미와, 식 (1)~(5)를 하나의 정수 계획으로 풀지 않은 "
     "사유는 추가자료에 싣는다."),
    ("여유율을 적용한 이 상한은 3.5절에서", None),
    ("식 (1)~(5)를 하나의 정수 계획으로 푸는 것은", None),

    # 3.5 — feasible 정의 되짚기, score 재사용 설명 → 추가자료
    ("식 (3)을 자리 형태로 다시 쓴 것이다.",
     "식 (3)을 남은 자리 형태로 다시 쓴 것이다. 작업을 t′에 놓으려면 시작 시점만이 아니라 "
     "실행이 끝날 때까지 매 순간 자리가 있어야 한다."),
    ("score는 3.4절의 식 (11)을 그대로 쓰되,",
     "점수는 3.4절의 식 (11)을 그대로 쓰되 예측은 매 슬롯 새로 발행된 최신값을 쓴다. "
     "제출 시점의 예측을 끝까지 쓰는 사전 예약형과 달리 미래를 안다고 가정하지 않는다."),
]


def main():
    shutil.copy2(DOC, DOC.replace("CAST_압축본.docx",
                 "versions/2026-09-24/CAST_압축본_fb39전.docx"))
    z, xml = D.load(DOC)
    n0 = len(D.paragraphs(xml))
    before = sum(len(t) for *_, t in D.paragraphs(xml) if t)
    removed = 0
    for head, new in EDITS:
        if new is None:
            xml, o = D.delete(xml, head)
            removed += 1
            print(f"  삭제 {o:>4}자  {head[:32]}…")
        else:
            xml, o, n = D.replace_text(xml, head, new)
            print(f"  수정 {o:>4} → {n:>4}자 ({n-o:+5})  {head[:28]}…")
    after = sum(len(t) for *_, t in D.paragraphs(xml) if t)
    assert len(D.paragraphs(xml)) == n0 - removed
    assert xml.count("<w:drawing>") == 8
    D.save(DOC, z, xml, -removed)
    print(f"\n프로즈 {before:,} → {after:,}자 ({after-before:+,})")


if __name__ == "__main__":
    main()
