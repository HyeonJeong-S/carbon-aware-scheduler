# -*- coding: utf-8 -*-
"""도식 두 장(그림 1·2)의 삽입 크기를 줄인다.

그림 총 높이가 1,665pt 로 본문 2.6쪽 분량이고, 그중 도식 둘이 465pt 를 쓴다.
이 둘은 손으로 그린 SVG 라 글씨를 9pt 로 크게 잡아뒀으므로 175pt 폭으로 줄여도
7.3pt 상당이라 인쇄에서 읽힌다. 자료 그림(3~10)은 이미 5~7pt 글씨라 손대지 않는다.
"""
import re
import shutil
import zipfile
import xml.etree.ElementTree as ET

DOC = "/Users/jongha/Desktop/GitHub/carbon-aware-scheduler/paper/CAST_압축본.docx"
PARA = re.compile(r'<w:p\b[^>]*?/>|<w:p\b[^>]*?(?<!/)>.*?</w:p>', re.DOTALL)
TARGET = {"그림 1. CAST의 전체 파이프라인": 176, "그림 2. 리전별 LSTM 구조": 176}


def main():
    shutil.copy2(DOC, DOC.replace("CAST_압축본.docx",
                 "versions/2026-09-24/CAST_압축본_그림축소전.docx"))
    z = zipfile.ZipFile(DOC)
    xml = z.read("word/document.xml").decode("utf-8")
    n0, d0 = len(PARA.findall(xml)), xml.count("<w:drawing>")

    paras = list(PARA.finditer(xml))
    edits = []
    for i, m in enumerate(paras):
        t = re.sub(r"<[^>]+>", "", m.group(0)).strip()
        for head, w_pt in TARGET.items():
            if t.startswith(head):
                fm = paras[i - 1]
                assert "<w:drawing" in fm.group(0), head
                ex = re.search(r'<wp:extent cx="(\d+)" cy="(\d+)"', fm.group(0))
                cx, cy = int(ex.group(1)), int(ex.group(2))
                ncx = int(w_pt * 12700)
                ncy = int(cy * ncx / cx)
                new = re.sub(r'cx="\d+" cy="\d+"', f'cx="{ncx}" cy="{ncy}"', fm.group(0))
                edits.append((fm.start(), fm.end(), new,
                              f"{head[:18]}  {cx/12700:.0f}×{cy/12700:.0f} → "
                              f"{ncx/12700:.0f}×{ncy/12700:.0f}pt"))
    for s, e, new, msg in sorted(edits, reverse=True):
        xml = xml[:s] + new + xml[e:]
        print("  ", msg)

    ET.fromstring(xml)
    assert len(PARA.findall(xml)) == n0 and xml.count("<w:drawing>") == d0
    tmp = DOC + ".n"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as o:
        for it in z.infolist():
            o.writestr(it, xml.encode() if it.filename == "word/document.xml"
                       else z.read(it.filename))
    z.close()
    shutil.move(tmp, DOC)
    import docx
    docx.Document(DOC)


if __name__ == "__main__":
    main()
