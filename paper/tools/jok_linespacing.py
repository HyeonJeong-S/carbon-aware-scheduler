# -*- coding: utf-8 -*-
"""문단 유형별 행간. 고정 행간(exact)을 문서 전체에 걸면 안 된다.

** 사고(2026-10-08) ** : pPrDefault 에 line=247 lineRule=exact(12.35pt)를 걸었더니
그림 문단과 수식 문단이 그 높이로 **잘렸다** — 3쪽에서 그림1·2·3이 아래 한 줄만
남았다. 인라인 그림은 줄 높이를 따르므로, 고정 행간은 글줄 문단에만 걸어야 한다.

JOK 실측(5d, 세 편): 본문 12.35 · 초록 10.57 · 참고문헌 10.15pt.
그림·수식·제목은 내용 높이를 따라야 하므로 auto 로 둔다.
"""
import re, shutil, zipfile
import xml.etree.ElementTree as ET

DOC = "/Users/jongha/Desktop/GitHub/carbon-aware-scheduler/paper/CAST_JOK_v2.docx"
PARA = re.compile(r'<w:p\b[^>]*?/>|<w:p\b[^>]*?(?<!/)>.*?</w:p>', re.DOTALL)
TBL = re.compile(r'<w:tbl>.*?</w:tbl>', re.DOTALL)

BODY, ABSTRACT, REFS = 247, 211, 203     # 12.35 / 10.57 / 10.15pt
AUTO = ('240', 'auto')


def want(t, frag, in_tbl):
    if '<w:drawing' in frag or '<w:pict' in frag:  return AUTO          # 그림 — 잘리면 안 된다
    if '<m:oMath' in frag:                          return AUTO          # 수식 — 분수·적분이 높다
    if in_tbl:                                      return AUTO          # 표 칸 — 줄바꿈 높이가 제각각
    if re.match(r'^CAST:', t):                      return AUTO          # 제목 두 줄
    if re.match(r'^(이종하|단국대학교)', t):          return AUTO
    if re.match(r'^\[\d+\]', t):                    return (str(REFS), 'exact')
    if t.startswith(("초록", "주제어:", "Abstract", "Keywords:")):
        return (str(ABSTRACT), 'exact')
    return (str(BODY), 'exact')


z = zipfile.ZipFile(DOC); parts = {i.filename: z.read(i.filename) for i in z.infolist()}
infos = z.infolist(); z.close()
x = parts["word/document.xml"].decode()
tbl = [(m.start(), m.end()) for m in TBL.finditer(x)]
cnt = {}
for m in reversed(list(PARA.finditer(x))):
    frag = m.group(0)
    t = re.sub(r"<[^>]+>", "", frag).strip()
    in_tbl = any(s <= m.start() < e for s, e in tbl)
    if not t and '<w:drawing' not in frag:
        continue
    line, rule = want(t, frag, in_tbl)
    sp = f'<w:spacing w:line="{line}" w:lineRule="{rule}"/>'
    pm = re.search(r'<w:pPr\b.*?</w:pPr>', frag, re.DOTALL)
    if pm:
        ppr = pm.group(0)
        if '<w:spacing' in ppr:
            # 기존 spacing 의 before/after 는 살리고 line 만 바꾼다
            def fix(mm):
                a = dict(re.findall(r'w:(before|after|beforeLines|afterLines)="([^"]+)"', mm.group(0)))
                attrs = " ".join(f'w:{k}="{v}"' for k, v in a.items())
                return f'<w:spacing {attrs} w:line="{line}" w:lineRule="{rule}"/>'.replace("  ", " ")
            new_ppr = re.sub(r'<w:spacing\b[^>]*/>', fix, ppr)
        else:
            new_ppr = ppr.replace('<w:pPr>', '<w:pPr>' + sp, 1)
        new = frag[:pm.start()] + new_ppr + frag[pm.end():]
    else:
        om = re.match(r'<w:p\b[^>]*?>', frag)
        new = frag[:om.end()] + f'<w:pPr>{sp}</w:pPr>' + frag[om.end():]
    x = x[:m.start()] + new + x[m.end():]
    cnt[rule + line] = cnt.get(rule + line, 0) + 1

# 기본값은 본문용으로 두되, 위에서 모든 문단에 명시했으므로 영향은 작다
ET.fromstring(x)
parts["word/document.xml"] = x.encode()
tmp = DOC + ".new"
with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as o:
    for it in infos: o.writestr(it, parts[it.filename])
shutil.move(tmp, DOC)
import docx; docx.Document(DOC)
for k, v in sorted(cnt.items(), key=lambda a: -a[1]): print(f"  {k:12s} {v:3d}문단")
print("행간 적용 완료")
