# -*- coding: utf-8 -*-
"""표 네 개의 폭을 JOK 단 폭(195.6pt)으로 줄인다.

** 사고 **: 어제 JOK 조판으로 옮기면서 **그림만 195.6pt 로 다시 박고 표는 A4 시절
215pt 를 그대로 뒀다.** 네 표 전부 단을 19.4pt 씩 넘었고, 왼쪽 단에 놓인 표1·표3 은
오른쪽 단의 그림·본문과 **글자가 겹쳐 찍히고 있었다**(b7 이 괘선 좌표로 찾았다).
오른쪽 단의 표2·표4 는 페이지 우측 여백을 침범했다.

각 열을 같은 비율(195.6/215 = 0.9098)로 줄이고, 반올림 오차는 가장 넓은 열에 몰아
합을 정확히 3912 twip 으로 맞춘다.
"""
import re, shutil, zipfile
import xml.etree.ElementTree as ET

DOC = "/Users/jongha/Desktop/GitHub/carbon-aware-scheduler/paper/CAST_JOK_본문.docx"
TBL = re.compile(r'<w:tbl>.*?</w:tbl>', re.DOTALL)
TARGET = 3912                      # 195.6pt
z = zipfile.ZipFile(DOC); parts = {i.filename: z.read(i.filename) for i in z.infolist()}
infos = z.infolist(); z.close()
x = parts["word/document.xml"].decode()

for ti, m in reversed(list(enumerate(TBL.finditer(x), 1))):
    t = m.group(0)
    old = [int(v) for v in re.findall(r'<w:gridCol w:w="(\d+)"', t)]
    assert old, f"표{ti}: gridCol 없음"
    s = sum(old)
    new = [int(round(v * TARGET / s)) for v in old]
    new[new.index(max(new))] += TARGET - sum(new)      # 반올림 오차를 가장 넓은 열에
    assert sum(new) == TARGET, (ti, new)
    # 같은 값이 여러 열에 쓰일 수 있으므로 열 순서대로 하나씩 바꾼다
    it = iter(new)
    t2 = re.sub(r'<w:gridCol w:w="\d+"/>', lambda _: f'<w:gridCol w:w="{next(it)}"/>', t)
    # tcW 는 행마다 같은 순서로 네 번 나온다
    mapping = {}
    for o, n in zip(old, new):
        mapping.setdefault(o, n)
    def fix(mm):
        o = int(mm.group(1))
        return f'<w:tcW w:w="{mapping.get(o, int(round(o*TARGET/s)))}" w:type="dxa"/>'
    t2 = re.sub(r'<w:tcW w:w="(\d+)" w:type="dxa"/>', fix, t2)
    t2 = re.sub(r'<w:tblW w:w="\d+"', f'<w:tblW w:w="{TARGET}"', t2)
    x = x[:m.start()] + t2 + x[m.end():]
    print(f"  표{ti}: {old} ({s}) → {new} ({TARGET}) · {s/20:.1f}pt → {TARGET/20:.1f}pt")

ET.fromstring(x)
parts["word/document.xml"] = x.encode()
tmp = DOC + ".new"
with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as o:
    for it2 in infos: o.writestr(it2, parts[it2.filename])
shutil.move(tmp, DOC)
import docx; docx.Document(DOC)
print("표 폭 적용 완료")
