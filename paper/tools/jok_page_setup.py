# -*- coding: utf-8 -*-
"""CAST_JOK_v2.docx 의 쪽 규격을 정보과학회논문지(JOK) 실물에 맞춘다.

값의 출처: 5d 가 JOK e-journal 세 편(108120·108121·108123)의 **가운데 쪽 25개**를
pymupdf 로 직접 재어 얻었다. 규정 문구(182×257mm, 단 69mm, 거터 4.4mm)는 반올림된
값이라 역산하면 1.4pt 오차가 쌓인다 — 실측을 쓴다.

  용지      515.0 × 728.0pt  (181.7 × 256.8mm)
  여백      좌 57.5 · 우 53.2 · 위(본문) 83.8 · 아래 75.1pt
  머리말    쪽 위에서 56.5pt 에 한 줄(짝수쪽=영문제목+쪽번호, 홀수쪽=쪽번호+학회지명)
  꼬리말    없음 (y>700 에 아무것도 없다)
  단        2단 · 폭 195.6pt · 거터 12.5pt(4.4mm)
  ※ 위(19.9mm)보다 아래(26.5mm)가 6.6mm 크다 — 대칭이 아니다. 착오가 아니라 실측이다.

모든 <w:sectPr> 에 적용한다. 단 수(w:cols)는 구역마다 다르므로 건드리지 않는다 —
제목·초록 구역과 전단 그림 구역은 1단, 본문은 2단이다.
"""
import re, shutil, zipfile
import xml.etree.ElementTree as ET

DOC = "/Users/jongha/Desktop/GitHub/carbon-aware-scheduler/paper/CAST_JOK_v2.docx"
TW = lambda pt: int(round(pt * 20))
PG = f'<w:pgSz w:w="{TW(515.0)}" w:h="{TW(728.0)}"/>'
MAR = (f'<w:pgMar w:top="{TW(83.8)}" w:right="{TW(53.2)}" w:bottom="{TW(75.1)}" '
       f'w:left="{TW(57.5)}" w:header="{TW(56.5)}" w:footer="0" w:gutter="0"/>')
GUTTER = TW(4.4 * 72 / 25.4)

z = zipfile.ZipFile(DOC)
parts = {i.filename: z.read(i.filename) for i in z.infolist()}
infos = z.infolist(); z.close()
xml = parts["word/document.xml"].decode()

secs = list(re.finditer(r'<w:sectPr\b.*?</w:sectPr>', xml, re.DOTALL))
print(f"  구역 {len(secs)}개")
for m in reversed(secs):
    f = m.group(0)
    cols = re.search(r'<w:cols\b[^>]*/>', f)
    n = re.search(r'w:num="(\d+)"', cols.group(0)) if cols else None
    ncol = int(n.group(1)) if n else 1
    new = f
    new = re.sub(r'<w:pgSz\b[^>]*/>', PG, new) if '<w:pgSz' in new else new.replace('<w:sectPr>', '<w:sectPr>' + PG, 1)
    new = re.sub(r'<w:pgMar\b[^>]*/>', MAR, new) if '<w:pgMar' in new else new
    # 거터는 실측 4.4mm 로, 단 수는 그대로
    new = re.sub(r'<w:cols\b[^>]*/>',
                 f'<w:cols w:num="2" w:space="{GUTTER}"/>' if ncol == 2 else f'<w:cols w:space="{GUTTER}"/>',
                 new)
    xml = xml[:m.start()] + new + xml[m.end():]
    print(f"    {ncol}단 구역 갱신")

ET.fromstring(xml)
parts["word/document.xml"] = xml.encode()
tmp = DOC + ".new"
with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as o:
    for it in infos:
        o.writestr(it, parts[it.filename])
shutil.move(tmp, DOC)
import docx; docx.Document(DOC)
print("쪽 규격 적용 완료")
