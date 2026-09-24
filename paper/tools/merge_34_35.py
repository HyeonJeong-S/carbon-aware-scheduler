# -*- coding: utf-8 -*-
"""3.4(용량 미고려 기준선)와 3.5(용량 인지)를 한 절로 합친다.

사용자: "우리 논문이 용량 인지라면, 3.4에서 그냥 용량 인지로 때려박으면 안돼?
애초에 실험 자체를 그렇게 하는거지" → "용량 인지를 고려했고, 만약에 고려하지
않으면 이렇게 된다, 이런 식으로 하는 게 낫지"

지금 구조의 문제: 제안 기법이 아닌 기준선이 절 하나를 통째로 먼저 차지해서,
읽는 사람이 "이게 우리 방법인가?" 하고 멈춘다. 비교군임을 아무리 명시해도
**순서 자체가 주는 인상**을 이기지 못한다.

새 구조: 3.4 시간 이동 하나로 합치고
  (1) 슬롯 점수 정의 — 두 방식이 공유하는 부분
  (2) 용량 인지 온라인 배정 — 제안 기법. Algorithm 1 과 보장
  (3) 용량을 보지 않으면 — 대조군. 4장 반사실 상한의 근거
순서를 뒤집으면 "우리 방법 → 안 하면 이렇게 된다"로 읽힌다.
"""
import re
import shutil
import sys

import docx
from docx.oxml.ns import qn

sys.path.insert(0, "/Users/jongha/Desktop/GitHub/carbon-aware-scheduler/paper/tools")
import docx_edit as D

DOC = "/Users/jongha/Desktop/GitHub/carbon-aware-scheduler/paper/CAST_압축본.docx"


def set_text(p, new):
    runs = p._p.findall(qn("w:r"))
    if not runs:
        p.add_run(new)
        return
    for r in runs[1:]:
        p._p.remove(r)
    for t in runs[0].findall(qn("w:t")):
        runs[0].remove(t)
    el = runs[0].makeelement(qn("w:t"), {})
    el.set(qn("xml:space"), "preserve")
    el.text = new
    runs[0].append(el)


def main():
    shutil.copy2(DOC, DOC.replace("CAST_압축본.docx",
                 "versions/2026-09-24/CAST_압축본_절통합전.docx"))

    # ── 1단계: 텍스트 수정 (docx_edit) ──
    z, xml = D.load(DOC)
    n0 = len(D.paragraphs(xml))

    # 3.4 제목 → 통합 제목
    xml, *_ = D.replace_text(xml, "3.4 시간 이동 — 마감 내 슬롯 선택",
                             "3.4 시간 이동 — 용량 인지 슬롯 선택")
    # 3.4 첫 문단: 비교군 선언 → 제안 기법 선언
    xml, o, n = D.replace_text(xml, "이 절이 기술하는 것은 제안 기법이 아니라",
        "시간 이동 단계는 작업 j의 실행 가능 윈도우를 [t_early, t_late] = [s_j, D_j − d_j]로 "
        "둔다. 후보는 이 윈도우 안의 1시간 슬롯이며, 후보를 애초에 마감 이내에서만 탐색하므로 "
        "이 단계에서 마감 위반은 정의상 발생하지 않는다. 윈도우가 비면 즉시 실행한다. 예측 "
        "지평을 벗어나는 경우도 즉시 실행으로 처리한다 — 예측이 24시간까지만 있어 비교할 "
        "근거가 없기 때문이다.")
    print(f"  3.4 도입 {o} → {n}자")
    # 3.4 끝 "정리하면 이 기준선은..." → 용량 인지로 넘어가는 다리
    xml, o, n = D.replace_text(xml, "정리하면 이 기준선은 리전의 용량을 보지 않는다.",
        "여기까지는 각 작업이 독립적으로 자기 최적 슬롯을 고르는 규칙이다. 그러나 3.2절에서 "
        "식 (3)으로 선언한 리전별 동시 실행 상한은 아직 강제되지 않았다. 이하에서 그 제약을 "
        "알고리즘 수준에서 강제한다. 식 (3)의 우변인 여유율 적용 상한 ⌊η·cap_r⌋을 K_r로 "
        "줄여 쓰고, 예측 지평을 H로 둔다.")
    print(f"  3.4 다리 {o} → {n}자")
    # 3.5 도입 문단 삭제(위 다리가 대신함)
    xml, od = D.delete(xml, "3.2절에서 식 (3)으로 리전별 동시 실행 상한을 선언했지만")
    print(f"  3.5 도입 삭제 {od}자")
    # 중복된 윈도우 설명 문단 삭제
    xml, od2 = D.delete(xml, "예측 지평을 벗어나는 경우는 즉시 실행으로 처리한다.")
    print(f"  중복 문단 삭제 {od2}자")
    # 3.5 제목 → 대조군 소제목으로 바꿔 절 끝으로 옮길 준비
    xml, *_ = D.replace_text(xml, "3.5 용량 인지 온라인 시간 이동",
                             "용량을 보지 않으면 어떻게 되는가")
    # 마지막 보장 문단 뒤에 대조군 설명을 붙인다
    xml, o, n = D.replace_text(xml, "슬롯당 계산 비용은 그 슬롯의 대기 작업 수와",
        "슬롯당 계산 비용은 그 슬롯의 대기 작업 수와 예측 지평 H의 곱에 비례한다. "
        "비교를 위해, 같은 점수 규칙을 쓰되 용량을 전혀 보지 않는 경우도 함께 측정한다. "
        "후보 슬롯을 고를 때 그 슬롯에 이미 배정된 작업 수를 참조하지 않으면 저탄소 시간대로 "
        "작업이 몰려도 아무것도 막지 않는다. 이 경우가 내는 값이 4장의 반사실 상한이며, "
        "실제로 달성한 값과의 차이가 곧 용량 제약의 대가다.")
    print(f"  대조군 설명 {o} → {n}자")
    # 빨간 글씨 문단 제거
    for h in ["<우리 논문이 용량 인지라면"]:
        try:
            xml, od3 = D.delete(xml, h)
            print(f"  빨간 글씨 삭제 {od3}자")
        except AssertionError:
            pass
    removed = 2 + (1 if "우리 논문이 용량 인지라면" not in xml else 0)
    D.save(DOC, z, xml, -removed)

    # ── 2단계: "용량을 보지 않으면" 소제목을 절 끝으로 이동 ──
    d = docx.Document(DOC)
    paras = d.paragraphs
    hi = next((i for i, p in enumerate(paras)
               if p.text.strip() == "용량을 보지 않으면 어떻게 되는가"), None)
    if hi is not None:
        # 소제목을 지운다 — 이제 본문 흐름에 녹아 별도 제목이 필요 없다
        paras[hi]._p.getparent().remove(paras[hi]._p)
        print("  '용량을 보지 않으면' 소제목 제거(본문에 녹음)")
    d.save(DOC)

    d2 = docx.Document(DOC)
    print("\n=== 절 구성 ===")
    for p in d2.paragraphs:
        t = p.text.strip()
        if re.match(r"^\d+\.\s?\d*\s*\S", t) and len(t) < 45:
            print("  ", t)


if __name__ == "__main__":
    main()
