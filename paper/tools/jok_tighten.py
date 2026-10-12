# -*- coding: utf-8 -*-
"""내용을 건드리지 않고 지면만 줄인다 — 게재료 구간(9쪽부터 50,000원/쪽) 때문.

줄이는 것만 한다. 글자 크기·본문·캡션 글은 손대지 않는다.
  · 빈 문단 삭제 (그림 여백용이 아닌 것만)
  · 영문 캡션 뒤 여백 12→6pt (캡션 묶음과 다음 문단 사이)
  · 수식 앞뒤 여백 8→4pt (수식 19개라 누적이 크다)
  · 절 제목 앞 여백 12→8pt
  · 캡션 행간 12.35→10.57pt (JOK 초록 행간과 같은 값 — 캡션은 본문보다 조이는 게 보통)
"""
import re, shutil, zipfile
import xml.etree.ElementTree as ET

DOC = "/Users/jongha/Desktop/GitHub/carbon-aware-scheduler/paper/CAST_JOK_v2.docx"
PARA = re.compile(r'<w:p\b[^>]*?/>|<w:p\b[^>]*?(?<!/)>.*?</w:p>', re.DOTALL)
TBL = re.compile(r'<w:tbl>.*?</w:tbl>', re.DOTALL)

z = zipfile.ZipFile(DOC); parts = {i.filename: z.read(i.filename) for i in z.infolist()}
infos = z.infolist(); z.close()
x = parts["word/document.xml"].decode()
tbl = [(m.start(), m.end()) for m in TBL.finditer(x)]
n_del = n_sp = n_ln = 0

for m in reversed(list(PARA.finditer(x))):
    frag = m.group(0)
    t = re.sub(r"<[^>]+>", "", frag).strip()
    has_img = '<w:drawing' in frag or '<w:pict' in frag
    has_math = '<m:oMath' in frag
    in_tbl = any(s <= m.start() < e for s, e in tbl)
    if in_tbl or '<w:sectPr' in frag:
        continue
    # ① 빈 문단 — 구역 나눔이나 그림을 품지 않은 것만 지운다
    if not t and not has_img:
        x = x[:m.start()] + x[m.end():]; n_del += 1; continue
    new = frag
    # ② 여백 조이기
    def sp(mm):
        s = mm.group(0)
        b = re.search(r'w:before="(\d+)"', s); a = re.search(r'w:after="(\d+)"', s)
        b = int(b.group(1)) if b else 0; a = int(a.group(1)) if a else 0
        if has_math:
            b, a = min(b, 80), min(a, 80)                     # 수식 4pt
        elif re.match(r'^(Fig\.|Table)\s*\d+\s', t):
            a = min(a, 120)                                    # 영문 캡션 뒤 6pt
        elif re.match(r'^\d+\.\s', t):
            b = min(b, 160)                                    # 절 제목 앞 8pt
        keep = re.sub(r'w:(before|after)="\d+"\s*', '', s)
        keep = keep.replace('<w:spacing ', f'<w:spacing w:before="{b}" w:after="{a}" ').replace('  ', ' ')
        return keep
    if '<w:spacing' in new:
        new2 = re.sub(r'<w:spacing\b[^>]*/>', sp, new)
        if new2 != new: n_sp += 1
        new = new2
    # ③ 캡션 행간
    if re.match(r'^(그림|표)\s*\d+\s', t):
        new3 = re.sub(r'(<w:spacing\b[^>]*?)w:line="\d+" w:lineRule="exact"',
                      r'\1w:line="211" w:lineRule="exact"', new)
        if new3 != new: n_ln += 1
        new = new3
    if new != frag:
        x = x[:m.start()] + new + x[m.end():]

ET.fromstring(x)
parts["word/document.xml"] = x.encode()
tmp = DOC + ".new"
with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as o:
    for it in infos: o.writestr(it, parts[it.filename])
shutil.move(tmp, DOC)
import docx; docx.Document(DOC)
print(f"  빈 문단 {n_del}개 삭제 · 여백 {n_sp}곳 조임 · 캡션 행간 {n_ln}곳")
