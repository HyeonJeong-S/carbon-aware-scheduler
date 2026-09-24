# -*- coding: utf-8 -*-
"""그림 2를 전단 폭으로 키우고 캡션이 그림에서 떨어지지 않게 한다.

증상: 그림 2가 3쪽 맨 아래, 캡션이 4쪽 맨 위로 갈라졌고 그림이 작아 글씨가 안 읽혔다.
원인: 그림 1과 같은 1단 구역(451pt)에 205pt 짜리를 넣어 가운데 작게 박혔고,
      쪽 끝에서 그림과 캡션 사이가 끊어졌다.
조치: 삽입 폭을 전단(440pt)으로 키우고, 그림 문단에 keepNext 를 주어 캡션과 묶는다.
"""
import shutil

import docx
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt
from PIL import Image

DOC = "/Users/jongha/Desktop/GitHub/carbon-aware-scheduler/paper/CAST_압축본.docx"
FIG = "/Users/jongha/Desktop/GitHub/carbon-aware-scheduler/paper/diagram/fig2_forecast.png"


def keep_next(p):
    pPr = p._p.find(qn("w:pPr"))
    if pPr is None:
        pPr = OxmlElement("w:pPr")
        p._p.insert(0, pPr)
    if pPr.find(qn("w:keepNext")) is None:
        pPr.append(OxmlElement("w:keepNext"))


def main():
    shutil.copy2(DOC, DOC.replace("CAST_압축본.docx",
                 "versions/2026-09-24/CAST_압축본_그림2폭수정전.docx"))
    d = docx.Document(DOC)
    paras = d.paragraphs
    cap_i = next(i for i, p in enumerate(paras)
                 if p.text.strip().startswith("그림 2. 리전별 탄소집약도 예측"))
    fig_p = paras[cap_i - 1]
    assert "graphicData" in fig_p._p.xml, "그림 2 문단을 찾지 못했다"

    im = Image.open(FIG)
    w = Pt(440)
    h = int(w * im.height / im.width)
    for ext in fig_p._p.iter():
        if ext.tag.endswith("}extent") or ext.tag.endswith("}ext"):
            if ext.get("cx"):
                ext.set("cx", str(int(w)))
                ext.set("cy", str(int(h)))
    # 그림 바이트도 새 판으로
    rid = fig_p._p.xpath(".//a:blip/@r:embed")[0]
    part = d.part.related_parts[rid]
    part._blob = open(FIG, "rb").read()

    keep_next(fig_p)
    for p in paras[cap_i - 3:cap_i]:      # 앞 문단들도 묶어 그림이 혼자 밀리지 않게
        keep_next(p)

    d.save(DOC)
    print(f"그림 2: 폭 440pt 로 확대, keepNext 적용 (높이 {h/12700:.0f}pt)")


if __name__ == "__main__":
    main()
