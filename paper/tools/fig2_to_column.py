# -*- coding: utf-8 -*-
"""그림 2를 전단 구역에서 빼내 단내(2단 안)로 옮긴다.

사용자 지적 2번: "하나의 사진이 2단을 다 차지하니까 어떻게 읽어야 할 지 모르겠음.
1단 안에 들어가게 하는 게 좋을듯…? 아니면 맨 위로 올리거나"

두 가지를 다 시도했다.
 · "맨 위로" — 그림 1·2 를 한 구역으로 묶었더니 두 장이 함께 다음 쪽으로 밀려
   앞 쪽이 909자만 남고 통째로 비었다. 되돌렸다.
 · "1단 안으로"(이 판) — 그림 2 만 전단 구역에서 빼 본문 단 안으로 넣는다.
   전단 그림이 하나(그림 1)만 남아 흐름이 한 번만 끊긴다.

구조: 현재 [본문(2단 끝) | 그림1 | 그림1캡션(1단 끝) | 그림2 | 그림2캡션(1단 끝) | 본문…]
     목표 [본문(2단 끝) | 그림1 | 그림1캡션(1단 끝) | 그림2 | 그림2캡션 | 본문…]
     → 그림 2 캡션이 들고 있던 1단 sectPr 을 **그림 1 캡션으로 옮기면** 1단 구역이
       그림 1 에서 끝나고 그림 2 는 그 뒤 2단 구역에 속하게 된다.
"""
import re
import shutil
import zipfile
import xml.etree.ElementTree as ET

DOC = "/Users/jongha/Desktop/GitHub/carbon-aware-scheduler/paper/CAST_압축본.docx"
FIG = "/Users/jongha/Desktop/GitHub/carbon-aware-scheduler/paper/diagram/fig2_forecast.png"
PARA = re.compile(r'<w:p\b[^>]*?/>|<w:p\b[^>]*?(?<!/)>.*?</w:p>', re.DOTALL)
SECT = re.compile(r'<w:sectPr\b.*?</w:sectPr>', re.DOTALL)


def find(xml, head):
    for m in PARA.finditer(xml):
        if re.sub(r"<[^>]+>", "", m.group(0)).strip().startswith(head):
            return m
    raise AssertionError(head)


def main():
    shutil.copy2(DOC, DOC.replace("CAST_압축본.docx",
                 "versions/2026-09-24/CAST_압축본_그림2단내전.docx"))
    z = zipfile.ZipFile(DOC)
    parts = {i.filename: z.read(i.filename) for i in z.infolist()}
    infos = z.infolist()
    xml = parts["word/document.xml"].decode("utf-8")
    n0, d0 = len(PARA.findall(xml)), xml.count("<w:drawing>")

    # 구역 규약: 문단의 sectPr 은 "여기서 끝나는 구역"의 속성이다.
    # 지금은 그림1캡션이 1단 구역을 끝내고, 그림2캡션이 또 다른 1단 구역을 끝낸다.
    # 그림2캡션의 sectPr 을 **지우기만 하면** 그림2와 그 캡션은 뒤따르는 2단
    # 구역에 합류한다 — 옮길 필요가 없다.
    m2 = find(xml, "그림 2. 리전별 탄소집약도 예측")
    s2 = SECT.search(m2.group(0))
    assert s2, "그림 2 캡션에 sectPr 이 없다 — 이미 처리됐을 수 있다"
    new2 = m2.group(0).replace(s2.group(0), "")
    new2 = re.sub(r'<w:pPr>\s*</w:pPr>', "", new2)
    xml = xml[:m2.start()] + new2 + xml[m2.end():]

    # 그림 2 삽입 폭을 단내(205pt)로 줄이고 새 그림으로 교체
    from PIL import Image
    im = Image.open(FIG)
    cx = int(205 * 12700)
    cy = int(cx * im.height / im.width)
    m2 = find(xml, "그림 2. 리전별 탄소집약도 예측")
    # 캡션 바로 앞 문단이 그림
    prev = None
    for m in PARA.finditer(xml):
        if m.end() <= m2.start():
            prev = m
    assert "<w:drawing" in prev.group(0), "그림 2 문단을 못 찾았다"
    fixed = re.sub(r'cx="\d+" cy="\d+"', f'cx="{cx}" cy="{cy}"', prev.group(0))
    xml = xml[:prev.start()] + fixed + xml[prev.end():]

    rid = re.search(r'r:embed="(rId\d+)"', fixed).group(1)
    rel = parts["word/_rels/document.xml.rels"].decode()
    tgt = re.search(rf'Id="{rid}"[^>]*Target="([^"]+)"', rel).group(1)
    parts["word/" + tgt.replace("word/", "")] = open(FIG, "rb").read()

    ET.fromstring(xml)
    assert len(PARA.findall(xml)) == n0 and xml.count("<w:drawing>") == d0
    parts["word/document.xml"] = xml.encode()
    z.close()
    tmp = DOC + ".n"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as o:
        for it in infos:
            o.writestr(it, parts[it.filename])
    shutil.move(tmp, DOC)
    import docx
    docx.Document(DOC)
    print(f"그림 2 → 단내 205pt (높이 {cy/12700:.0f}pt), 전단 구역은 그림 1 에서 끝남")


if __name__ == "__main__":
    main()
