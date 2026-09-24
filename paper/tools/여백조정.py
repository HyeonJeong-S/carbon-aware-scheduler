# -*- coding: utf-8 -*-
"""본편의 용지 여백을 바꾸고 표 폭을 새 단 폭에 맞춘다.

왜 이 도구가 있나
  2026-09-24 기준 압축본이 12쪽인데 목표는 10쪽이다. 본문을 24% 덜어내지
  않고 쪽수를 줄이는 유일한 길이 판면이다. 지금 여백이 사방 1인치(1440twip
  = 25.4mm)로 KCI 2단 논문치고 넓다. 20mm 로 줄이면 본문 면적이 11.5% 늘어
  약 10.8쪽이 된다 — 내용을 한 글자도 버리지 않는다.

왜 자동으로 안 하나
  여백은 학회가 정하는 값이고 투고 학회가 아직 안 정해졌다. 그래서 값을
  인자로 받고, 기본은 미리보기(dry-run)로만 돈다.

표를 같이 손봐야 하는 이유
  표 1~4 의 폭이 지금 단 폭(4,302twip)에 맞춰 4,300 으로 박혀 있다.
  여백만 줄이면 단은 넓어지는데 표만 좁게 남아 오른쪽에 빈 띠가 생긴다.
  이 도구는 표 폭과 열 폭을 새 단 폭에 비례해 다시 잡는다.

  ./.venv/bin/python paper/tools/여백조정.py            # 미리보기
  ./.venv/bin/python paper/tools/여백조정.py --mm 20 --apply
"""
import argparse
import os
import shutil
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime

import docx
from docx.oxml.ns import qn

PAPER = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
DOC = os.path.join(PAPER, "CAST_압축본.docx")
TWIP_PER_MM = 1440 / 25.4


def layout(doc):
    """(용지폭, 용지높이, 여백, 단 간격, 단 수) — 마지막 sectPr 기준."""
    s = doc.sections[-1]
    sect = s._sectPr
    cols = sect.find(qn('w:cols'))
    n = int(cols.get(qn('w:num'), "1")) if cols is not None else 1
    space = int(cols.get(qn('w:space'), "425")) if cols is not None else 425
    return (s.page_width.twips, s.page_height.twips,
            s.left_margin.twips, s.top_margin.twips, space, n)


def col_width(page_w, margin, space, n):
    return (page_w - 2 * margin - space * (n - 1)) // n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mm", type=float, default=20.0, help="새 여백(mm), 사방 동일")
    ap.add_argument("--apply", action="store_true", help="실제로 고친다 (기본은 미리보기)")
    a = ap.parse_args()

    d = docx.Document(DOC)
    pw, ph, lm, tm, space, n = layout(d)
    new_m = int(round(a.mm * TWIP_PER_MM))
    old_col = col_width(pw, lm, space, n)
    new_col = col_width(pw, new_m, space, n)

    print(f"용지      {pw} × {ph} twip")
    print(f"여백      {lm} → {new_m} twip   ({lm/TWIP_PER_MM:.1f}mm → {a.mm:.1f}mm)")
    print(f"본문폭    {pw-2*lm} → {pw-2*new_m}  ({(pw-2*new_m)/(pw-2*lm)-1:+.1%})")
    print(f"본문높이  {ph-2*tm} → {ph-2*new_m}  ({(ph-2*new_m)/(ph-2*tm)-1:+.1%})")
    area = ((pw-2*new_m)*(ph-2*new_m)) / ((pw-2*lm)*(ph-2*tm))
    print(f"본문 면적 {area-1:+.1%}   →  12쪽 × {1/area:.3f} ≈ {12/area:.1f}쪽 예상")
    print(f"단 폭     {old_col} → {new_col} twip ({n}단, 간격 {space})")
    print()
    print("표 폭 재조정:")
    for i, t in enumerate(d.tables, 1):
        grid = t._tbl.find(qn('w:tblGrid'))
        cols = [int(c.get(qn('w:w'))) for c in grid.findall(qn('w:gridCol'))]
        cur = sum(cols)
        scaled = [int(round(c * new_col / cur)) for c in cols]
        scaled[-1] += new_col - sum(scaled)          # 반올림 오차를 마지막 열에
        print(f"  표 {i}: {cur} → {sum(scaled)}  {cols} → {scaled}")
        if not a.apply:
            continue
        for gc, w in zip(grid.findall(qn('w:gridCol')), scaled):
            gc.set(qn('w:w'), str(w))
        tblW = t._tbl.find(qn('w:tblPr')).find(qn('w:tblW'))
        if tblW is not None:
            tblW.set(qn('w:w'), str(sum(scaled)))
        for row in t.rows:
            for cell, w in zip(row.cells, scaled):
                tcW = cell._tc.get_or_add_tcPr().find(qn('w:tcW'))
                if tcW is None:
                    tcW = cell._tc.get_or_add_tcPr().makeelement(qn('w:tcW'), {})
                    cell._tc.get_or_add_tcPr().append(tcW)
                tcW.set(qn('w:w'), str(w))
                tcW.set(qn('w:type'), "dxa")

    if not a.apply:
        print("\n미리보기만 했다. 실제로 바꾸려면 --apply 를 붙여라.")
        return

    snap = os.path.join(PAPER, "versions",
                        f"CAST_압축본_{datetime.now():%Y%m%d_%H%M%S}_before_여백.docx")
    os.makedirs(os.path.dirname(snap), exist_ok=True)
    shutil.copy2(DOC, snap)
    print("\n스냅샷:", os.path.basename(snap))

    for s in d.sections:
        s.top_margin = s.bottom_margin = s.left_margin = s.right_margin = docx.shared.Twips(new_m)
    d.save(DOC)
    docx.Document(DOC)
    print("적용 완료. 쪽수는 Word 로 PDF 를 다시 뽑아 확인할 것.")


if __name__ == "__main__":
    main()
