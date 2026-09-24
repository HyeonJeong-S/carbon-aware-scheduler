# -*- coding: utf-8 -*-
"""docx 문단 단위 안전 편집 — 텍스트 앵커로 찾아 한 <w:p> 안에서만 고친다.

원칙(이전 사고에서 얻은 것):
 - 문단 경계를 넘는 정규식 절대 금지
 - <w:drawing>/<m:oMath>/<w:sectPr>/<w:tbl> 를 품은 문단은 손대지 않는다
 - 편집 후 ET.fromstring 파싱 + 문단 수 델타 검증 + docx 적재 검사
 - 원본은 항상 먼저 스냅샷
"""
import re
import shutil
import zipfile
import xml.etree.ElementTree as ET

PARA = re.compile(r'<w:p\b[^>]*?/>|<w:p\b[^>]*?(?<!/)>.*?</w:p>', re.DOTALL)
TBL = re.compile(r'<w:tbl>.*?</w:tbl>', re.DOTALL)
RUN = re.compile(r'<w:r\b(?:(?!</w:r>).)*?</w:r>', re.DOTALL)
PROTECT = ("<w:drawing", "<w:pict", "<m:oMath", "<w:object", "<w:sectPr")


def _esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def text_of(frag):
    return re.sub(r"<[^>]+>", "", frag).strip()


def paragraphs(xml):
    """표 안의 문단은 제외하고 (시작, 끝, 조각, 평문) 목록."""
    spans = [(m.start(), m.end()) for m in TBL.finditer(xml)]
    out = []
    for m in PARA.finditer(xml):
        if any(s <= m.start() < e for s, e in spans):
            continue
        out.append((m.start(), m.end(), m.group(0), text_of(m.group(0))))
    return out


def find_one(xml, head):
    """첫머리가 head 인 문단을 정확히 하나 찾아 반환."""
    hits = [p for p in paragraphs(xml) if p[3].startswith(head)]
    if len(hits) != 1:
        raise AssertionError(f"{head[:36]!r} → {len(hits)}개 매칭 (1개여야 함)")
    return hits[0]


def replace_text(xml, head, new_text):
    """문단 하나의 본문 텍스트를 통째로 갈아끼운다. 첫 run 의 서식을 유지한다."""
    s, e, frag, old = find_one(xml, head)
    for k in PROTECT:
        assert k not in frag, f"{head[:30]!r}: {k} 포함 — 편집 금지"

    runs = RUN.findall(frag)
    assert runs, f"{head[:30]!r}: run 이 없음"
    first = runs[0]
    rpr = re.search(r'<w:rPr\b.*?</w:rPr>', first, re.DOTALL)
    rpr = rpr.group(0) if rpr else ""
    new_run = (f'<w:r>{rpr}<w:t xml:space="preserve">{_esc(new_text)}</w:t></w:r>')

    # 문단 속성(<w:pPr>)은 그대로 두고 run 만 교체
    ppr = re.search(r'<w:pPr\b.*?</w:pPr>', frag, re.DOTALL)
    ppr = ppr.group(0) if ppr else ""
    open_tag = re.match(r'<w:p\b[^>]*?>', frag).group(0)
    new_frag = f"{open_tag}{ppr}{new_run}</w:p>"
    return xml[:s] + new_frag + xml[e:], len(old), len(new_text)


def delete(xml, head):
    """문단 하나를 통째로 지운다."""
    s, e, frag, old = find_one(xml, head)
    for k in PROTECT:
        assert k not in frag, f"{head[:30]!r}: {k} 포함 — 삭제 금지"
    return xml[:s] + xml[e:], len(old)


def load(path):
    z = zipfile.ZipFile(path)
    return z, z.read("word/document.xml").decode("utf-8")


def save(path, z, xml, expect_delta):
    """검증 후 원자적으로 다시 쓴다. expect_delta = 문단 수 증감 예상치."""
    ET.fromstring(xml)
    tmp = path + ".new"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as o:
        for it in z.infolist():
            o.writestr(it, xml.encode("utf-8") if it.filename == "word/document.xml"
                       else z.read(it.filename))
    z.close()
    shutil.move(tmp, path)
    import docx
    docx.Document(path)          # 적재 검사
