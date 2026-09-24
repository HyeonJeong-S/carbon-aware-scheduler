# -*- coding: utf-8 -*-
"""표 1(α → 배정)을 빼고 그 내용을 본문 두 문장으로 흡수한다.

표와 그림 5가 겹친다. 표는 한 슬롯에서 α를 바꿨을 때의 배정을, 그림 5는 1년치
전체가 실제로 어디로 갔는지를 보인다. 둘 다 "라우팅"을 말하는데, 실측 전체를 보이는
그림 쪽이 강하고 표의 세 줄은 문장으로 옮겨도 잃는 것이 없다.

사용자가 표를 두 번 요청한 것은 "α가 정해지면 어디로 가는지 보여달라"는 뜻이었고,
그 요구는 표가 아니라 **그 내용**이 충족한다. 그림 5가 훨씬 더 많이 답한다.
"""
import shutil
import sys

import docx
from docx.oxml.ns import qn

sys.path.insert(0, "/Users/jongha/Desktop/GitHub/carbon-aware-scheduler/paper/tools")
import docx_edit as D

DOC = "/Users/jongha/Desktop/GitHub/carbon-aware-scheduler/paper/CAST_압축본.docx"


def main():
    shutil.copy2(DOC, DOC.replace("CAST_압축본.docx",
                 "versions/2026-09-24/CAST_압축본_표1삭제전.docx"))
    # 1) 표와 캡션 제거 (python-docx)
    d = docx.Document(DOC)
    cap = next(p for p in d.paragraphs if p.text.strip().startswith("표 1. 가중치 α"))
    tbl = [t for t in d.tables if len(t.rows) == 4 and "배정 리전" in t.rows[0].cells[1].text][0]
    tbl._tbl.getparent().remove(tbl._tbl)
    cap._p.getparent().remove(cap._p)
    d.save(DOC)
    print("  표 1과 캡션 제거")

    # 2) 표를 소개하던 문단을 그림 5 소개로 바꾸고, 표의 내용을 문장으로 흡수
    z, xml = D.load(DOC)
    n0 = len(D.paragraphs(xml))
    xml, o, n = D.replace_text(xml, "가중치가 배정을 어떻게 바꾸는지는",
        "가중치가 배정을 어떻게 바꾸는지는 한 슬롯을 열어 보면 분명하다. 그림 4의 슬롯에서 "
        "α를 0에서 1까지 옮기면 목적지가 세 구간으로 갈린다 — 0.4 이하에서는 홈(한국, "
        "351 gCO₂/kWh), 0.5에서 0.8 사이에서는 캘리포니아(14, 134 ms), 1.0에서는 "
        "프랑스(9, 238 ms)다. 무릎점 0.508은 가운데 구간에 들어, 탄소를 홈 대비 96% 줄이면서 "
        "지연은 상한의 55%만 쓴다. 실제 배정은 리전별 잔여 용량 안에서만 이루어지므로 같은 "
        "α라도 그 슬롯에 자리가 없으면 다음 후보로 넘어간다.")
    print(f"  소개 문단 {o} → {n}자 (표 내용 흡수)")
    assert len(D.paragraphs(xml)) == n0
    D.save(DOC, z, xml, 0)

    # 3) 표 번호 재매김
    import renumber_tables
    renumber_tables.main()


if __name__ == "__main__":
    main()
