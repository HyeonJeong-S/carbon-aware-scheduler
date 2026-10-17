# -*- coding: utf-8 -*-
"""v2 원고(paper/문서/v2_draft/99_원고.txt) → paper/CAST_JOK_v2.docx. v1 docx(CAST_JOK_v1.docx)의 문단을 서식 틀로 복제한다.
원고 표기: 제목:/Title:/초록:/주제어:/Abstract:/Keywords: · "# 1절" · "## 3.1" · "[그림 N | 파일[, 파일2] | 단폭|전폭]"+캡션 2줄 ·
"[표 N]"+캡션 2줄+행("a | b | c")·빈 줄 · "[식 N]"(omml/eqN.xml) · "[알고리즘 1]"+줄들·빈 줄 · "# 참고문헌"+"[n] …".
틀: 제목부(v1 0~8 요소 그대로, 글만 교체), 절 제목(1. 서론 / 3.1 개요), 본문(서론 첫 단락), 그림(단폭: 그림 2 단락, 전폭: 그림 1 섹션 꼴),
캡션(그림 2/Fig. 2, 표 1/Table 1), 수식((1) 단락), 표(표 1), 알고리즘(Algorithm 1), 참고문헌(제목·[1]).
    ./.venv/bin/python paper/tools/build_v2_docx.py [--in 99_원고.txt] [--out paper/CAST_JOK_v2.docx]
"""
import argparse, copy, os, re, sys
import docx
from docx.shared import Pt
from docx.text.paragraph import Paragraph
from docx.oxml.ns import qn
from lxml import etree

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
V1 = os.path.join(ROOT, "paper", "CAST_JOK_v1.docx")
DRAFT = os.path.join(ROOT, "paper", "문서", "v2_draft")
DIAG = os.path.join(ROOT, "paper", "diagram")
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
M_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"
WIDTH = {"단폭": 195.6, "전폭": 402.0}

# ── 원고 파싱 ──────────────────────────────────────────────────────────────
def parse(path):
    lines = open(path, encoding="utf-8").read().split("\n")
    head, blocks, i = {}, [], 0
    while i < len(lines) and not lines[i].startswith("# "):
        m = re.match(r"^(제목|Title|초록|주제어|Abstract|Keywords):\s*(.*)$", lines[i])
        if m: head[m.group(1)] = m.group(2).strip()
        i += 1
    para = []
    def flush():
        nonlocal para
        if para: blocks.append(("p", " ".join(x.strip() for x in para))); para = []
    while i < len(lines):
        ln = lines[i].rstrip()
        if not ln.strip():
            flush(); i += 1; continue
        if ln.startswith("## "): flush(); blocks.append(("h2", ln[3:].strip())); i += 1; continue
        if ln.startswith("# "):
            flush(); t = ln[2:].strip()
            blocks.append(("refs", []) if t.startswith("참고문헌") else ("h1", t)); i += 1; continue
        m = re.match(r"^\[그림 (\d+)\s*\|\s*([^|]+)\|\s*(단폭|전폭)\s*\]$", ln)
        if m:
            flush(); files = [f.strip() for f in m.group(2).split(",")]
            blocks.append(("fig", dict(n=int(m.group(1)), files=files, width=m.group(3), kr=lines[i+1].strip(), en=lines[i+2].strip()))); i += 3; continue
        m = re.match(r"^\[표 (\d+)(?:\s*\|\s*(단폭|전폭))?\s*\]$", ln)
        if m:
            flush(); kr, en = lines[i+1].strip(), lines[i+2].strip(); i += 3; rows = []
            while i < len(lines) and lines[i].strip():
                rows.append([c.strip() for c in lines[i].split("|")]); i += 1
            blocks.append(("tbl", dict(n=int(m.group(1)), kr=kr, en=en, rows=rows, width=m.group(2) or "단폭"))); continue
        m = re.match(r"^\[식 (\d+)\]$", ln)
        if m: flush(); blocks.append(("eq", int(m.group(1)))); i += 1; continue
        m = re.match(r"^\[알고리즘 (\d+)\]$", ln)
        if m:
            flush(); i += 1; alg = []
            while i < len(lines) and lines[i].strip(): alg.append(lines[i].rstrip()); i += 1
            blocks.append(("alg", alg)); continue
        if blocks and blocks[-1][0] == "refs" and re.match(r"^\[\d+\]", ln):
            blocks[-1][1].append(ln.strip()); i += 1; continue
        para.append(ln); i += 1
    flush()
    return head, blocks

# ── 틀 찾기 ────────────────────────────────────────────────────────────────
def ptext(p): return "".join(t.text or "" for t in p.iter(qn("w:t")))
def find(els, pred, what):
    for e in els:
        if e.tag == qn("w:p") and pred(e): return e
    raise KeyError(what)

def templates(doc):
    els = list(doc.element.body.iterchildren())
    T = dict(
        title_kr=els[0], title_en=els[1], abs_kr=els[5], kw_kr=els[6], abs_en=els[7], kw_en=els[8],
        h1=find(els, lambda e: ptext(e).strip() == "1. 서론", "h1"),
        h2=find(els, lambda e: ptext(e).strip().startswith("3.1 "), "h2"),
        body=find(els, lambda e: ptext(e).startswith("데이터센터가 쓰는 전력이"), "body"),
        cap_kr=find(els, lambda e: ptext(e).startswith("그림 2 "), "cap_kr"),
        cap_en=find(els, lambda e: ptext(e).startswith("Fig. 2 "), "cap_en"),
        tcap_kr=find(els, lambda e: ptext(e).startswith("표 1 "), "tcap_kr"),
        tcap_en=find(els, lambda e: ptext(e).startswith("Table 1 "), "tcap_en"),
        eq=find(els, lambda e: e.find(".//" + qn("m:oMath")) is not None and ptext(e).strip().endswith("(1)"), "eq"),
        alg=find(els, lambda e: ptext(e).startswith("Algorithm 1"), "alg"),
        ref_h=find(els, lambda e: ptext(e).strip() == "참고문헌", "ref_h"),
        ref_item=find(els, lambda e: ptext(e).startswith("[1] "), "ref_item"),
        table=[e for e in els if e.tag == qn("w:tbl")][0],
    )
    # 그림 단락: 그림 2 캡션 바로 앞의 drawing 단락; 전폭(그림 1)은 캡션 Fig. 1 의 sectPr 과 그 앞 단락의 sectPr
    idx = {id(e): i for i, e in enumerate(els)}
    T["figp"] = els[idx[id(T["cap_kr"])] - 1]
    cap1_en = find(els, lambda e: ptext(e).startswith("Fig. 1 "), "cap1_en")
    T["sect_fig"] = cap1_en.find(qn("w:pPr")).find(qn("w:sectPr"))           # 1단(그림) 섹션
    before = els[idx[id(cap1_en)] - 3]                                        # 그림 1 단락 앞 본문 단락(2단 섹션 끝)
    T["sect_body"] = before.find(qn("w:pPr")).find(qn("w:sectPr"))
    assert T["sect_fig"] is not None and T["sect_body"] is not None
    T["figp_full"] = els[idx[id(cap1_en)] - 2]
    T["title_block"] = els[:9]
    return T

# ── 문단 만들기 ────────────────────────────────────────────────────────────
def first_rpr(p):
    r = p.find(qn("w:r"))
    rp = r.find(qn("w:rPr")) if r is not None else None
    return copy.deepcopy(rp) if rp is not None else None

def clear_runs(p, keep_sect=True):
    for ch in list(p):
        if ch.tag == qn("w:pPr"): continue
        p.remove(ch)
    ppr = p.find(qn("w:pPr"))
    if ppr is not None and not keep_sect:
        sp = ppr.find(qn("w:sectPr"))
        if sp is not None: ppr.remove(sp)

def make_run(text, rpr=None, br=False):
    r = etree.SubElement(etree.Element(qn("w:r")), qn("w:t")); r = r.getparent()
    if rpr is not None: r.insert(0, copy.deepcopy(rpr))
    t = r.find(qn("w:t")); t.text = text; t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    if br: etree.SubElement(r, qn("w:br"))
    return r

def para_from(template, text, keep_sect=False):
    p = copy.deepcopy(template); rpr = first_rpr(p); clear_runs(p, keep_sect=keep_sect)
    p.append(make_run(text, rpr)); return p

def lead_para(template, lead, text):
    """초록/Abstract: 첫 run(굵은 머리말)은 두고 나머지를 한 run 으로."""
    p = copy.deepcopy(template); runs = p.findall(qn("w:r"))
    lead_rpr = first_rpr(p); body_rpr = copy.deepcopy(runs[1].find(qn("w:rPr"))) if len(runs) > 1 and runs[1].find(qn("w:rPr")) is not None else None
    clear_runs(p, keep_sect=True)
    p.append(make_run(lead, lead_rpr)); p.append(make_run("  " + text, body_rpr)); return p

def strip_sect(p):
    ppr = p.find(qn("w:pPr")); sp = ppr.find(qn("w:sectPr")) if ppr is not None else None
    if sp is not None: ppr.remove(sp)

def add_sect(p, sect):
    ppr = p.find(qn("w:pPr"))
    if ppr is None: ppr = etree.SubElement(p, qn("w:pPr")); p.insert(0, ppr)
    strip_sect(p); ppr.append(copy.deepcopy(sect))

# ── 그림 ──────────────────────────────────────────────────────────────────
def stack_ab(files):
    """두 png 를 (a)(b) 라벨과 함께 세로로 합친다 → diagram/<a>_ab.png"""
    from PIL import Image, ImageDraw, ImageFont
    ims = [Image.open(os.path.join(DIAG, f + ".png")).convert("RGB") for f in files]
    margin = 110                                         # (a)(b) 라벨 띠 — y축 제목과 안 겹치게(92 지적)
    w = max(im.width for im in ims) + margin; gap = 30
    h = sum(im.height for im in ims) + gap * (len(ims) - 1)
    out = Image.new("RGB", (w, h), "white"); y = 0
    try: font = ImageFont.truetype("/System/Library/Fonts/AppleSDGothicNeo.ttc", 56)
    except Exception: font = ImageFont.load_default()
    for k, im in enumerate(ims):
        out.paste(im, (margin, y)); ImageDraw.Draw(out).text((10, y + 10), f"({'ab'[k]})", fill="black", font=font); y += im.height + gap
    path = os.path.join(DIAG, files[0] + "_ab.png"); out.save(path, dpi=(500, 500)); return path

def figure_elems(T, fig, prev_p):
    files, width = fig["files"], WIDTH[fig["width"]]
    path = stack_ab(files) if len(files) > 1 else os.path.join(DIAG, files[0] + ".png")
    full = fig["width"] == "전폭"
    fp = copy.deepcopy(T["figp_full"] if full else T["figp"]); clear_runs(fp)
    kr = para_from(T["cap_kr"], fig["kr"]); en = para_from(T["cap_en"], fig["en"])
    if full:
        if prev_p is not None: add_sect(prev_p, T["sect_body"])
        add_sect(en, T["sect_fig"])
    return fp, path, width, kr, en

def table_elems(T, tbl, full=False):
    cap_kr = para_from(T["tcap_kr"], tbl["kr"]); cap_en = para_from(T["tcap_en"], tbl["en"])
    t = copy.deepcopy(T["table"]); rows = tbl["rows"]; ncol = max(len(r) for r in rows)
    # 셀 좌우 여백을 2pt 로(기본 5.4pt 는 단 폭 표에서 열을 잡아먹는다 — 10-17 표 2·5 꺾임)
    tblpr = t.find(qn("w:tblPr"))
    for e in tblpr.findall(qn("w:tblLayout")): tblpr.remove(e)
    lay = etree.SubElement(tblpr, qn("w:tblLayout")); lay.set(qn("w:type"), "fixed")   # 지정한 열 폭을 Word 가 그대로 쓰게(자동 맞춤이면 머리 글자가 열을 좌우함)
    for e in tblpr.findall(qn("w:tblCellMar")): tblpr.remove(e)
    mar = etree.SubElement(tblpr, qn("w:tblCellMar"))
    for side in ("left", "right"):
        m = etree.SubElement(mar, qn("w:" + side)); m.set(qn("w:w"), "40"); m.set(qn("w:type"), "dxa")
    grid = t.find(qn("w:tblGrid"))
    for g in list(grid): grid.remove(g)
    total = 8040 if full else 3912                            # 전폭 402pt / 단폭 195.6pt (twips)
    tw = t.find(qn("w:tblPr")).find(qn("w:tblW"))
    if tw is not None: tw.set(qn("w:w"), str(total))
    # 열 폭: 각 열의 가장 긴 칸(한글·한자는 2, 나머지 1)에 비례 — 균등 분할은 긴 머리를 꺾는다(92 지적; v1 표도 비례)
    def dlen(txt): return sum(2 if ("가" <= ch <= "힣" or "\u4e00" <= ch <= "\u9fff") else 1 for ch in txt)
    # 머리 행은 두 줄로 꺾여도 되므로 절반만 세고, 본문 칸은 그대로(머리가 길어 본문 열을 좁히던 표 4 사고)
    # 고정 폭 표라 noWrap 이 안 먹는다 — 본문 가장 긴 칸 + 여유 2, 최소 6
    def hdr_w(c):   # 머리는 두 줄로 꺾여도 되지만 단어 중간에서 꺾이면 안 된다 — 가장 긴 단어 + 1
        h = rows[0][c] if c < len(rows[0]) else ""
        return int(max([dlen(w) for w in h.split()] + [0]) * 1.3) + 2     # 영문 소문자는 숫자보다 넓다 — 1.3배
    wts = [max(8, max(dlen(r[c]) if c < len(r) else 0 for r in rows[1:]) + 4, hdr_w(c)) for c in range(ncol)]
    widths = [int(total * w / sum(wts)) for w in wts]; widths[-1] += total - sum(widths)
    for w in widths: etree.SubElement(grid, qn("w:gridCol")).set(qn("w:w"), str(w))
    # 숫자 열(본문 칸이 전부 숫자·범위·—·⟦ ⟧)만 오른쪽, 글자 열은 왼쪽(92 지적: 표 1 Region)
    NUM = re.compile(r"^[\d.,%/–\-—+()\[\]⟦⟧ ×]*$")
    numeric = [all(NUM.match(r[c]) for r in rows[1:] if c < len(r)) for c in range(ncol)]
    trs = t.findall(qn("w:tr")); head_tr, body_tr = trs[0], trs[1]
    for tr in trs: t.remove(tr)
    for i, row in enumerate(rows):
        tr = copy.deepcopy(head_tr if i == 0 else body_tr); tcs = tr.findall(qn("w:tc"))
        while len(tcs) < ncol: tr.append(copy.deepcopy(tcs[-1])); tcs = tr.findall(qn("w:tc"))
        while len(tcs) > ncol: tr.remove(tcs[-1]); tcs = tr.findall(qn("w:tc"))
        for c, tc in enumerate(tcs):
            tcw = tc.find(qn("w:tcPr")).find(qn("w:tcW")) if tc.find(qn("w:tcPr")) is not None else None
            if tcw is not None: tcw.set(qn("w:w"), str(widths[c])); tcw.set(qn("w:type"), "dxa")
            ps = tc.findall(qn("w:p")); p0 = ps[0]
            for extra in ps[1:]: tc.remove(extra)
            rpr = first_rpr(p0); clear_runs(p0); txt = row[c] if c < len(row) else ""
            if rpr is None: rpr = etree.Element(qn("w:rPr"))
            for e in rpr.findall(qn("w:sz")) + rpr.findall(qn("w:szCs")): rpr.remove(e)
            for tag in ("w:sz", "w:szCs"):                       # 표 글자 6.5pt(v1 머리행과 같게) — 본문 행이 더 커서 꺾이던 것
                e = etree.SubElement(rpr, qn(tag)); e.set(qn("w:val"), "13")
            p0.append(make_run(txt, rpr))
            # 짧은 칸(숫자·한 단어)은 줄바꿈 금지 — "43,8/30" 같은 꺾임 방지
            tcpr = tc.find(qn("w:tcPr"))
            if tcpr is not None:
                for e in tcpr.findall(qn("w:noWrap")): tcpr.remove(e)
                if i > 0 and len(txt) <= 14: etree.SubElement(tcpr, qn("w:noWrap"))     # 본문 짧은 칸("61.57 / 93.96")은 한 줄로
            # 정렬(v1 규칙): 머리 행은 가운데, 본문 행은 첫 열 왼쪽·나머지 오른쪽 — "—"·⟦ ⟧ 칸도 같은 열이면 같게
            ppr = p0.find(qn("w:pPr"))
            if ppr is None: ppr = etree.Element(qn("w:pPr")); p0.insert(0, ppr)
            for e in ppr.findall(qn("w:jc")): ppr.remove(e)
            if i == 0 or (c > 0 and numeric[c]):
                jc = etree.SubElement(ppr, qn("w:jc")); jc.set(qn("w:val"), "center" if i == 0 else "right")
        t.append(tr)
    return cap_kr, cap_en, t

def eq_elem(T, n):
    p = copy.deepcopy(T["eq"]); om = p.find(qn("m:oMath"))
    new = etree.fromstring(open(os.path.join(DRAFT, "omml", f"eq{n}.xml"), encoding="utf-8").read().encode("utf-8"))
    om.getparent().replace(om, new)
    for r in reversed(p.findall(qn("w:r"))):
        t = r.find(qn("w:t"))
        if t is not None and t.text and "(" in t.text: t.text = f"({n})"; break
    return p

def alg_elem(T, lines):
    p = copy.deepcopy(T["alg"]); rpr = first_rpr(p); clear_runs(p)
    for k, ln in enumerate(lines): p.append(make_run(ln, rpr, br=(k < len(lines) - 1)))
    return p

# ── 본문 기호 → 수식 서체 (v1 mathify.py 의 v2 확장: 원고의 a_b / a^b / a_b^c 와 낱글자 변수) ──────
MATH = "Cambria Math"
# 밑(1~3 글자, 모자·물결 결합 포함) + _첨자(1~4 글자) + 선택 ^위첨자( (t) 또는 1~3 글자 )
SYM_RE = re.compile(r"(?<![A-Za-z0-9가-힣_^])([A-Za-zα-ωΑ-Ω℧ℓ][\u0302\u0303\u0304]?|cap|Ĉ|C̃|ℓ̃|λ̃|ẽ|λ̄)"
                    r"(?:_([A-Za-z0-9α-ωΑ-Ωτ]{1,4}))?(?:\^(\([a-z]\)|[A-Za-z0-9α-ω]{1,3}))?(?![A-Za-z0-9_])")   # 뒤에 한글 조사가 바로 붙어도("d_j다") 잡는다
BARE_RE = re.compile(r"(?<![A-Za-z0-9α-ωΑ-Ω._/@%\-])([A-Za-zα-ωΑ-Ω])(?![A-Za-z0-9α-ωΑ-Ω._/@\-])")
UPRIGHT = {"cap", "def", "max", "min"}

def _math_spans(text):
    """(시작, 끝, 밑, 첨자, 위첨자) 목록. 첨자/위첨자 없는 낱글자는 한국어 문장에서만."""
    spans = []
    for m in SYM_RE.finditer(text):
        if m.group(2) is None and m.group(3) is None: continue
        spans.append((m.start(), m.end(), m.group(1), m.group(2) or "", m.group(3) or ""))
    taken = {i for a, b, *_ in spans for i in range(a, b)}
    korean = sum(1 for c in text if "가" <= c <= "힣") / max(1, len(text))
    if korean >= 0.25 and "@" not in text:
        for m in BARE_RE.finditer(text):
            if m.start() not in taken and m.group(1) not in ("a",):
                spans.append((m.start(), m.end(), m.group(1), "", ""))
    return sorted(spans)

def _rpr_math(base_rpr, vert=None, upright=False):
    c = copy.deepcopy(base_rpr) if base_rpr is not None else etree.Element(qn("w:rPr"))
    for e in c.findall(qn("w:rFonts")) + c.findall(qn("w:i")) + c.findall(qn("w:vertAlign")): c.remove(e)
    f = etree.Element(qn("w:rFonts")); f.set(qn("w:ascii"), MATH); f.set(qn("w:hAnsi"), MATH); f.set(qn("w:cs"), MATH); c.insert(0, f)
    if not upright: c.append(etree.Element(qn("w:i")))
    if vert: v = etree.Element(qn("w:vertAlign")); v.set(qn("w:val"), vert); c.append(v)
    return c

def mathify_paragraph(p):
    if p.find(".//" + qn("m:oMath")) is not None or p.find(".//" + qn("w:drawing")) is not None: return 0
    runs = p.findall(qn("w:r"))
    if not runs: return 0
    text = "".join(t.text or "" for t in p.iter(qn("w:t")))
    if text.startswith(("Algorithm", "[", "Fig.", "Table")) or re.match(r"^\[\d+\]", text): return 0
    spans = _math_spans(text)
    if not spans: return 0
    base_rpr = runs[0].find(qn("w:rPr"))
    for r in runs: p.remove(r)
    def add(txt, rpr):
        if txt: p.append(make_run(txt, rpr))
    last = 0
    for a, b, base, sub, sup in spans:
        add(text[last:a], base_rpr)
        add(base, _rpr_math(base_rpr, upright=(base in UPRIGHT)))
        if sub: add(sub, _rpr_math(base_rpr, "subscript", upright=(sub in UPRIGHT)))
        if sup: add(sup.strip("()") if sup.startswith("(") else sup, _rpr_math(base_rpr, "superscript", upright=(sup.strip("()") in UPRIGHT or sup.startswith("("))))
        last = b
    add(text[last:], base_rpr)
    return len(spans)

def mathify_doc(doc):
    n = 0
    for p in doc.element.body.iter(qn("w:p")): n += mathify_paragraph(p)
    return n


# ── 조립 ──────────────────────────────────────────────────────────────────
def build(src, out):
    head, blocks = parse(src)
    doc = docx.Document(V1); T = templates(doc); body = doc.element.body
    final_sect = body.find(qn("w:sectPr"))
    for e in list(body):
        if e is not final_sect: body.remove(e)
    prev_p, pictures = None, []
    def add(e):
        nonlocal prev_p
        body.insert(list(body).index(final_sect), e); prev_p = e if e.tag == qn("w:p") else prev_p
    # 제목부도 마지막 sectPr 앞에 넣어야 한다 — body.append 는 sectPr 뒤에 붙어 문서 끝으로 밀린다(10-17 첫 조립 사고)
    tb = T["title_block"]
    add(para_from(tb[0], head["제목"], keep_sect=True)); add(para_from(tb[1], head["Title"], keep_sect=True))
    for e in tb[2:5]: add(copy.deepcopy(e))
    add(lead_para(tb[5], "초록", head["초록"])); add(para_from(tb[6], "주제어: " + head["주제어"], keep_sect=True))
    add(lead_para(tb[7], "Abstract", head["Abstract"])); add(para_from(tb[8], "Keywords: " + head["Keywords"], keep_sect=True))
    prev_p = None
    for kind, val in blocks:
        if kind == "h1": add(para_from(T["h1"], val))
        elif kind == "h2": add(para_from(T["h2"], val))
        elif kind == "p": add(para_from(T["body"], val))
        elif kind == "eq": add(eq_elem(T, val))
        elif kind == "alg": add(alg_elem(T, val))
        elif kind == "fig":
            fp, path, width, kr, en = figure_elems(T, val, prev_p)
            add(fp); pictures.append((fp, path, width)); add(kr); add(en)
        elif kind == "tbl":
            ncol = max(len(r) for r in val["rows"])
            if ncol >= 5 and val["width"] != "단폭!": val["width"] = "전폭"      # 열 5개 이상은 단 폭에 안 들어간다(10-17) — 자동 전폭
            kr, en, t = table_elems(T, val, full=(val["width"] == "전폭"))
            if val["width"] == "전폭":                      # 전폭 표: 앞 단락에서 2단 섹션을 끝내고, 표 뒤 빈 단락이 1단 섹션을 끝낸다
                if prev_p is not None: add_sect(prev_p, T["sect_body"])
                add(kr); add(en); add(t)
                tail = para_from(T["body"], ""); add_sect(tail, T["sect_fig"]); add(tail)
            else:
                add(kr); add(en); add(t)
        elif kind == "refs":
            add(para_from(T["ref_h"], "참고문헌"))
            for item in val: add(para_from(T["ref_item"], item))
    for fp, path, width in pictures:                       # 그림은 문단이 문서에 붙은 뒤 넣는다(관계 id 때문)
        Paragraph(fp, doc._body).add_run().add_picture(path, width=Pt(width))
    n_math = mathify_doc(doc)
    doc.save(out)
    print(f"본문 기호 {n_math}곳을 수식 서체로")
    n_p = len(body.findall(qn("w:p"))); n_t = len(body.findall(qn("w:tbl")))
    print(f"wrote {out}: 문단 {n_p}, 표 {n_t}, 그림 {len(pictures)}, 식 {sum(1 for k, _ in blocks if k == 'eq')}, 참고문헌 {sum(len(v) for k, v in blocks if k == 'refs')}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--in", dest="src", default=os.path.join(DRAFT, "99_원고.txt"))
    ap.add_argument("--out", default=os.path.join(ROOT, "paper", "CAST_JOK_v2.docx")); a = ap.parse_args(); build(a.src, a.out)
