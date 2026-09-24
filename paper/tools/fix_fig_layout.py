# -*- coding: utf-8 -*-
"""전단 그림 두 장을 한 구역으로 묶는다 (사용자 지적 2번).

증상
  3쪽 아래 20%가 통째로 빈다. 그림 1(전단)과 그림 2(전단)가 **각각 별도의
  1단 구역**으로 잡혀 있어, 그림 1 구역이 끝난 자리에 그림 2가 안 들어가면
  통째로 다음 쪽으로 밀리고 그 아래가 비는 것이다.

사용자: "하나의 사진이 2단을 다 차지하니까 어떻게 읽어야 할 지 모르겠음.
        1단 안에 들어가게 하거나 맨 위로 올리거나"

조치
  두 그림과 두 캡션을 **하나의 1단 구역**으로 합친다. 그러면 [그림1·캡션·
  그림2·캡션]이 한 덩어리로 움직여 쪽 상단에 나란히 놓이고, 읽는 순서도
  "위의 그림 두 장 → 아래 두 단"으로 분명해진다.

방법
  구역은 "그 구역을 끝내는 문단의 sectPr"로 정의된다. 그림 1 캡션이 들고 있는
  sectPr(1단)을 지우면 그 구역이 다음 구역과 합쳐진다 — 그림 2 캡션의
  sectPr(1단)이 둘을 함께 끝낸다.
"""
import re
import shutil
import zipfile
import xml.etree.ElementTree as ET

DOC = "/Users/jongha/Desktop/GitHub/carbon-aware-scheduler/paper/CAST_압축본.docx"
PARA = re.compile(r'<w:p\b[^>]*?/>|<w:p\b[^>]*?(?<!/)>.*?</w:p>', re.DOTALL)
SECT = re.compile(r'<w:sectPr\b.*?</w:sectPr>', re.DOTALL)


def main():
    shutil.copy2(DOC, DOC.replace("CAST_압축본.docx",
                 "versions/2026-09-24/CAST_압축본_그림구역전.docx"))
    z = zipfile.ZipFile(DOC)
    xml = z.read("word/document.xml").decode("utf-8")
    n0 = len(PARA.findall(xml))
    d0 = xml.count("<w:drawing>")

    # 그림 1 캡션 문단을 찾아 그 sectPr 만 제거
    target = None
    for m in PARA.finditer(xml):
        t = re.sub(r"<[^>]+>", "", m.group(0)).strip()
        if t.startswith("그림 1. CAST의 전체 파이프라인"):
            target = m
            break
    assert target is not None, "그림 1 캡션을 찾지 못했다"
    frag = target.group(0)
    sm = SECT.search(frag)
    assert sm, "그림 1 캡션에 sectPr 이 없다 — 이미 합쳐졌거나 구조가 다르다"
    cols = re.search(r'<w:cols([^>]*)', sm.group(0))
    print(f"  제거할 구역: cols={cols.group(1).strip() if cols else '?'}")

    # sectPr 만 빼고, 그것을 감싸던 빈 pPr 도 정리
    fixed = frag.replace(sm.group(0), "")
    fixed = re.sub(r'<w:pPr>\s*</w:pPr>', "", fixed)
    xml = xml[:target.start()] + fixed + xml[target.end():]

    ET.fromstring(xml)
    assert len(PARA.findall(xml)) == n0, "문단 수 변함"
    assert xml.count("<w:drawing>") == d0, "그림 손실"

    tmp = DOC + ".n"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as o:
        for it in z.infolist():
            o.writestr(it, xml.encode() if it.filename == "word/document.xml"
                       else z.read(it.filename))
    z.close()
    shutil.move(tmp, DOC)
    import docx
    docx.Document(DOC)

    # 남은 구역 확인
    for i, m in enumerate(PARA.finditer(xml)):
        if "<w:sectPr" in m.group(0):
            c = re.search(r'w:num="(\d+)"', m.group(0))
            t = re.sub(r"<[^>]+>", "", m.group(0))[:34]
            print(f"  [{i:>3}] cols={c.group(1) if c else '1'}  {t}")


if __name__ == "__main__":
    main()
