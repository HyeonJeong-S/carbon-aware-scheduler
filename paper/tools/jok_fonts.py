# -*- coding: utf-8 -*-
"""CAST_JOK_투고본.docx 의 글꼴·크기를 정보과학회논문지(JOK) 실물에 맞춘다.

크기 출처: 5d 가 JOK e-journal 세 편(108120·108121·108123)을 pymupdf span 단위로
직접 재어 얻었다. 세 편이 소수점까지 수렴한 값들이다.

  국문제목 15.46 · 영문제목 12.58 · 국문저자 9.71 · 절제목 8.75 · 소절제목 7.79(굵게)
  본문 7.79 · 식번호 7.79 · 수식기호 7.56~7.67 · 캡션(한) 7.79 · 캡션(영)·초록·키워드 7.31
  참고문헌 7.19 · 표(숫자) 6.71 · 각주 5.75 · 행간 본문 12.35

** Word 의 제약 ** : <w:sz> 는 반쪽포인트 **정수**라 7.79pt 를 그대로 못 넣는다.
가장 가까운 반쪽포인트로 내린다(7.79→8.0, 7.31→7.5, 7.19→7.0, 6.71→6.5 …).
본문이 0.21pt 커지지만 눈으로는 구별이 안 되고, 반대로 7.5 로 내리면 0.29pt 작아진다.

** 크기가 아니라 내용으로 분류한다. ** 지금 문서는 같은 성격인데 크기가 다른 데가 있다
(소절 "4.4"만 9.0pt, 본문 세 문단이 9.0pt로 박혀 있는 등 옛 편집의 흔적).
크기로 매핑하면 그 불일치가 그대로 옮겨진다.
"""
import re, shutil, zipfile
import xml.etree.ElementTree as ET

DOC = "/Users/jongha/Desktop/GitHub/carbon-aware-scheduler/paper/CAST_JOK_투고본.docx"
PARA = re.compile(r'<w:p\b[^>]*?/>|<w:p\b[^>]*?(?<!/)>.*?</w:p>', re.DOTALL)
TBL = re.compile(r'<w:tbl>.*?</w:tbl>', re.DOTALL)
RUN = re.compile(r'<w:r\b(?:(?!</w:r>).)*?</w:r>', re.DOTALL)
OMATH = re.compile(r'<m:oMath>.*?</m:oMath>', re.DOTALL)
KFONT = "휴먼명조"

BODY, HEAD, SUB = 16, 18, 16          # 8.0 / 9.0 / 8.0(굵게)
TITLE_KO, TITLE_EN, AUTHOR = 31, 25, 19
CAP_KO, CAP_EN, ABSTRACT = 16, 15, 15
REFS, TABLE, MATH = 14, 13, 15
LINE_BODY = 247                        # 12.35pt


def classify(t):
    if re.match(r'^\[\d+\]', t):                         return REFS
    if re.match(r'^(그림|표)\s*\d+\s', t):                return CAP_KO
    if re.match(r'^(Fig\.|Table)\s*\d+\s', t):            return CAP_EN
    if re.match(r'^\d+\.\d+\s', t):                       return SUB
    if re.match(r'^\d+\.\s', t):                          return HEAD
    if t.startswith(("초록", "주제어:", "Abstract", "Keywords:")):  return ABSTRACT
    return None                                           # 본문 — 지정하지 않고 기본값 상속


def set_sz(frag, sz):
    """문단 조각 안의 모든 run 과 문단부호 rPr 에 크기를 박는다. oMath 안은 따로."""
    def fix_rpr(rpr, v):
        rpr = re.sub(r'<w:sz w:val="\d+"\s*/>', '', rpr)
        rpr = re.sub(r'<w:szCs w:val="\d+"\s*/>', '', rpr)
        return rpr.replace('</w:rPr>', f'<w:sz w:val="{v}"/><w:szCs w:val="{v}"/></w:rPr>')
    def do(m, v):
        r = m.group(0)
        if '<w:rPr>' in r or '<w:rPr ' in r:
            rm = re.search(r'<w:rPr\b.*?</w:rPr>', r, re.DOTALL)
            return r[:rm.start()] + fix_rpr(rm.group(0), v) + r[rm.end():]
        om = re.match(r'<w:r\b[^>]*?>', r)
        return r[:om.end()] + f'<w:rPr><w:sz w:val="{v}"/><w:szCs w:val="{v}"/></w:rPr>' + r[om.end():]
    # 수식 안은 MATH 로, 밖은 sz 로
    out, last = [], 0
    for mm in OMATH.finditer(frag):
        out.append(RUN.sub(lambda m: do(m, sz), frag[last:mm.start()]))
        out.append(re.sub(r'<w:sz w:val="\d+"\s*/>', f'<w:sz w:val="{MATH}"/>',
                   re.sub(r'<w:szCs w:val="\d+"\s*/>', f'<w:szCs w:val="{MATH}"/>', mm.group(0))))
        last = mm.end()
    out.append(RUN.sub(lambda m: do(m, sz), frag[last:]))
    return "".join(out)


z = zipfile.ZipFile(DOC)
parts = {i.filename: z.read(i.filename) for i in z.infolist()}
infos = z.infolist(); z.close()

# ── styles.xml: 기본 글꼴·크기·행간 ──
st = parts["word/styles.xml"].decode()
st = st.replace('w:eastAsia="나눔명조"', f'w:eastAsia="{KFONT}"')
st = st.replace('<w:lang w:val="en-US" w:eastAsia="ko-KR" w:bidi="ar-SA"/>',
                f'<w:sz w:val="{BODY}"/><w:szCs w:val="{BODY}"/>'
                '<w:lang w:val="en-US" w:eastAsia="ko-KR" w:bidi="ar-SA"/>', 1)
st = st.replace('<w:spacing w:line="288" w:lineRule="auto"/>',
                f'<w:spacing w:line="{LINE_BODY}" w:lineRule="exact"/>', 1)
parts["word/styles.xml"] = st.encode()

x = parts["word/document.xml"].decode()
x = x.replace('w:eastAsia="나눔명조"', f'w:eastAsia="{KFONT}"')

tbl_spans = [(m.start(), m.end()) for m in TBL.finditer(x)]
def in_table(p):
    return any(s <= p < e for s, e in tbl_spans)

paras = [(m.start(), m.end(), m.group(0)) for m in PARA.finditer(x)]
counts = {}
for s, e, frag in reversed(paras):
    t = re.sub(r"<[^>]+>", "", frag).strip()
    if in_table(s):
        sz = TABLE
    else:
        if not t:
            continue
        sz = classify(t)
        if sz is None:                       # 본문 — 박힌 크기를 지워 기본값을 쓰게 한다
            new = re.sub(r'<w:sz w:val="\d+"\s*/>', '', frag)
            new = re.sub(r'<w:szCs w:val="\d+"\s*/>', '', new)
            for mm in OMATH.finditer(new):
                pass
            # 수식은 지우면 안 되므로 다시 박는다
            new = "".join(
                (re.sub(r'<w:sz w:val="\d+"\s*/>', f'<w:sz w:val="{MATH}"/>', seg) if i % 2 else seg)
                for i, seg in enumerate(re.split(r'(<m:oMath>.*?</m:oMath>)', new, flags=re.DOTALL)))
            x = x[:s] + new + x[e:]
            counts["본문(상속)"] = counts.get("본문(상속)", 0) + 1
            continue
    x = x[:s] + set_sz(frag, sz) + x[e:]
    k = {REFS: "참고문헌", CAP_KO: "캡션(한)", CAP_EN: "캡션(영)", SUB: "소절제목",
         HEAD: "절제목", ABSTRACT: "초록·키워드", TABLE: "표"}[sz]
    counts[k] = counts.get(k, 0) + 1

# 제목·저자는 글자로 찾는다
for pat, sz, nm in ((r'^CAST: 리전 용량', TITLE_KO, "국문제목"),
                    (r'^CAST: Carbon-Aware', TITLE_EN, "영문제목"),
                    (r'^이종하 · ', AUTHOR, "저자"),
                    (r'^단국대학교', AUTHOR, "소속")):
    for s, e, frag in reversed([(m.start(), m.end(), m.group(0)) for m in PARA.finditer(x)]):
        t = re.sub(r"<[^>]+>", "", frag).strip()
        if re.match(pat, t):
            x = x[:s] + set_sz(frag, sz) + x[e:]
            counts[nm] = counts.get(nm, 0) + 1
            break

ET.fromstring(x)
parts["word/document.xml"] = x.encode()
tmp = DOC + ".new"
with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as o:
    for it in infos:
        o.writestr(it, parts[it.filename])
shutil.move(tmp, DOC)
import docx; docx.Document(DOC)
for k, v in sorted(counts.items(), key=lambda a: -a[1]):
    print(f"  {k:12s} {v:3d}문단")
print("글꼴·크기 적용 완료")
