# -*- coding: utf-8 -*-
"""그림 1을 전단에서 단내로 — 전단 그림을 완전히 없앤다.

사용자 지적 2번의 최종 해결. 그림 1이 전단(451pt)인 한 그 구역이 끝난 자리에
2단을 다시 잡지 못해 쪽 아래 25%가 계속 비었다. 그림을 세로형 215pt 로 다시
그렸으므로(gen_figs.py fig_architecture) 이제 본문 단 안으로 넣을 수 있다.

조치
 1. 그림 1 을 부동(anchor)에서 본문 내(inline)로 바꾼다 — 단 안에서는 부동
    배치가 오히려 글을 밀어낸다.
 2. 그림 1 캡션이 들고 있던 1단 sectPr 을 제거해 전단 구역 자체를 없앤다.
 3. 삽입 폭을 205pt 로, 새 그림 비율(215:258)에 맞춘 높이로.
"""
import re
import shutil
import zipfile
import xml.etree.ElementTree as ET

from PIL import Image

DOC = "/Users/jongha/Desktop/GitHub/carbon-aware-scheduler/paper/CAST_압축본.docx"
FIG = "/Users/jongha/Desktop/GitHub/carbon-aware-scheduler/paper/diagram/fig1_architecture.png"
PARA = re.compile(r'<w:p\b[^>]*?/>|<w:p\b[^>]*?(?<!/)>.*?</w:p>', re.DOTALL)
SECT = re.compile(r'<w:sectPr\b.*?</w:sectPr>', re.DOTALL)
ANCH = re.compile(r'<wp:anchor\b.*?</wp:anchor>', re.DOTALL)


def find(xml, head):
    for m in PARA.finditer(xml):
        if re.sub(r"<[^>]+>", "", m.group(0)).strip().startswith(head):
            return m
    raise AssertionError(head)


def main():
    shutil.copy2(DOC, DOC.replace("CAST_압축본.docx",
                 "versions/2026-09-24/CAST_압축본_그림1단내전.docx"))
    z = zipfile.ZipFile(DOC)
    parts = {i.filename: z.read(i.filename) for i in z.infolist()}
    infos = z.infolist()
    xml = parts["word/document.xml"].decode("utf-8")
    n0, d0 = len(PARA.findall(xml)), xml.count("<w:drawing>")

    im = Image.open(FIG)
    cx = int(205 * 12700)
    cy = int(cx * im.height / im.width)

    # 1) 캡션의 1단 sectPr 제거
    mc = find(xml, "그림 1. CAST의 전체 파이프라인")
    sm = SECT.search(mc.group(0))
    if sm:
        fixed = mc.group(0).replace(sm.group(0), "")
        fixed = re.sub(r'<w:pPr>\s*</w:pPr>', "", fixed)
        xml = xml[:mc.start()] + fixed + xml[mc.end():]
        print("  전단 구역(1단 sectPr) 제거")

    # 2) 그림 문단: anchor → inline, 크기 갱신
    mc = find(xml, "그림 1. CAST의 전체 파이프라인")
    prev = None
    for m in PARA.finditer(xml):
        if m.end() <= mc.start():
            prev = m
    assert "<w:drawing" in prev.group(0), "그림 1 문단을 못 찾았다"
    frag = prev.group(0)

    am = ANCH.search(frag)
    if am:
        a = am.group(0)
        inner = re.search(r'<a:graphic\b.*?</a:graphic>', a, re.DOTALL).group(0)
        ext = re.search(r'<wp:extent[^/]*/>', a)
        doc_pr = re.search(r'<wp:docPr\b[^/]*/>', a)
        inline = (f'<wp:inline distT="0" distB="0" distL="0" distR="0">'
                  f'<wp:extent cx="{cx}" cy="{cy}"/>'
                  f'<wp:effectExtent l="0" t="0" r="0" b="0"/>'
                  f'{doc_pr.group(0) if doc_pr else "<wp:docPr id=\"901\" name=\"fig1\"/>"}'
                  f'{inner}</wp:inline>')
        frag = frag[:am.start()] + inline + frag[am.end():]
        print("  부동(anchor) → 본문 내(inline) 전환")
    frag = re.sub(r'cx="\d+" cy="\d+"', f'cx="{cx}" cy="{cy}"', frag)
    xml = xml[:prev.start()] + frag + xml[prev.end():]

    # 3) 그림 파일 교체
    rid = re.search(r'r:embed="(rId\d+)"', frag).group(1)
    rel = parts["word/_rels/document.xml.rels"].decode()
    tgt = re.search(rf'Id="{rid}"[^>]*Target="([^"]+)"', rel).group(1)
    parts["word/" + tgt.replace("word/", "")] = open(FIG, "rb").read()

    ET.fromstring(xml)
    assert len(PARA.findall(xml)) == n0, "문단 수 변함"
    assert xml.count("<w:drawing>") == d0, "그림 손실"
    parts["word/document.xml"] = xml.encode()
    z.close()
    tmp = DOC + ".n"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as o:
        for it in infos:
            o.writestr(it, parts[it.filename])
    shutil.move(tmp, DOC)
    import docx
    docx.Document(DOC)
    print(f"  그림 1 → 단내 205×{cy/12700:.0f}pt")

    left = [m for m in PARA.finditer(xml) if "<w:sectPr" in m.group(0)]
    print(f"  남은 구역 {len(left)}개 (전단 그림 없음)")


if __name__ == "__main__":
    main()
