# -*- coding: utf-8 -*-
"""v2 원고(paper/문서/v2_draft/99_원고.txt) → paper/CAST_JOK_v2.docx. v1 docx(CAST_JOK_v1.docx)의 문단을 서식 틀로 복제한다.
원고 표기: 제목:/Title:/초록:/주제어:/Abstract:/Keywords: · "# 1절" · "## 3.1" · "[그림 N | 파일[, 파일2] | 단폭|전폭]"+캡션 2줄 ·
"[표 N]"+캡션 2줄+행("a | b | c")·빈 줄 · "[식 N]"(omml/eqN.xml) · "[알고리즘 1]"+줄들·빈 줄 · "# 참고문헌"+"[n] …".
틀: 제목부(v1 0~8 요소 그대로, 글만 교체), 절 제목(1. 서론 / 3.1 개요), 본문(서론 첫 단락), 그림(단폭: 그림 2 단락, 전폭: 그림 1 섹션 꼴),
캡션(그림 2/Fig. 2, 표 1/Table 1), 수식((1) 단락), 표(표 1), 알고리즘(Algorithm 1), 참고문헌(제목·[1]).
    ./.venv/bin/python paper/tools/build_v2_docx.py [--in 99_원고.txt] [--out paper/CAST_JOK_v2.docx]
"""
import argparse, copy, os, re, sys, unicodedata
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
            blocks.append(("tbl", dict(n=int(m.group(1)), kr=kr, en=en, rows=rows, width=m.group(2) or "단폭", explicit=bool(m.group(2))))); continue
        m = re.match(r"^\[식 (\d+)([a-z]?)\]$", ln)       # 10-18: (11a)(11b) 처럼 갈래 번호도
        if m: flush(); blocks.append(("eq", int(m.group(1)) if not m.group(2) else m.group(1) + m.group(2))); i += 1; continue
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

CAP_JC = "center"   # 87 [19]: JOK 게재본 캡션은 가운데 정렬. v1 틀은 그림 캡션이 양쪽(문서 기본 jc=both 물려받음), 표 캡션이 양쪽·왼쪽 섞임

def caption(template, text):
    """캡션 단락: 틀 그대로 + 정렬만 CAP_JC. 양쪽 정렬은 짧은 줄에서 낱말 사이가 크게 벌어졌다(19쪽 그림 9 국문 등)."""
    p = no_overflow(para_from(template, text)); ppr = p.find(qn("w:pPr"))
    for e in ppr.findall(qn("w:jc")): ppr.remove(e)
    jc = etree.Element(qn("w:jc")); jc.set(qn("w:val"), CAP_JC)
    anchor = next((ppr.find(qn(t)) for t in ("w:textAlignment", "w:textboxTightWrap", "w:outlineLvl", "w:divId", "w:cnfStyle", "w:rPr", "w:sectPr", "w:pPrChange") if ppr.find(qn(t)) is not None), None)
    (anchor.addprevious(jc) if anchor is not None else ppr.append(jc))
    return p

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
    kr = caption(T["cap_kr"], fig["kr"]); en = caption(T["cap_en"], fig["en"])
    if full:
        if prev_p is not None: add_sect(prev_p, T["sect_body"])
        add_sect(en, T["sect_fig"])
    return fp, path, width, kr, en

TBL_SZ = 14       # 7pt. Word 글자 크기는 0.5pt 단위라 6.7 은 못 쓴다. JOK 실측 본문 7.79/캡션 7.31 이 명목 8/7.5pt 의 0.974배이므로
                  # 실측 6.71pt 표는 명목 6.89pt → 7pt 가 가깝다(우리 PDF 는 명목의 0.99배로 찍혀 7pt → 약 6.93pt)

def _dlen(txt): return sum(2 if ("가" <= ch <= "힣" or "\u4e00" <= ch <= "\u9fff") else 1 for ch in txt)

def table_fits_column(rows):
    """단폭(195.6pt)에 들어가는지 글자 폭으로 어림한다(89 [13]: 열 5개 이상이면 무조건 전폭이던 규칙을 바꿈).
    본문 칸은 가장 긴 칸, 머리는 두 줄로 꺾여도 되므로 가장 긴 낱말. 7pt Times 한 글자 평균 3.6pt, 칸 여백·열 사이 6pt."""
    ncol = max(len(r) for r in rows); need = 0.0
    for c in range(ncol):
        body = max([_dlen(r[c]) for r in rows[1:] if c < len(r)] + [0])
        head = max([_dlen(w) for w in (rows[0][c] if c < len(rows[0]) else "").split()] + [0])
        need += max(body, head) * 3.6 * TBL_SZ / 14 + 6
    return need <= 195.6 - 4, need

# 표 머리 이름 맞춤(84 [12] 가): 같은 양을 표 4 는 "Lat. (ms)", 표 7 은 "Latency (ms)" 로 썼다 — 조립에서 짧은 쪽으로
HEAD_RENAME = {"Latency (ms)": "Lat. (ms)"}
HEAD_VAR_RE = re.compile(r"(?<![A-Za-z0-9.\-])([A-Za-z])(?![A-Za-z.])")    # 표 머리의 라틴 낱글자 변수(표 2 "k", "Median d") — 본문·캡션처럼 기울임(84 [12] 나)
# 82 [7]: 숫자·붙임표 바로 뒤 글자는 단위·이름의 일부("SN-24h" 의 h)라 변수가 아니다 — 전에는 h 가 수식 이탤릭으로 찍혔다
RULE_TOP, RULE_MID = 12, 6        # 위·아래 굵은 선 1.5pt, 머리 아래 가는 선 0.75pt(v1 표 틀과 같은 굵기)
LAST_PAD = 20                     # 마지막 행 아래 안쪽 여백 1pt(+ 선 행 0.5pt = 1.5pt) — 내림 글자(g·y·p)가 아래 선에 0.5pt 로 붙었다(84 [14])

def rule_row(ncol, total, side, sz, h=20):
    """표 전체 폭 한 칸(gridSpan)짜리 얇은 행에 선 하나. 84 [14]: 표 테두리(tblBorders)·칸 테두리 모두 Word(Mac) PDF 에서
    칸마다 따로 그어져 칸 경계에서 선 굵기만큼(1.44pt·0.72pt) 끊겼다. 한 칸이면 한 줄로 그어진다. 높이 h(twips, 정확히).
    주의: 선이 놓인 가장자리 건너편에 여러 칸짜리 행이 닿으면 Word 는 그 칸들 경계마다 다시 끊는다(시험에서 확인).
    그래서 위 선은 맨 윗행의 top, 아래 선은 맨 아랫행의 bottom, 가운데 선은 한 칸 행 둘 사이(rule_rows_mid)에 긋는다."""
    tr = _el("w:tr"); trpr = _el("w:trPr", tr); _el("w:cantSplit", trpr); _el("w:trHeight", trpr, val=h, hRule="exact")
    tc = _el("w:tc", tr); tcpr = _el("w:tcPr", tc); _el("w:tcW", tcpr, w=total, type="dxa"); _el("w:gridSpan", tcpr, val=ncol)
    _el("w:" + side, _el("w:tcBorders", tcpr), val="single", sz=sz, space=0, color="000000")
    p = _el("w:p", tc); ppr = _el("w:pPr", p); _el("w:keepNext", ppr)
    _el("w:spacing", ppr, before=0, after=0, line=h, lineRule="exact")
    rp = _el("w:rPr", ppr); _el("w:sz", rp, val=2); _el("w:szCs", rp, val=2)
    return tr

def rule_rows_mid(ncol, total, sz):
    """머리 아래 가는 선: 한 칸 행 둘(위 빈 행 0.5pt + 아래 행 top 선) — 선의 양쪽이 모두 한 칸이라 끊기지 않는다."""
    a = rule_row(ncol, total, "top", sz, h=10)
    tb = a.find(".//" + qn("w:tcBorders")); tb.getparent().remove(tb)
    return [a, rule_row(ncol, total, "top", sz, h=10)]

def table_elems(T, tbl, full=False):
    cap_kr = caption(T["tcap_kr"], tbl["kr"]); cap_en = caption(T["tcap_en"], tbl["en"])
    t = copy.deepcopy(T["table"]); rows = [list(r) for r in tbl["rows"]]; ncol = max(len(r) for r in rows)
    rows[0] = [HEAD_RENAME.get(h, h) for h in rows[0]]
    # 셀 좌우 여백을 2pt 로(기본 5.4pt 는 단 폭 표에서 열을 잡아먹는다 — 10-17 표 2·5 꺾임)
    tblpr = t.find(qn("w:tblPr"))
    for e in tblpr.findall(qn("w:tblLayout")): tblpr.remove(e)
    lay = etree.SubElement(tblpr, qn("w:tblLayout")); lay.set(qn("w:type"), "fixed")   # 지정한 열 폭을 Word 가 그대로 쓰게(자동 맞춤이면 머리 글자가 열을 좌우함)
    for e in tblpr.findall(qn("w:tblBorders")): tblpr.remove(e)   # 선은 rule_row 로(84 [14]). 틀의 tblBorders 위·아래는 칸마다 끊겼다
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
    # 넉넉한 표(어림 폭이 표 폭 안): 열마다 필요한 폭을 먼저 주고 남는 폭을 고르게 나눈다 — 비례 배분은 긴 글자 열(Region)에
    # 폭을 몰아 주고 짧은 숫자 열 머리("Start")를 꺾었다(단폭으로 바꾼 표 1, 7pt)
    need = [20 * (max(max([_dlen(r[c]) for r in rows[1:] if c < len(r)] + [0]) * 3.6,
                      max([_dlen(w) for w in (rows[0][c] if c < len(rows[0]) else "").split()] + [0]) * 3.6 * 1.2) * TBL_SZ / 14 + 6)
            for c in range(ncol)]
    if sum(need) <= total:
        extra = (total - sum(need)) / ncol
        widths = [int(x + extra) for x in need]; widths[-1] += total - sum(widths)
    for w in widths: etree.SubElement(grid, qn("w:gridCol")).set(qn("w:w"), str(w))
    # 숫자 열(본문 칸이 전부 숫자·범위·—·⟦ ⟧)만 오른쪽, 글자 열은 왼쪽(92 지적: 표 1 Region)
    # 음수 기호 −(U+2212)와 신뢰구간의 "to"도 숫자 열로 — 표 6 의 Δ·CI 두 열만 왼쪽 정렬이던 것(87 [18])
    NUM = re.compile(r"^(?:[\d.,%/–\-−—+()\[\]⟦⟧ ×]|to)*$")
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
            for tag in ("w:sz", "w:szCs"):                       # 표 글자 TBL_SZ(89 [13][25]: JOK 숫자표 실측 6.71pt)
                e = etree.SubElement(rpr, qn(tag)); e.set(qn("w:val"), str(TBL_SZ))
            if i == 0 and HEAD_VAR_RE.search(txt):               # 머리의 k, d → 수식 이탤릭(굵기는 머리 그대로)
                spans = [(m.start(), m.end(), m.group(1), "", "") for m in HEAD_VAR_RE.finditer(txt)]
                for r in math_runs(txt, rpr, spans=spans): p0.append(r)
            else:
                p0.append(make_run(txt, rpr))
            # 짧은 칸(숫자·한 단어)은 줄바꿈 금지 — "43,8/30" 같은 꺾임 방지
            tcpr = tc.find(qn("w:tcPr"))
            if tcpr is not None:
                for e in tcpr.findall(qn("w:noWrap")) + tcpr.findall(qn("w:tcBorders")) + tcpr.findall(qn("w:tcMar")): tcpr.remove(e)
                add_ = []
                if i > 0 and len(txt) <= 14: add_.append(_el("w:noWrap"))         # 본문 짧은 칸("61.57 / 93.96")은 한 줄로
                if i == len(rows) - 1:                           # 마지막 행 아래 여백(84 [14])
                    tm = _el("w:tcMar"); _el("w:bottom", tm, w=LAST_PAD, type="dxa"); add_.append(tm)
                va = tcpr.find(qn("w:vAlign"))                   # 스키마 순서: tcW, gridSpan, tcBorders, shd, noWrap, tcMar, …, vAlign
                for e in add_: (va.addprevious(e) if va is not None else tcpr.append(e))
            # 정렬: 머리 행도 그 열의 데이터와 같게(89 [15]: 가운데 머리가 열 위에 안 놓이던 것) — 글자 열 왼쪽, 숫자 열 오른쪽
            ppr = p0.find(qn("w:pPr"))
            if ppr is None: ppr = etree.Element(qn("w:pPr")); p0.insert(0, ppr)
            for e in ppr.findall(qn("w:jc")) + ppr.findall(qn("w:ind")): ppr.remove(e)
            ind = etree.Element(qn("w:ind")); ind.set(qn("w:firstLine"), "0")   # 문서 기본 첫 줄 들여쓰기 10pt 가 칸마다 먹혀 "0./9"처럼 꺾였다
            sp = ppr.find(qn("w:spacing"))
            (sp.addnext(ind) if sp is not None else ppr.append(ind))
            if c > 0 and numeric[c]:
                jc = etree.SubElement(ppr, qn("w:jc")); jc.set(qn("w:val"), "right")
        if i == 0: t.append(rule_row(ncol, total, "top", RULE_TOP))           # 위 굵은 선(맨 윗행의 top)
        t.append(tr)
        if i == 0:                                                            # 머리 아래 가는 선(전에는 머리 칸마다 tcBorders)
            for x in rule_rows_mid(ncol, total, RULE_MID): t.append(x)
    for x in rule_rows_mid(ncol, total, RULE_TOP): t.append(x)              # 아래 굵은 선: 마지막 행 여백 LAST_PAD + 0.5pt 밑. 맨 아랫행 bottom 으로 그으면 왼쪽 끝이 0.7pt 삐져나왔다
    return cap_kr, cap_en, t

def eq_elem(T, n):
    p = copy.deepcopy(T["eq"]); om = p.find(qn("m:oMath"))
    new = etree.fromstring(open(os.path.join(DRAFT, "omml", f"eq{n}.xml"), encoding="utf-8").read().encode("utf-8"))
    om.getparent().replace(om, new)
    for r in reversed(p.findall(qn("w:r"))):
        t = r.find(qn("w:t"))
        if t is not None and t.text and "(" in t.text:
            t.text = f"({n})"; rp = r.find(qn("w:rPr"))
            if rp is not None:                                   # 식 번호는 바른 글꼴(89 [24]: JOK 실측 본문과 같은 바른 글꼴)
                for e in rp.findall(qn("w:i")) + rp.findall(qn("w:iCs")): rp.remove(e)
            break
    ppr = p.find(qn("w:pPr")); prp = ppr.find(qn("w:rPr")) if ppr is not None else None
    if prp is not None:
        for e in prp.findall(qn("w:i")) + prp.findall(qn("w:iCs")): prp.remove(e)
    if new.find(".//" + qn("m:f")) is not None: return eq_display(p, new, n)
    # 번호 앞 탭을 오른쪽 끝 절대 탭(ptab)으로: 두 줄 식의 둘째 줄이 가운데 탭보다 짧으면 번호가 가운데 탭에 붙었다(89 [7] 식 12)
    runs = p.findall(qn("w:r"))
    for r in runs[1:]:
        tab = r.find(qn("w:tab"))
        if tab is not None:
            pt = etree.Element(qn("w:ptab")); pt.set(qn("w:relativeTo"), "margin"); pt.set(qn("w:alignment"), "right"); pt.set(qn("w:leader"), "none")
            r.replace(tab, pt)
    if new.find(".//" + qn("w:br")) is not None:             # 두 줄 식: 둘째 줄을 들여 이어지는 줄로 보이게
        ind = ppr.find(qn("w:ind"))
        if ind is None: ind = etree.SubElement(ppr, qn("w:ind"))
        ind.set(qn("w:left"), str(EQ_BR_INDENT.get(n, 560)))
    return p

EQ_BR_INDENT = {12: 1100}     # 둘째 줄 들여쓰기(twips). 식 12 는 첫 줄이 짧아 가운데에 놓이므로 둘째 줄을 더 들인다

def eq_display(p, om, n):
    """분수가 든 식: 글줄 수식이면 Word 가 분수를 글줄 크기(분자·분모 5.5pt)로 줄인다(89 [24] 식 (8)).
    디스플레이 수식(m:oMathPara) + 식 배열의 '#(n)' 번호(Word 식 번호 규약)로 바꾼다. 번호는 본문 글꼴(Times, 바른 글꼴)."""
    ppr = p.find(qn("w:pPr"))
    for ch in list(p):
        if ch is not ppr: p.remove(ch)
    tabs = ppr.find(qn("w:tabs"))
    if tabs is not None: ppr.remove(tabs)
    para = etree.SubElement(p, qn("m:oMathPara")); om2 = etree.SubElement(para, qn("m:oMath"))
    ea = etree.SubElement(om2, qn("m:eqArr")); eapr = etree.SubElement(ea, qn("m:eqArrPr"))
    etree.SubElement(eapr, qn("m:maxDist")).set(qn("m:val"), "1")
    e = etree.SubElement(ea, qn("m:e"))
    for ch in list(om): e.append(ch)
    def txt_run(t):
        r = etree.SubElement(e, qn("m:r")); mr = etree.SubElement(r, qn("m:rPr")); etree.SubElement(mr, qn("m:nor"))
        wr = etree.SubElement(r, qn("w:rPr")); f = etree.SubElement(wr, qn("w:rFonts"))
        for a in ("ascii", "hAnsi", "cs"): f.set(qn("w:" + a), "Times New Roman")
        etree.SubElement(r, qn("m:t")).text = t
    r = etree.SubElement(e, qn("m:r")); etree.SubElement(r, qn("m:t")).text = "#"
    txt_run(f"({n})")
    return p

ALG_SZ = 14        # 7pt — 표 글자(TBL_SZ)와 같다. 7.5pt 에서는 10·11행이 단폭을 넘어 "← x^α*", "α*" 만 다음 줄로 갈렸다(87 [16])
ALG_W = 3912       # 단폭 195.6pt(twips)
# 국문 제목: v1 알고리즘 제목 꼴("Algorithm 1  제목", 상자 첫 줄)을 국문에도 — 그림·표가 국·영문 두 줄 캡션인 것과 맞춘다(87 [16]).
# 원고에 "알고리즘 N  …" 줄이 있으면 그것을 쓰고, 없으면 아래 이름을 쓴다.
ALG_KR = {1: "결합 롤링 배정"}
CAP_SZ_KR, CAP_SZ_EN, CAP_LINE = 16, 15, 233     # 캡션 틀(v1 그림 2/Fig. 2)과 같은 값: 국문 8pt(문서 기본), 영문 7.5pt, 줄 11.65pt 고정
# 알고리즘 상자 띄우기(84 [3]): "bottom" 이면 매인 단락(상자 바로 뒤 단락)이 놓인 단의 아래 끝, "top" 이면 단 위. None 이면 줄 안(전처럼).
ALG_FLOAT = "bottom"

def _el(tag, parent=None, **attrs):
    e = etree.SubElement(parent, qn(tag)) if parent is not None else etree.Element(qn(tag))
    for k, v in attrs.items(): e.set(qn("w:" + k), str(v))
    return e

def no_overflow(p):
    """문장부호 내밀기(overflowPunct)를 끈다. Word 는 줄 첫머리 금지 글자(%, 닫는 괄호, 마침표)를 단 오른쪽 여백으로
    내밀어 찍는데, '61.57%' 줄이 단 경계를 4.6pt 넘었다(89 [23]). 끄면 그 글자를 앞 말과 함께 다음 줄로 넘긴다."""
    ppr = p.find(qn("w:pPr"))
    if ppr is None: ppr = etree.Element(qn("w:pPr")); p.insert(0, ppr)
    for e in ppr.findall(qn("w:overflowPunct")): ppr.remove(e)
    e = etree.Element(qn("w:overflowPunct")); e.set(qn("w:val"), "0")
    # 스키마 순서: keepNext … autoSpaceDN, bidi, adjustRightInd, snapToGrid, spacing … 의 앞쪽(kinsoku·wordWrap·overflowPunct 는 pBdr·shd·tabs 뒤)
    anchor = None
    for tag in ("w:topLinePunct", "w:autoSpaceDE", "w:autoSpaceDN", "w:bidi", "w:adjustRightInd", "w:snapToGrid", "w:spacing", "w:ind", "w:jc", "w:rPr", "w:sectPr"):
        anchor = ppr.find(qn(tag))
        if anchor is not None: break
    if anchor is not None: anchor.addprevious(e)
    else: ppr.append(e)
    return p

FLOAT_FIGS = True     # 10-18 실측: 단 바닥 빈 곳 합 약 1,465pt → 약 750pt (줄 안 그림 대비)

def float_top(*ps):
    """단폭 그림(그림 문단 + 캡션 두 줄)을 하나의 틀(frame)로 묶어 단 위에 띄운다(89 [6][22]).
    줄 안 그림은 그 자리에 못 들어가면 다음 단으로 통째로 넘어가 앞 단 아래가 비었다(19쪽 왼쪽 단 410pt 등).
    같은 framePr 을 가진 이웃 문단은 Word 가 한 틀로 묶는다. 위치는 그 단의 본문 위쪽, 본문은 틀 아래로 흐른다."""
    for p in ps:
        ppr = p.find(qn("w:pPr"))
        if ppr is None: ppr = etree.Element(qn("w:pPr")); p.insert(0, ppr)
        for e in ppr.findall(qn("w:framePr")): ppr.remove(e)
        fr = etree.Element(qn("w:framePr"))
        for k, v in (("w", ALG_W), ("vSpace", 200), ("wrap", "around"), ("vAnchor", "margin"), ("hAnchor", "text"), ("xAlign", "left"), ("yAlign", "top")):
            fr.set(qn("w:" + k), str(v))
        anchor = None                                         # 스키마 순서: pStyle, keepNext, keepLines, pageBreakBefore, framePr, …
        for tag in ("w:widowControl", "w:numPr", "w:suppressLineNumbers", "w:pBdr", "w:shd", "w:tabs", "w:suppressAutoHyphens", "w:kinsoku", "w:wordWrap",
                    "w:overflowPunct", "w:topLinePunct", "w:autoSpaceDE", "w:autoSpaceDN", "w:bidi", "w:adjustRightInd", "w:snapToGrid", "w:spacing", "w:ind", "w:jc", "w:rPr"):
            anchor = ppr.find(qn(tag))
            if anchor is not None: break
        if anchor is not None: anchor.addprevious(fr)
        else: ppr.append(fr)

FLOAT_ALL = True     # 87 [4][5][6][7]: 그림·표를 모두 같은 방식(띄운 바깥 표)으로. 단폭은 단 위, 전폭은 쪽 위.

def float_box(children, full=False):
    """그림(그림 단락 + 캡션 두 줄) 또는 표(캡션 두 줄 + 표)를 한 칸짜리 바깥 표에 넣고 그 바깥 표를 띄운다(tblpPr).
    - framePr(88 회차의 그림 틀)는 표를 품지 못해 표 캡션과 표를 한 틀로 못 묶었고, 틀과 띄운 표는 서로 피하지 않아 겹쳤다
      (12쪽 전폭 표 3 위에 그림 5 틀이 겹침). 그림도 같은 바깥 표로 띄우면 tblOverlap=never 로 서로 비켜 쌓인다.
    - 단폭: 그 단의 본문 위(가로 기준 = 단). 전폭: 쪽 본문 위(가로 기준 = 여백, 가운데) — 두 단이 모두 그 아래로 흐른다.
      섹션 나누기로 만든 전폭 표는 쪽 가운데에 끼어 위 본문이 왼쪽→오른쪽→표 아래 왼쪽으로 읽혔다(87 [7]).
    - 띄운 표는 바로 뒤 단락에 매인다. 그 단락이 놓인 단(전폭은 쪽)의 위로 간다."""
    W = 8040 if full else ALG_W
    tbl = _el("w:tbl"); pr = _el("w:tblPr", tbl)
    _el("w:tblpPr", pr, leftFromText=0, rightFromText=0, topFromText=0, bottomFromText=FLOAT_GAP,
        vertAnchor="margin", horzAnchor=("margin" if full else "text"), tblpXSpec=("center" if full else "left"), tblpYSpec="top")
    _el("w:tblOverlap", pr, val="never")
    _el("w:tblW", pr, w=W, type="dxa")
    b = _el("w:tblBorders", pr)
    for side in ("top", "left", "bottom", "right", "insideH", "insideV"): _el("w:" + side, b, val="nil")
    _el("w:tblLayout", pr, type="fixed")
    mar = _el("w:tblCellMar", pr)
    for side in ("top", "left", "bottom", "right"): _el("w:" + side, mar, w=0, type="dxa")
    _el("w:tblLook", pr, val="0000")
    _el("w:gridCol", _el("w:tblGrid", tbl), w=W)
    tr = _el("w:tr", tbl); _el("w:cantSplit", _el("w:trPr", tr))
    tc = _el("w:tc", tr); _el("w:tcW", _el("w:tcPr", tc), w=W, type="dxa")
    for k, c in enumerate(children):
        ppr = c.find(qn("w:pPr")) if c.tag == qn("w:p") else None
        if ppr is not None:
            for e in ppr.findall(qn("w:framePr")): ppr.remove(e)
            sp = ppr.find(qn("w:spacing"))
            if sp is not None and k == 0: sp.set(qn("w:before"), "0")                    # 틀 맨 위 — 단 머리에서 빈 곳일 뿐
            if sp is not None and k == len(children) - 1: sp.set(qn("w:after"), "0")     # 틀 아래 여백은 bottomFromText 로
        tc.append(c)
    end = _el("w:p", tc); ppr = _el("w:pPr", end)                 # 칸은 단락으로 끝나야 한다 — 높이 1pt
    _el("w:spacing", ppr, before=0, after=0, line=20, lineRule="exact")
    rp = _el("w:rPr", ppr); _el("w:sz", rp, val=2); _el("w:szCs", rp, val=2)
    return tbl

FLOAT_GAP = 220       # 띄운 그림·표와 아래 본문 사이 11pt(v1 그림 캡션 아래 12pt 와 비슷하게)

# 띄운 그림·표의 자리 옮김: 원고 위치에서 본문 단락 n개 앞(−)·뒤(+)로. Word 는 띄운 것을 뒤로 미뤄 두지 못해서,
# 매인 단락이 단 아래에 놓여 그림이 그 단에 안 들어가면 단락째 다음 단으로 넘어가 앞 단 아래가 빈다(87 [4][5][6]).
# 그 단락보다 한두 단락 앞에 매면 그림이 그 단 위로 가고 본문이 아래를 채운다. 값은 조판 결과를 보고 정한다(--shift 로 시험).
# 10-18 2회차 값(그때 원고 기준). 원고가 바뀌면 다시 맞춘다: 조립 → export_pdf → --report 로 단 아래 빈 곳과 그림·표 자리를 보고
# --shift 로 시험. 요령: 단폭 그림이 다음 단 머리로 넘어가 앞 단 아래가 비면 그 그림을 −1, −2.
# 전폭 표는 매인 단락이 오른쪽 단에 놓이면 그 쪽 위에 못 가고 다음 쪽으로 단락째 넘어가므로, 매인 단락이 왼쪽 단에 오도록 앞(−)이나 뒤(+)로.
# 절 제목 바로 뒤에는 두지 말 것(제목의 '다음 문단과 함께'가 띄운 표에 걸려 제목만 다음 쪽으로 감).
# 알고리즘 1 −2(84 [3], 10-18 3회차): 상자를 단 아래 끝에 띄우는데(ALG_FLOAT), 매인 단락의 첫 줄 + 상자가 그 단 남은 자리에
# 안 들어가면 단락째 다음 단으로 넘어가 앞 단 아래가 빈다(원래 자리·−1 은 원고 판에 따라 8쪽 오른쪽 단 아래 172pt 가 비었다).
# 두 단락 앞에 매면 3회차판·10:55 판·10:59 판 원고 셋 모두 8쪽 오른쪽 단 아래 끝에 놓였다. (4회차에 0 으로 되돌림 — 아래 주석)
# 10-18 4회차(82 [3]): 13:25 원고로 다시 맞춤 — 알고리즘 −2→0, 표 3 −3→0, 표 4 0→+1. 13:25 원고에서 단 아래 40pt 넘는 빈 곳 0.
#   알고리즘 0 은 4회차판·13:25 원고 둘 다에서 8쪽 오른쪽 단을 채웠다(−2 는 4회차판 8쪽 R 123pt, −3 은 13:25 원고 170pt).
#   표 3·4 값은 원고 판마다 결과가 크게 갈린다(같은 값이 4회차판에서는 12쪽 R 191pt·18쪽 R 211pt) — 원고가 멈춘 뒤 다시 맞출 것.
FLOAT_SHIFT = {("tbl", 3): 0, ("tbl", 4): 1, ("tbl", 6): -1, ("fig", 9): -1, ("alg", 1): 0, ("fig", 5): -1, ("fig", 8): 4}   # fig5 +1(10-18): 표 4 와 같은 자리에 겹쳤다  # fig8 +4(10-18 5회차판): 표 6(전폭)과 겹침

def apply_shift(blocks, shift):
    """("fig"|"tbl", 번호) → n. 그림·표가 아닌 블록(단락·절 제목·식) n개를 건너 앞(−)·뒤(+)로 옮긴다."""
    out = list(blocks)
    for (kind, n), d in shift.items():
        i = next((k for k, (kk, v) in enumerate(out) if kk == kind and (kind == "alg" or v["n"] == n)), None)   # 알고리즘은 하나뿐(번호 없이 1)
        if i is None or not d: continue
        item = out.pop(i); j = i; cnt = 0
        while cnt < abs(d) and (j > 0 if d < 0 else j < len(out)):
            if d < 0: j -= 1; cnt += out[j][0] not in ("fig", "tbl", "alg")
            else: cnt += out[j][0] not in ("fig", "tbl", "alg"); j += 1
        out.insert(j, item)
    return out

def spacer(keep=False, h=80):
    p = _el("w:p"); ppr = _el("w:pPr", p)
    if keep: _el("w:keepNext", ppr)
    _el("w:spacing", ppr, before=0, after=0, line=h, lineRule="exact")
    rp = _el("w:rPr", ppr); _el("w:sz", rp, val=4); _el("w:szCs", rp, val=4)
    return p

# 82 [20]: 절 제목·참고문헌 제목의 한글은 v1 틀이 "Apple SD Gothic Neo"(굵게)로 지정 — 맥에만 있는 글꼴이라 다른 환경에서는
# 대체 글꼴(fontTable altName 맑은 고딕)로 바뀌어 줄바꿈이 달라질 수 있다. 본문 한글 휴먼명조는 레귤러 한 벌뿐(굵은 꼴 없음)이고,
# JOK 실물도 절 제목은 고딕 굵은체라 명조로 바꾸면 안 된다. 맥 Word(번들 malgun/malgunbd)·윈도에 모두 있는 맑은 고딕(굵은 꼴 있음)으로.
HEAD_KR_FONT = "맑은 고딕"
def head_font(doc):
    n = 0
    for f in doc.element.body.iter(qn("w:rFonts")):
        if f.get(qn("w:eastAsia")) == "Apple SD Gothic Neo": f.set(qn("w:eastAsia"), HEAD_KR_FONT); n += 1
    return n

def keep_next_only(p, keep=True):
    """84 [4]: \uc808 \uc81c\ubaa9\uc740 '\ub2e4\uc74c \ub2e8\ub77d\uacfc \ud568\uaed8'\ub9cc \ub450\uace0 '\uc55e\uc5d0\uc11c \ucabd \ub098\ub214'\u00b7'\uc904 \ud568\uaed8'\ub294 \ub048\ub2e4. \ubcf8\ubb38 \ub2e8\ub77d(keep=False)\uc740 \ub458 \ub2e4 \ub048\ub2e4.
    v1 \ud2c0\uc5d0\ub294 \uc6d0\ub798 \ub458 \ub2e4 \uc5c6\ub2e4(\uc81c\ubaa9 keepNext \ubfd0) \u2014 \ud2c0\uc774 \ubc14\ub00c\uc5b4\ub3c4 \ub07c\uc5b4\ub4e4\uc9c0 \uc54a\uac8c \uc870\ub9bd\uc5d0\uc11c \uc9c0\uc6b4\ub2e4."""
    ppr = p.find(qn("w:pPr"))
    if ppr is None: return p
    for tag in ("w:pageBreakBefore", "w:keepLines"):
        for e in ppr.findall(qn(tag)): ppr.remove(e)
    if keep and ppr.find(qn("w:keepNext")) is None:
        e = etree.Element(qn("w:keepNext")); ps = ppr.find(qn("w:pStyle"))
        (ps.addnext(e) if ps is not None else ppr.insert(0, e))
    return p

ZWSP = "\u200b"
def break_after_slash(txt):
    """84 [18]: "(\ucd5c\ub313\uac12\u2212\ucd5c\uc19f\uac12)/\uc77c\ud3c9\uade0" \uc740 \ub04a\uc744 \uacf3\uc774 \uc5c6\uc5b4 \ud1b5\uc9f8\ub85c \ub2e4\uc74c \uc904\ub85c \uac00\uace0 \uc55e \uc904 \ub0b1\ub9d0 \uc0ac\uc774\uac00 \ubc8c\uc5b4\uc84c\ub2e4.
    '/' \ub4a4\uc5d0 \ud55c\uae00\uc774 \ubc14\ub85c \uc624\uba74 \ud3ed \uc5c6\ub294 \ub04a\uae40(ZWSP)\uc744 \ub123\uc5b4 '/' \ub4a4\uc5d0\uc11c \uc904\uc774 \ubc14\ub014 \uc218 \uc788\uac8c \ud55c\ub2e4(\uc6d0\uace0\ub294 \uadf8\ub300\ub85c)."""
    return re.sub(r"/(?=[\uac00-\ud7a3])", "/" + ZWSP, txt)

NBSP = "\u00a0"
def alg_keep(txt):
    """대입 하나가 두 줄로 갈리지 않게(87 [16]): '; '로 나뉜 문장 가운데 짧은 것(16자 이하, 예: "Q ← Q ∖ {j}")은
    낱말 사이를 줄 나눔 없는 공백으로 묶는다. 줄은 '; ' 뒤에서 바뀐다."""
    parts = txt.split("; ")
    return "; ".join(x.replace(" ", NBSP) if len(x) <= 16 else x for x in parts)

def alg_elem(T, lines):
    """알고리즘 → 한 칸짜리 표(위·아래 괘선, v1 Algorithm 1 상자와 같은 1pt 선). 89 [5]:
    원문 기호를 수식 서체로, 줄마다 단락(넘어가는 줄은 내어쓰기), 왼쪽 정렬, 행 나눔 금지 + 다음 문단과 함께."""
    tbl = _el("w:tbl"); pr = _el("w:tblPr", tbl)
    if ALG_FLOAT:                                            # 84 [3]: 단 아래 끝에 띄운다(그림·표가 단 위·아래에 놓이는 규칙). 위 본문과 11pt
        _el("w:tblpPr", pr, leftFromText=0, rightFromText=0, topFromText=FLOAT_GAP, bottomFromText=0,
            vertAnchor="margin", horzAnchor="text", tblpXSpec="left", tblpYSpec=ALG_FLOAT)
        _el("w:tblOverlap", pr, val="never")
    _el("w:tblW", pr, w=ALG_W, type="dxa"); _el("w:jc", pr, val="left")
    b = _el("w:tblBorders", pr)
    for side in ("top", "bottom"): _el("w:" + side, b, val="single", sz=8, space=0, color="000000")
    _el("w:tblLayout", pr, type="fixed")
    mar = _el("w:tblCellMar", pr)
    for side, w in (("top", 50), ("left", 20), ("bottom", 50), ("right", 20)): _el("w:" + side, mar, w=w, type="dxa")
    _el("w:tblLook", pr, val="0000")
    _el("w:gridCol", _el("w:tblGrid", tbl), w=ALG_W)
    tr = _el("w:tr", tbl); _el("w:cantSplit", _el("w:trPr", tr))
    tc = _el("w:tc", tr); _el("w:tcW", _el("w:tcPr", tc), w=ALG_W, type="dxa")
    base = _el("w:rPr"); _el("w:sz", base, val=ALG_SZ); _el("w:szCs", base, val=ALG_SZ)
    bold = copy.deepcopy(base); bold.insert(0, _el("w:b"))
    # 줄 번호 오른쪽 끝 9pt("10:" 7pt 폭 8.9pt), 번호와 본문 사이 3pt, 들여쓰기 한 단 6.5pt(87 [16]: 10행을 한 줄에 — 전에는 10/5/8.5pt)
    NUM_TAB, GAP, STEP = 180, 60, 130
    def para(left=0, hang=0, tabs=(), bottom=False, line=180):
        p = _el("w:p", tc); ppr = _el("w:pPr", p)
        _el("w:keepNext", ppr); _el("w:keepLines", ppr)
        if bottom:
            pb = _el("w:pBdr", ppr); _el("w:bottom", pb, val="single", sz=4, space=1, color="000000")
        if tabs:
            tb = _el("w:tabs", ppr)
            for kind, pos in tabs: _el("w:tab", tb, val=kind, pos=pos)
        _el("w:spacing", ppr, before=0, after=0, line=line, lineRule="exact")   # 9pt(7pt 글자). 머리 두 줄은 캡션 줄 간격
        _el("w:ind", ppr, left=left, hanging=hang)
        _el("w:jc", ppr, val="left")
        return p
    def tab_run(): r = _el("w:r"); r.append(copy.deepcopy(base)); _el("w:tab", r); return r
    kr = next((ln.strip() for ln in lines if ln.strip().startswith("알고리즘 ")), None)
    lines = [ln for ln in lines if not ln.strip().startswith("알고리즘 ")]
    def sized(rp, sz):
        rp = copy.deepcopy(rp)
        for e in rp.findall(qn("w:sz")) + rp.findall(qn("w:szCs")): rp.remove(e)
        _el("w:sz", rp, val=sz); _el("w:szCs", rp, val=sz); return rp
    def title(p, txt, sz):                                   # "Algorithm 1  제목" — 번호는 굵게, 제목은 보통(v1 꼴: 번호 뒤 두 칸)
        mm = re.match(r"^((?:Algorithm|알고리즘) \d+)(.*)$", txt)
        p.append(make_run(mm.group(1) if mm else txt, sized(bold, sz)))
        if mm and mm.group(2): p.append(make_run(mm.group(2), sized(base, sz)))
    for k, ln in enumerate(lines):
        m = re.match(r"^\s*(\d+):(\s*)(.*)$", ln)
        if k == 0:                                           # 머리: 국문 제목 줄 + 영문 제목 줄(그림·표 캡션처럼 국문 먼저), 아래 가는 선
            # 84 [3]: 글자 크기·줄 간격은 그림·표 캡션과 같게(국문 8pt → 7.92, 영문 7.5pt → 7.44, 줄 11.65pt).
            # 정렬은 왼쪽으로 둔다 — 알고리즘 상자는 머리가 상자 왼쪽 위에 붙는 것이 관례(v1 상자, LaTeX algorithm 꼴)이고
            # 상자 위·아래 괘선과 머리 아래 가는 선 사이에 들어 있어 가운데 캡션과 섞여 보일 일이 없다. 번호 굵게도 같은 관례.
            mm = re.match(r"^Algorithm (\d+)", ln.strip())
            if kr is None and mm and int(mm.group(1)) in ALG_KR: kr = f"알고리즘 {mm.group(1)}  {ALG_KR[int(mm.group(1))]}"
            if kr: title(para(line=CAP_LINE), kr, CAP_SZ_KR)
            title(para(bottom=True, line=CAP_LINE), ln.strip(), CAP_SZ_EN)
        elif m:                                              # " 9:     본문" — 번호는 오른쪽 탭, 본문은 깊이만큼
            depth = max(0, (len(m.group(2)) - 1) // 2); c = NUM_TAB + GAP + depth * STEP
            p = para(left=c + STEP, hang=c + STEP, tabs=(("right", NUM_TAB), ("left", c)))
            p.append(tab_run()); p.append(make_run(m.group(1) + ":", base)); p.append(tab_run())
            for r in math_runs(alg_keep(m.group(3).strip()), base, bare=True): p.append(r)
        else:                                                # Input: / Output:
            mm = re.match(r"^(\w+:)\s*(.*)$", ln.strip())
            p = para(left=STEP * 2, hang=STEP * 2)
            if mm:
                p.append(make_run(mm.group(1) + " ", bold))
                for r in math_runs(mm.group(2), base, bare=True): p.append(r)
            else:
                for r in math_runs(ln.strip(), base, bare=True): p.append(r)
    return tbl

# ── 본문 기호 → 수식 서체 (v1 mathify.py 의 v2 확장: 원고의 a_b / a^b / a_b^c 와 낱글자 변수) ──────
MATH = "Cambria Math"
# 밑(1~3 글자, 모자·물결 결합 포함) + _첨자(1~4 글자 또는 {…}) + 선택 ^위첨자( (t), 1~3 글자 또는 {…} )
# {…} 꼴(Σ_{j∈Q}, x^{α*}, x_{j r 0})은 89 [5] 지적 — 알고리즘과 본문에 원문 기호로 찍히던 것
SYM_RE = re.compile(r"(?<![A-Za-z0-9가-힣_^])([A-Za-zα-ωΑ-Ω℧ℓ][\u0302\u0303\u0304]?|cap|Ĉ|C̃|ℓ̃|λ̃|ẽ|λ̄|ē)"
                    r"(?:_(?:\{([^{}]{1,12})\}|([A-Za-z0-9α-ωΑ-Ωτ]{1,4})))?"
                    r"(?:\^(?:\{([^{}]{1,8})\}|(\([a-z]\)|[A-Za-z0-9α-ω]{1,3})))?(?![A-Za-z0-9_])")   # 뒤에 한글 조사가 바로 붙어도("d_j다") 잡는다
BARE_RE = re.compile(r"(?<![A-Za-z0-9α-ωΑ-Ω._/@%\-])([A-Za-zα-ωΑ-Ω])(?![A-Za-z0-9α-ωΑ-Ω._/@\-])")
STAR_RE = re.compile(r"(?<![A-Za-z0-9])([A-Za-zα-ω])\*")                      # 알고리즘의 α* (위첨자 *)
# 영문 단락(영문 캡션·표 칸·영문 초록)의 그리스 낱글자: 본문과 같은 수식 이탤릭으로(87 [20]: 표·캡션의 α 가 Times 직립이었다).
# 라틴 낱글자는 영문에서 낱말과 가릴 수 없어 그대로 둔다. "Fixed-α" 처럼 붙임표 뒤도 잡는다.
GREEK_RE = re.compile(r"(?<![A-Za-z0-9α-ωΑ-Ω._/@%])([α-ωΑ-Ω])(?![A-Za-z0-9α-ωΑ-Ω_])")
PANEL_RE = re.compile(r"(?:^|(?<=[\s(\d]))\(([b-h])\)")                           # 그림 칸 이름 "(b)", "그림 9(b)" — 변수가 아니다(87 [13] 나)
UPRIGHT = {"cap", "def", "max", "min", "Σ", "*"}

def _math_spans(text, bare=False, greek=False):
    """(시작, 끝, 밑, 첨자, 위첨자) 목록. 첨자/위첨자 없는 낱글자는 한국어 문장에서만(bare=True 면 늘 — 알고리즘)."""
    spans = []
    for m in SYM_RE.finditer(text):
        sub = m.group(2) if m.group(2) is not None else m.group(3)
        sup = m.group(4) if m.group(4) is not None else m.group(5)
        if sub is None and sup is None: continue
        spans.append((m.start(), m.end(), m.group(1), (sub or "").replace(" ", ""), sup or ""))
    taken = {i for a, b, *_ in spans for i in range(a, b)}
    if bare:
        for m in STAR_RE.finditer(text):
            if m.start() not in taken:
                spans.append((m.start(), m.end(), m.group(1), "", "*")); taken |= set(range(m.start(), m.end()))
    korean = sum(1 for c in text if "가" <= c <= "힣") / max(1, len(text))
    panel = {m.start(1) for m in PANEL_RE.finditer(text)} if not bare else set()
    if bare or (korean >= 0.25 and "@" not in text):
        for m in BARE_RE.finditer(text):
            if m.start() not in taken and m.group(1) not in ("a",) and m.start() not in panel:
                spans.append((m.start(), m.end(), m.group(1), "", "")); taken |= {m.start()}
    if greek:
        for m in GREEK_RE.finditer(text):
            if m.start() not in taken:
                spans.append((m.start(), m.end(), m.group(1), "", "")); taken |= {m.start()}
    return sorted(spans)

def _rpr_math(base_rpr, vert=None, upright=False):
    c = copy.deepcopy(base_rpr) if base_rpr is not None else etree.Element(qn("w:rPr"))
    for e in c.findall(qn("w:rFonts")) + c.findall(qn("w:i")) + c.findall(qn("w:vertAlign")): c.remove(e)
    f = etree.Element(qn("w:rFonts")); f.set(qn("w:ascii"), MATH); f.set(qn("w:hAnsi"), MATH); f.set(qn("w:cs"), MATH); c.insert(0, f)
    if not upright: c.append(etree.Element(qn("w:i")))
    if vert: v = etree.Element(qn("w:vertAlign")); v.set(qn("w:val"), vert); c.append(v)
    return c

def omml_subsup(base, sub, sup, base_rpr):
    """글줄 수식 <m:oMath><m:sSubSup> — 식 (8) 의 Ĉ_r^(t) 와 같은 꼴. 글자 크기는 둘레 글(base_rpr)의 sz 를 따른다."""
    def wrpr():
        rp = etree.Element(qn("w:rPr")); f = _el("w:rFonts", rp)
        for a in ("ascii", "hAnsi", "cs"): f.set(qn("w:" + a), MATH)
        if base_rpr is not None:
            for tag in ("w:sz", "w:szCs"):
                e = base_rpr.find(qn(tag))
                if e is not None: rp.append(copy.deepcopy(e))
        return rp
    def mrun(parent, txt, upright=False):
        r = etree.SubElement(parent, qn("m:r"))
        if upright: etree.SubElement(etree.SubElement(r, qn("m:rPr")), qn("m:sty")).set(qn("m:val"), "p")
        r.append(wrpr()); etree.SubElement(r, qn("m:t")).text = txt
    om = etree.Element(qn("m:oMath")); ss = etree.SubElement(om, qn("m:sSubSup"))
    etree.SubElement(etree.SubElement(ss, qn("m:sSubSupPr")), qn("m:ctrlPr")).append(wrpr())
    e = etree.SubElement(ss, qn("m:e")); nfd = unicodedata.normalize("NFD", base)
    if len(nfd) == 2 and nfd[1] in "̂̃̄":     # Ĉ → C 위 악센트(식 (8) 의 \hat{C} 와 같은 꼴 — 합성 글자 Ĉ 는 수식에서 바로 섰다)
        acc = etree.SubElement(e, qn("m:acc")); apr = etree.SubElement(acc, qn("m:accPr"))
        etree.SubElement(apr, qn("m:chr")).set(qn("m:val"), nfd[1])
        mrun(etree.SubElement(acc, qn("m:e")), nfd[0])
    else:
        mrun(e, base, upright=(base in UPRIGHT))
    mrun(etree.SubElement(ss, qn("m:sub")), sub, upright=(sub in UPRIGHT))
    mrun(etree.SubElement(ss, qn("m:sup")), sup, upright=(sup in UPRIGHT))
    return om

def math_runs(text, base_rpr, bare=False, greek=False, spans=None):
    """글 한 줄 → run 목록(기호는 Cambria Math 이탤릭·첨자). 본문 mathify 와 알고리즘이 같이 쓴다."""
    out = []
    def add(txt, rpr):
        if txt: out.append(make_run(txt, rpr))
    last = 0
    for a, b, base, sub, sup in (spans if spans is not None else _math_spans(text, bare=bare, greek=greek)):
        add(text[last:a], base_rpr)
        if sub and sup and bare:                              # Ĉ_r^(t): 아래·위첨자를 쌓는다(84 [9]: run 으로는 "Ĉr(t)" 로 옆으로 이어졌다).
            # 알고리즘(bare)에서만. 본문(양쪽 정렬)에 글줄 수식을 넣었더니 Word 가 수식 경계를 늘림 자리로 써서
            # "Ĉ_r^(t) (t+i, d_j)" 처럼 수식 뒤가 3pt 벌어졌다(6쪽, 시험 조립) — 본문은 전처럼 run 으로 둔다.
            out.append(omml_subsup(base, sub, sup, base_rpr)); last = b; continue
        add(base, _rpr_math(base_rpr, upright=(base in UPRIGHT)))
        if sub: add(sub, _rpr_math(base_rpr, "subscript", upright=(sub in UPRIGHT)))
        if sup.startswith("(") and sup.endswith(")"):         # Ĉ^(t): 괄호는 바로, t 는 이탤릭 — 식 (8) 과 같게
            add("(", _rpr_math(base_rpr, "superscript", upright=True)); add(sup[1:-1], _rpr_math(base_rpr, "superscript"))
            add(")", _rpr_math(base_rpr, "superscript", upright=True))
        elif sup: add(sup, _rpr_math(base_rpr, "superscript", upright=(sup in UPRIGHT)))
        last = b
    add(text[last:], base_rpr)
    return out

def mathify_paragraph(p):
    if p.find(".//" + qn("m:oMath")) is not None or p.find(".//" + qn("w:drawing")) is not None: return 0
    runs = p.findall(qn("w:r"))
    if not runs: return 0
    if any(f.get(qn("w:ascii")) == MATH for f in p.iter(qn("w:rFonts"))): return 0   # 이미 기호를 조판한 단락(알고리즘)
    text = "".join(t.text or "" for t in p.iter(qn("w:t")))
    if re.match(r"^\[\d+\]", text): return 0                                         # 참고문헌
    # 영문 캡션(Fig./Table)·표 칸·영문 초록도 그리스 낱글자를 수식 서체로(87 [20]). 라틴 낱글자는 한국어 단락에서만(_math_spans)
    n = 0
    for r in runs:                                     # run 마다 따로 — 초록처럼 굵은 머리말 run 의 서식을 지키려고
        t = r.find(qn("w:t"))
        if t is None or not t.text or any(ch.tag not in (qn("w:rPr"), qn("w:t")) for ch in r): continue   # 탭·줄바꿈이 든 run 은 두기
        txt = t.text
        spans = _math_spans(txt, greek=True)
        if not spans: continue
        new = math_runs(txt, r.find(qn("w:rPr")), spans=spans)
        for x in new: r.addprevious(x)
        p.remove(r); n += len(spans)
    return n

def mathify_doc(doc):
    n = 0
    for p in doc.element.body.iter(qn("w:p")): n += mathify_paragraph(p)
    return n


# ── 조립 ──────────────────────────────────────────────────────────────────
def build(src, out, shift=None):
    head, blocks = parse(src)
    sh = dict(FLOAT_SHIFT); sh.update(shift or {})
    if FLOAT_ALL and sh:
        blocks = apply_shift(blocks, sh); print("  자리 옮김:", ", ".join(f"{dict(fig='그림', tbl='표', alg='알고리즘')[k]} {n} {d:+d}" for (k, n), d in sh.items() if d))
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
    # 초록도 문장부호 내밀기를 끈다 — 영문 초록 "64.44–71.93%" 의 %가 오른쪽 여백으로 6pt 나갔다(2회차 조립)
    add(no_overflow(lead_para(tb[5], "초록", head["초록"]))); add(para_from(tb[6], "주제어: " + head["주제어"], keep_sect=True))
    add(no_overflow(lead_para(tb[7], "Abstract", head["Abstract"]))); add(para_from(tb[8], "Keywords: " + head["Keywords"], keep_sect=True))
    prev_p = None
    for k, (kind, val) in enumerate(blocks):
        if kind == "h1": add(keep_next_only(para_from(T["h1"], val)))
        elif kind == "h2": add(keep_next_only(para_from(T["h2"], val)))
        elif kind == "p": add(keep_next_only(no_overflow(para_from(T["body"], break_after_slash(val))), keep=False))
        elif kind == "eq": add(eq_elem(T, val))
        elif kind == "alg":                                # 상자 위·아래 4pt 띄움(빈 단락, 높이 4pt) — 본문이 괘선에 붙지 않게
            if ALG_FLOAT:                                  # 띄우면 위 여백은 topFromText, 빈 단락은 단 가운데 빈 줄로 남으므로 뺀다
                add(alg_elem(T, val))
                if k + 1 < len(blocks) and blocks[k + 1][0] in ("fig", "tbl", "alg"): add(spacer(h=20))   # 이웃 표와 한 표로 합쳐지지 않게
            else: add(spacer(keep=True)); add(alg_elem(T, val)); add(spacer())
        elif kind == "fig":
            fp, path, width, kr, en = figure_elems(T, val, None if FLOAT_ALL else prev_p)
            pictures.append((fp, path, width))
            if FLOAT_ALL:
                if val["width"] == "전폭": strip_sect(en)
                add(float_box([fp, kr, en], full=(val["width"] == "전폭")))
                if k + 1 < len(blocks) and blocks[k + 1][0] in ("fig", "tbl", "alg"): add(spacer(h=20))   # 이웃 표와 한 표로 합쳐지지 않게
            else:
                add(fp); add(kr); add(en)
                if val["width"] == "단폭" and FLOAT_FIGS: float_top(fp, kr, en)
        elif kind == "tbl":
            ncol = max(len(r) for r in val["rows"])
            if not val["explicit"] and ncol >= 5:      # 표기 없고 열 5개 이상: 단폭에 들어가면 단폭, 아니면 전폭(89 [13]; 전에는 무조건 전폭)
                fits, need = table_fits_column(val["rows"]); val["width"] = "단폭" if fits else "전폭"
                print(f"  표 {val['n']}: 열 {ncol}개, 어림 폭 {need:.0f}pt → {val['width']}")
            kr, en, t = table_elems(T, val, full=(val["width"] == "전폭"))
            if FLOAT_ALL:
                add(float_box([kr, en, t], full=(val["width"] == "전폭")))
                if k + 1 < len(blocks) and blocks[k + 1][0] in ("fig", "tbl", "alg"): add(spacer(h=20))   # 이웃 표와 한 표로 합쳐지지 않게
            elif val["width"] == "전폭":                      # 전폭 표: 앞 단락에서 2단 섹션을 끝내고, 표 뒤 빈 단락이 1단 섹션을 끝낸다
                if prev_p is not None: add_sect(prev_p, T["sect_body"])
                add(kr); add(en); add(t)
                tail = para_from(T["body"], ""); add_sect(tail, T["sect_fig"]); add(tail)
            else:                                          # 단폭 표 아래 6pt(89 [22]: 아래 괘선에 본문이 3pt 로 붙음)
                add(kr); add(en); add(t); add(spacer(h=120))
        elif kind == "refs":
            add(para_from(T["ref_h"], "참고문헌"))
            for item in val: add(no_overflow(para_from(T["ref_item"], item)))
    for fp, path, width in pictures:                       # 그림은 문단이 문서에 붙은 뒤 넣는다(관계 id 때문)
        Paragraph(fp, doc._body).add_run().add_picture(path, width=Pt(width))
    n_math = mathify_doc(doc); n_hf = head_font(doc); print(f"  제목 한글 글꼴 {n_hf}곳 → {HEAD_KR_FONT}")
    doc.save(out)
    print(f"본문 기호 {n_math}곳을 수식 서체로")
    n_p = len(body.findall(qn("w:p"))); n_t = len(body.findall(qn("w:tbl")))
    print(f"wrote {out}: 문단 {n_p}, 표 {n_t}, 그림 {len(pictures)}, 식 {sum(1 for k, _ in blocks if k == 'eq')}, 참고문헌 {sum(len(v) for k, v in blocks if k == 'refs')}")

def layout_report(pdf):
    """내보낸 PDF 에서 단 아래 빈 곳(40pt 넘는 것)과 그림·표의 자리(국문 캡션 첫 줄)를 적는다 — FLOAT_SHIFT 를 맞출 때 본다."""
    import pymupdf
    d = pymupdf.open(pdf); MID, BOT = 258.6, 652
    print(f"{pdf}: {len(d)}쪽")
    for i, pg in enumerate(d):
        rs = [pymupdf.Rect(b["bbox"]) for b in pg.get_text("dict")["blocks"]] + [x["rect"] for x in pg.get_drawings()]
        rs = [r for r in rs if 40 < r.y0 and r.y1 < 680]
        if not rs or i == 0 or i == len(d) - 1: continue
        for col, (x0, x1) in (("L", (50, MID)), ("R", (MID, 470))):
            ys = [r.y1 for r in rs if r.x0 < x1 - 2 and r.x1 > x0 + 2]
            if ys and BOT - max(ys) > 40: print(f"  {i + 1}쪽 {col}단 아래 {BOT - max(ys):.0f}pt 빔")
        for b in pg.get_text("dict")["blocks"]:
            for l in b.get("lines", [])[:1]:
                t = "".join(x["text"] for x in l["spans"]).strip()
                m = re.match(r"^(그림|표) (\d+) ", t)
                if m and l["bbox"][0] < 470: print(f"    {m.group(1)} {m.group(2)}: {i + 1}쪽 {'L' if l['bbox'][0] < MID else 'R'} y{l['bbox'][1]:.0f}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--in", dest="src", default=os.path.join(DRAFT, "99_원고.txt"))
    ap.add_argument("--out", default=os.path.join(ROOT, "paper", "CAST_JOK_v2.docx"))
    ap.add_argument("--shift", default="", help="자리 옮김 시험: fig5=-1,tbl3=1 (FLOAT_SHIFT 위에 덮어씀)")
    ap.add_argument("--report", metavar="PDF", help="조립하지 않고 내보낸 PDF 의 빈 곳·그림표 자리만 적는다")
    a = ap.parse_args()
    if a.report: layout_report(a.report); sys.exit()
    sh = {}
    for x in filter(None, a.shift.split(",")):
        m = re.match(r"^(fig|tbl|alg)(\d+)=([+-]?\d+)$", x.strip()); sh[(m.group(1), int(m.group(2)))] = int(m.group(3))
    build(a.src, a.out, sh)
