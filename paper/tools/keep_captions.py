# -*- coding: utf-8 -*-
"""캡션이 단·쪽을 건너뛰어 쪼개지지 않게 한다.

증상: 그림 5 캡션이 왼쪽 단 아래에서 시작해 오른쪽 단 맨 위로 이어졌다. 읽는
사람은 오른쪽 단 첫 줄("세로선이 홈에 남은 몫이다…")이 무엇을 말하는지 모른 채
읽기 시작한다 — 그림은 왼쪽 단 아래에 있기 때문이다.

조치
  · 캡션 문단에 <w:keepLines/> — 캡션 자체가 쪼개지지 않는다
  · 그림 문단에 <w:keepNext/> — 그림과 캡션이 떨어지지 않는다
표 캡션도 같다.
"""
import re
import shutil

import docx
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

DOC = "/Users/jongha/Desktop/GitHub/carbon-aware-scheduler/paper/CAST_압축본.docx"


def add(p, tag):
    pPr = p._p.find(qn("w:pPr"))
    if pPr is None:
        pPr = OxmlElement("w:pPr")
        p._p.insert(0, pPr)
    if pPr.find(qn(tag)) is None:
        e = OxmlElement(tag)
        # keepNext/keepLines 는 pPr 앞쪽에 와야 한다(스키마 순서)
        pPr.insert(0, e)
        return True
    return False


def main():
    shutil.copy2(DOC, DOC.replace("CAST_압축본.docx",
                 "versions/2026-09-24/CAST_압축본_keep전.docx"))
    d = docx.Document(DOC)
    paras = d.paragraphs
    n_cap = n_fig = 0
    for i, p in enumerate(paras):
        if re.match(r"^(그림|표)\s?\d+\.", p.text.strip()):
            if add(p, "w:keepLines"):
                n_cap += 1
            # 바로 앞이 그림이면 그 문단에 keepNext
            if i > 0 and "graphicData" in paras[i - 1]._p.xml:
                if add(paras[i - 1], "w:keepNext"):
                    n_fig += 1
                add(paras[i - 1], "w:keepLines")
    d.save(DOC)
    print(f"  캡션 {n_cap}개에 keepLines · 그림 {n_fig}개에 keepNext")
    # 검증
    d2 = docx.Document(DOC)
    bad = [p.text.strip()[:34] for p in d2.paragraphs
           if re.match(r"^(그림|표)\s?\d+\.", p.text.strip())
           and p._p.find(qn("w:pPr")) is not None
           and p._p.find(qn("w:pPr")).find(qn("w:keepLines")) is None]
    print("  누락:", bad or "없음")


if __name__ == "__main__":
    main()
