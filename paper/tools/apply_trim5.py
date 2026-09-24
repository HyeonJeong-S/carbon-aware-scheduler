# -*- coding: utf-8 -*-
"""§6.4 압축 — 사후강제 대조군의 절차와 세부 손실 분해를 추가자료로 옮긴다.

남기는 것과 옮기는 것의 기준
  · 결론이 인용하는 수치(71.9%, 91.38%)는 반드시 본편에 남긴다 — 결론이 드는
    숫자가 본문 어디에도 없으면 심사에서 바로 걸린다.
  · 대조군을 어떻게 만들었는지(반복 되돌리기 규칙), 되돌린 건수, 리전별 건당
    손실 같은 절차·분해는 재현에 필요할 뿐 논증에는 필요 없다 → 추가자료 A.1.
  · 그림 5(용량이 시간 이동을 막는 방식)가 새로 보여주는 것은 글로 반복하지 않는다.
"""
import sys
sys.path.insert(0, "/Users/jongha/Desktop/GitHub/carbon-aware-scheduler/paper/tools")
import docx_edit as D

P = "/Users/jongha/Desktop/GitHub/carbon-aware-scheduler/paper/CAST_압축본.docx"

EDITS = [
    ("시간 이동 단계는 리전 용량을 고려하지 않는다.",
     "시간 이동 단계가 리전 용량을 고려하지 않을 때 무슨 일이 생기는지 측정하였다. 동시 실행 "
     "수는 모든 작업의 시작·종료 시각에서의 누적합으로 세며, 로드밸런서가 용량을 산정할 때 "
     "쓰는 정의와 같다."),

    ("두 리전의 성격은 상반된다.",
     "두 리전의 성격은 상반된다. 캘리포니아는 상한을 넘긴 슬롯의 91.38%가 19시부터 21시까지 "
     "세 시간에 몰리는 반면(균등 분포라면 12.5%), 프랑스는 상위 세 시간대가 30.2%로 흩어져 "
     "있다. 캘리포니아의 초과는 태양광이 만드는 좁은 저탄소 시간대로의 집중이고, 프랑스의 "
     "초과는 리전 전체가 항상 낮아 물량이 몰리는 것이다."),

    ("이 초과가 얼마나 손해로 이어지는지 가늠하기 위해",
     "이 초과가 얼마나 손해로 이어지는지 가늠하기 위해, 배치 시점에 용량을 전혀 모르는 "
     "대조군을 일부러 만들었다. 상한을 넘긴 작업을 시간 이동 이전으로 되돌리기를 초과가 "
     "사라질 때까지 반복하는 규칙이며, 용량을 아는 스케줄러보다 항상 같거나 나쁘므로 그 "
     "결과는 아무 것도 하지 않았을 때 감수할 손해의 하한이 된다. 전체의 21.4%인 31,250건이 "
     "되돌려지고 총 절감률은 65.93%에서 59.37%로 내려간다. 손실은 고르지 않아 94.3%가 "
     "캘리포니아에서 나오며, 시간 이동이 만든 절감 2,651.6 kg 가운데 캘리포니아 한 리전이 "
     "71.9%인 1,905.4 kg을 차지하고 프랑스는 2.3%에 그친다. 탄소집약도가 종일 평탄한 "
     "리전에서는 실행 시각을 옮겨도 얻을 것이 없기 때문이다. 대조군을 만든 절차와 리전별 "
     "손실 분해는 추가자료에 싣는다."),

    ("되돌린 작업은 31,250건으로 전체의 21.4%다.", None),
    ("손실은 리전에 고르게 분포하지 않는다.", None),
]


def main():
    z, xml = D.load(P)
    n0 = len(D.paragraphs(xml))
    before = sum(len(t) for *_, t in D.paragraphs(xml) if t)
    removed = 0
    for head, new in EDITS:
        if new is None:
            xml, o = D.delete(xml, head)
            removed += 1
            print(f"  삭제 {o:>4}자  {head[:30]}…")
        else:
            xml, o, n = D.replace_text(xml, head, new)
            print(f"  수정 {o:>4} → {n:>4}자 ({n-o:+5})  {head[:26]}…")
    after = sum(len(t) for *_, t in D.paragraphs(xml) if t)
    assert len(D.paragraphs(xml)) == n0 - removed
    assert xml.count("<w:drawing>") == 8, "그림 손실"
    D.save(P, z, xml, -removed)
    print(f"\n프로즈 {before:,} → {after:,}자 ({after-before:+,})")
    # 결론이 드는 숫자가 본문에 살아 있는지 확인
    import zipfile, re
    t = re.sub(r"<[^>]+>", "", zipfile.ZipFile(P).read("word/document.xml").decode())
    for k in ("91.38%", "71.9%", "59.37%", "94.3%"):
        print(f"  {'있음' if k in t else '없음!!'}  {k}")


if __name__ == "__main__":
    main()
