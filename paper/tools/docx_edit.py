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


def replace_text(xml, head, new_text, allow_sectpr=False):
    """문단 하나의 본문 텍스트를 통째로 갈아끼운다. 첫 run 의 서식을 유지한다.

    2026-09-24 사고: 이 함수는 run 을 전부 버리고 새로 하나 만든다. 그런데
    사용자가 단 Word 메모의 표식(<w:commentRangeStart/End>, 그리고
    <w:commentReference> 를 품은 run)이 바로 그 문단 안에 있다 — 그림 1 캡션을
    고치면서 거기 달린 메모의 앵커를 통째로 날렸고, comments.xml 에 본문만 남아
    어디에 달렸는지 모르는 떠돌이 메모가 됐다. 사용자가 적은 글을 소리 없이
    잃는 건 가장 나쁜 실패다.
    이제 메모 표식을 뽑아 두었다가 새 run 앞뒤로 도로 끼운다 — 메모는 문단
    전체를 가리키게 되지만(원래는 문구 일부였을 수 있다) 사라지지는 않는다.
    """
    s, e, frag, old = find_one(xml, head)
    for k in PROTECT:
        if k == "<w:sectPr" and allow_sectpr:
            # 2026-10-08: 전단 그림의 영문 캡션 문단이 구역 나눔을 품는다. 이 함수는
            # <w:pPr> 를 통째로 보존하므로(아래 ppr) sectPr 도 그대로 남는다 —
            # 호출하는 쪽이 그걸 알고 있을 때만 열어 준다. 끝에서 보존을 검사한다.
            continue
        assert k not in frag, f"{head[:30]!r}: {k} 포함 — 편집 금지"

    runs = RUN.findall(frag)
    assert runs, f"{head[:30]!r}: run 이 없음"

    def _rpr(r):
        m = re.search(r'<w:rPr\b.*?</w:rPr>', r, re.DOTALL)
        return m.group(0) if m else ""

    def _txt(r):
        return "".join(re.findall(r'<w:t\b[^>]*>(.*?)</w:t>', r, re.DOTALL))

    # 2026-09-28 사고: 서식이 섞인 문단에서 첫 run 서식을 통째로 쓰면 문단 전체가
    # 그 서식이 된다. 캡션은 "그림 3." 만 굵고 나머지는 보통인데, 첫 run 이 그
    # 굵은 라벨이라 고칠 때마다 캡션 전체가 굵어졌다 — 그림 1·5·6·7·8·10 과
    # 표 3·4 의 캡션 여덟이 그렇게 굵어져 있었다(본문 조판이 이랬다저랬다 한 원인).
    # 앞쪽 run 들이 같은 서식이고 그 뒤가 다르면, 그 경계를 새 글에도 적용한다.
    pre_rpr = _rpr(runs[0])
    k = 0
    while k < len(runs) and _rpr(runs[k]) == pre_rpr:
        k += 1
    pre_text = "".join(_txt(r) for r in runs[:k])
    mixed = k < len(runs)

    def _run(rpr, text):
        return f'<w:r>{rpr}<w:t xml:space="preserve">{_esc(text)}</w:t></w:r>'

    def _major(rs):
        """글자 수가 가장 많은 서식 — 짧은 기호 run 이 문단을 물들이지 않게 한다.

        2026-09-28 사고: 처음엔 앞머리 바로 뒤 run(runs[k])의 서식을 썼다. 그런데
        "작업 집합을 J, 리전 집합을 R로…" 처럼 앞머리가 평문이고 그 다음이 기호 J
        (Cambria Math 기울임)인 문단에서는 **문단 전체가 수식 서체로 찍혔다.**
        본문 여덟 문단이 통째로 기울임이 됐다. 다수결이어야 맞다.
        """
        best, blen = "", -1
        for r in rs:
            t = len(_txt(r))
            if t > blen:
                best, blen = _rpr(r), t
        return best

    if mixed and pre_text and new_text.startswith(pre_text):
        # 앞머리(예: "그림 3.")가 그대로면 경계를 지켜 두 run 으로 나눈다.
        # 남은 글에는 뒤쪽에서 가장 널리 쓰인 서식을 준다(바로 다음 run 이 아니다).
        new_run = _run(pre_rpr, pre_text) + _run(_major(runs[k:]), new_text[len(pre_text):])
        print(f"  · 서식이 섞인 문단이다 — 앞머리 {pre_text.strip()[:20]!r} 서식을 지켜 나눴다")
    elif mixed:
        # 앞머리가 바뀌었다 — 다수결 서식을 문단 전체에 쓴다.
        new_run = _run(_major(runs), new_text)
        print(f"  · 서식이 섞인 문단인데 앞머리가 바뀌었다 — 가장 긴 run 의 서식을 썼다. 눈으로 확인할 것")
    else:
        new_run = _run(pre_rpr, new_text)

    # 메모 표식 보존 — 여는 것은 새 run 앞, 닫는 것과 참조 run 은 뒤에 둔다
    starts = "".join(re.findall(r'<w:commentRangeStart\b[^>]*/>', frag))
    ends = "".join(re.findall(r'<w:commentRangeEnd\b[^>]*/>', frag))
    refs = "".join(re.findall(
        r'<w:r\b(?:(?!</w:r>).)*?<w:commentReference\b[^>]*/>(?:(?!</w:r>).)*?</w:r>',
        frag, re.DOTALL))

    # 문단 속성(<w:pPr>)은 그대로 두고 run 만 교체
    ppr = re.search(r'<w:pPr\b.*?</w:pPr>', frag, re.DOTALL)
    ppr = ppr.group(0) if ppr else ""
    open_tag = re.match(r'<w:p\b[^>]*?>', frag).group(0)
    new_frag = f"{open_tag}{ppr}{starts}{new_run}{ends}{refs}</w:p>"
    if "<w:sectPr" in frag:
        assert "<w:sectPr" in new_frag, f"{head[:30]!r}: 구역 나눔이 사라졌다"
    if starts:
        ids = re.findall(r'w:id="(\d+)"', starts)
        print(f"  · 메모 {ids} 가 달린 문단이다 — 표식을 문단 전체로 옮겨 보존했다")
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


# ─────────────────────────────────────────────────────────────────────────
# 표 칸 편집 — 2026-10-08 추가
#
# paragraphs() 는 표 안 문단을 **일부러 제외한다**(표는 통째로 손대지 않는다는
# 원칙). 그런데 JOK 투고 규정 10항이 "그림 및 표의 내용은 모두 영문"을 요구해
# 칸 안의 글을 바꿔야 했다. 문단처럼 글머리로 찾으면("한국" 같은 짧은 말) 다른
# 데와 겹쳐 위험하므로, **(표 번호, 행 번호, 칸 번호) 좌표로만** 찾는다.
# 서식은 다수결(_major 와 같은 규칙)로 고른다 — 칸은 보통 서식이 하나뿐이다.
TR = re.compile(r'<w:tr\b(?:(?!<w:tr\b).)*?</w:tr>', re.DOTALL)
TC = re.compile(r'<w:tc>(?:(?!<w:tc>).)*?</w:tc>', re.DOTALL)


def table_spans(xml):
    return [(m.start(), m.end()) for m in TBL.finditer(xml)]


def cell_text(xml, ti, ri, ci):
    s, e, _ = _locate_cell(xml, ti, ri, ci)
    return text_of(xml[s:e])


def _locate_cell(xml, ti, ri, ci):
    """(표, 행, 칸) 좌표의 <w:tc> 범위를 절대 위치로 돌려준다. 1부터 센다."""
    sp = table_spans(xml)
    assert 1 <= ti <= len(sp), f"표 {ti} 없음 (총 {len(sp)}개)"
    ts, te = sp[ti - 1]
    tbl = xml[ts:te]
    assert tbl.count("<w:tbl>") == 1, f"표 {ti}: 중첩 표 — 손대지 않는다"
    rows = list(TR.finditer(tbl))
    assert 1 <= ri <= len(rows), f"표 {ti} 행 {ri} 없음 (총 {len(rows)}행)"
    row = rows[ri - 1]
    cells = list(TC.finditer(row.group(0)))
    assert 1 <= ci <= len(cells), f"표 {ti} 행 {ri} 칸 {ci} 없음 (총 {len(cells)}칸)"
    c = cells[ci - 1]
    s = ts + row.start() + c.start()
    e = ts + row.start() + c.end()
    return s, e, c.group(0)


def replace_cell(xml, ti, ri, ci, old_expect, new_text):
    """표 칸 하나의 글을 바꾼다. old_expect 와 지금 글이 다르면 멈춘다.

    old_expect 를 요구하는 이유: 좌표만으로 고치면 표 구조가 바뀌었을 때
    엉뚱한 칸을 조용히 덮어쓴다. 지금 글을 함께 대조해야 안전하다.
    """
    s, e, frag = _locate_cell(xml, ti, ri, ci)
    for k in PROTECT:
        assert k not in frag, f"표{ti}/{ri}/{ci}: {k} 포함 — 편집 금지"
    cur = text_of(frag)
    assert cur == old_expect, f"표{ti}/{ri}/{ci}: 지금 글이 {cur!r} 인데 {old_expect!r} 를 기대했다"

    paras = list(PARA.finditer(frag))
    assert len(paras) == 1, f"표{ti}/{ri}/{ci}: 문단이 {len(paras)}개 — 1개여야 한다"
    p = paras[0]
    pf = p.group(0)
    runs = RUN.findall(pf)
    assert runs, f"표{ti}/{ri}/{ci}: run 이 없음"

    def _rpr(r):
        m = re.search(r'<w:rPr\b.*?</w:rPr>', r, re.DOTALL)
        return m.group(0) if m else ""

    def _txt(r):
        return "".join(re.findall(r'<w:t\b[^>]*>(.*?)</w:t>', r, re.DOTALL))

    best, blen = "", -1
    for r in runs:                       # 다수결 서식
        t = len(_txt(r))
        if t > blen:
            best, blen = _rpr(r), t

    starts = "".join(re.findall(r'<w:commentRangeStart\b[^>]*/>', pf))
    ends = "".join(re.findall(r'<w:commentRangeEnd\b[^>]*/>', pf))
    refs = "".join(re.findall(
        r'<w:r\b(?:(?!</w:r>).)*?<w:commentReference\b[^>]*/>(?:(?!</w:r>).)*?</w:r>',
        pf, re.DOTALL))
    ppr = re.search(r'<w:pPr\b.*?</w:pPr>', pf, re.DOTALL)
    ppr = ppr.group(0) if ppr else ""
    open_tag = re.match(r'<w:p\b[^>]*?>', pf).group(0)
    new_run = f'<w:r>{best}<w:t xml:space="preserve">{_esc(new_text)}</w:t></w:r>'
    new_p = f"{open_tag}{ppr}{starts}{new_run}{ends}{refs}</w:p>"
    new_frag = frag[:p.start()] + new_p + frag[p.end():]
    return xml[:s] + new_frag + xml[e:]


def insert_after(xml, head, new_text, size_half=None):
    """head 로 찾은 문단 **바로 뒤**에 같은 서식의 문단을 하나 끼운다.

    2026-10-08 추가. JOK 규정 10항이 그림·표 제목을 한글과 영문 두 줄로 요구해
    기존 캡션 아래에 영문 줄을 넣어야 했다. 앵커 문단의 <w:pPr> 과 다수결 서식을
    그대로 물려받되, size_half(=w:sz 값, pt의 두 배)를 주면 글자 크기만 바꾼다.
    앵커 문단 자체는 건드리지 않는다 — 메모 앵커가 날아갈 일이 없다.
    """
    s, e, frag, old = find_one(xml, head)
    for k in PROTECT:
        assert k not in frag, f"{head[:30]!r}: {k} 포함 — 뒤에 끼우지 않는다"

    runs = RUN.findall(frag)
    assert runs, f"{head[:30]!r}: run 이 없음"

    def _rpr(r):
        m = re.search(r'<w:rPr\b.*?</w:rPr>', r, re.DOTALL)
        return m.group(0) if m else ""

    def _txt(r):
        return "".join(re.findall(r'<w:t\b[^>]*>(.*?)</w:t>', r, re.DOTALL))

    best, blen = "", -1
    for r in runs:
        t = len(_txt(r))
        if t > blen:
            best, blen = _rpr(r), t
    if size_half is not None:
        best = re.sub(r'<w:sz w:val="\d+"\s*/>', f'<w:sz w:val="{size_half}"/>', best)
        best = re.sub(r'<w:szCs w:val="\d+"\s*/>', f'<w:szCs w:val="{size_half}"/>', best)
        if "<w:sz " not in best:
            inner = best[len("<w:rPr>"):-len("</w:rPr>")] if best.startswith("<w:rPr>") else ""
            best = f'<w:rPr>{inner}<w:sz w:val="{size_half}"/><w:szCs w:val="{size_half}"/></w:rPr>'

    ppr = re.search(r'<w:pPr\b.*?</w:pPr>', frag, re.DOTALL)
    ppr = ppr.group(0) if ppr else ""
    # 앵커의 줄간격/들여쓰기는 물려받되, 캡션 아래 여백(spacing after)은 앵커 쪽에
    # 남겨 두는 게 자연스럽다 — 여기서는 그대로 쓴다(조판은 눈으로 확인할 것).
    new_p = (f'<w:p>{ppr}<w:r>{best}'
             f'<w:t xml:space="preserve">{_esc(new_text)}</w:t></w:r></w:p>')
    return xml[:e] + new_p + xml[e:]


def set_run_text(xml, head, idx, expect, new_text):
    """문단 안 idx 번째 run 의 글자만 바꾼다 (0부터). 서식은 손대지 않는다.

    2026-10-08 추가. 캡션 머리("그림 1.")는 굵은 run 둘로 쪼개져 있어
    replace_text 로 문단을 통째 갈면 굵기를 잃는다(2026-09-28 사고와 같은 길).
    run 하나의 <w:t> 내용만 바꾸면 서식·메모 앵커가 전부 그대로 남는다.
    expect 로 지금 글을 대조해 엉뚱한 run 을 건드리지 않게 한다.
    """
    s, e, frag, old = find_one(xml, head)
    runs = list(RUN.finditer(frag))
    assert 0 <= idx < len(runs), f"{head[:24]!r}: run {idx} 없음 (총 {len(runs)}개)"
    r = runs[idx]
    rf = r.group(0)
    cur = "".join(re.findall(r'<w:t\b[^>]*>(.*?)</w:t>', rf, re.DOTALL))
    assert cur == expect, f"{head[:24]!r} run{idx}: 지금 {cur!r} 인데 {expect!r} 를 기대했다"
    ts = list(re.finditer(r'(<w:t\b[^>]*>)(.*?)(</w:t>)', rf, re.DOTALL))
    assert len(ts) == 1, f"{head[:24]!r} run{idx}: <w:t> 가 {len(ts)}개"
    t = ts[0]
    new_rf = rf[:t.start()] + f'<w:t xml:space="preserve">{_esc(new_text)}</w:t>' + rf[t.end():]
    new_frag = frag[:r.start()] + new_rf + frag[r.end():]
    return xml[:s] + new_frag + xml[e:]


def set_ppr_spacing(xml, head, before=None, after=None, keep_next=None):
    """문단의 <w:spacing> 과 keepNext 만 손본다. 글자는 건드리지 않는다.

    2026-10-08 추가. 캡션 한글 줄과 영문 줄이 각각 after=240(12pt) 을 들고 있어
    두 줄 사이가 15pt 나 벌어졌다(한글의 after 12 + 영문의 before 3). 두 줄은
    한 제목이므로 붙여야 하고, 붙이면 세로 공간도 회수된다.
    요소 순서는 스키마가 정한다 — keepNext 가 keepLines 보다 앞이다.
    """
    s, e, frag, old = find_one(xml, head)
    m = re.search(r'<w:pPr\b.*?</w:pPr>', frag, re.DOTALL)
    assert m, f"{head[:24]!r}: pPr 이 없다"
    ppr = m.group(0)
    if before is not None or after is not None:
        sp = re.search(r'<w:spacing\b[^>]*/>', ppr)
        assert sp, f"{head[:24]!r}: spacing 이 없다"
        cur = dict(re.findall(r'w:(before|after|line|lineRule|beforeLines|afterLines)="([^"]+)"', sp.group(0)))
        if before is not None:
            cur["before"] = str(before)
        if after is not None:
            cur["after"] = str(after)
        order = ["before", "after", "line", "lineRule"]
        attrs = " ".join(f'w:{k}="{cur[k]}"' for k in order if k in cur)
        ppr = ppr[:sp.start()] + f"<w:spacing {attrs}/>" + ppr[sp.end():]
    if keep_next is True and "<w:keepNext/>" not in ppr:
        ppr = ppr.replace("<w:pPr>", "<w:pPr><w:keepNext/>", 1)
    if keep_next is False:
        ppr = ppr.replace("<w:keepNext/>", "")
    new_frag = frag[:m.start()] + ppr + frag[m.end():]
    return xml[:s] + new_frag + xml[e:]


def delete_substring(xml, head, target):
    """문단 안의 특정 글자만 잘라낸다. run 서식은 그대로 둔다.

    2026-10-09 사고: replace_text 로 문단을 통째 갈았더니 기울임 변수 13개(t, Wj, Dj …)가
    납작해졌다. Word 는 한 문단을 run 수십~수백 개로 쪼개 두고 변수마다 기울임을 준다 —
    문단을 하나의 run 으로 다시 쓰면 그 서식이 전부 사라진다.
    글자 몇 개만 지우는 일에는 문단을 다시 쓰지 말고 이 함수를 쓴다.
    """
    s, e, frag, old = find_one(xml, head)
    runs = list(RUN.finditer(frag))
    assert runs, f"{head[:24]!r}: run 이 없음"

    texts, spans = [], []
    pos = 0
    for r in runs:
        t = "".join(re.findall(r'<w:t\b[^>]*>(.*?)</w:t>', r.group(0), re.DOTALL))
        texts.append(t)
        spans.append((pos, pos + len(t)))
        pos += len(t)
    whole = "".join(texts)
    i = whole.find(target)
    assert i >= 0, f"{head[:24]!r}: {target!r} 를 못 찾음"
    assert whole.count(target) == 1, f"{head[:24]!r}: {target!r} 가 여러 번 나온다"
    j = i + len(target)

    out, last = [], 0
    for k, r in enumerate(runs):
        a, b = spans[k]
        if b <= i or a >= j:                       # 손댈 것 없음
            continue
        out.append((r, a, b))
    new_frag = frag
    for r, a, b in reversed(out):
        keep = texts[runs.index(r)][: max(0, i - a)] + texts[runs.index(r)][max(0, j - a):]
        rf = r.group(0)
        if keep == "":
            new_frag = new_frag[:r.start()] + new_frag[r.end():]
        else:
            ts = list(re.finditer(r'(<w:t\b[^>]*>)(.*?)(</w:t>)', rf, re.DOTALL))
            assert len(ts) == 1, f"{head[:24]!r}: run 안 <w:t> 가 {len(ts)}개"
            t = ts[0]
            new_rf = rf[:t.start()] + f'<w:t xml:space="preserve">{_esc(keep)}</w:t>' + rf[t.end():]
            new_frag = new_frag[:r.start()] + new_rf + new_frag[r.end():]
    return xml[:s] + new_frag + xml[e:], len(target)


# 본문 안에서 기호를 찍을 때 Word 가 쓰는 서식 (문서에서 그대로 떠 왔다).
MATH_RPR = '<w:rPr><w:rFonts w:ascii="Cambria Math" w:hAnsi="Cambria Math"/><w:i/></w:rPr>'
SUB_RPR = ('<w:rPr><w:rFonts w:ascii="Cambria Math" w:hAnsi="Cambria Math"/>'
           '<w:i/><w:vertAlign w:val="subscript"/></w:rPr>')
STYLES = {"": "", "math": MATH_RPR, "sub": SUB_RPR}


def insert_at(xml, head, after, segments):
    """문단 안 `after` 가 끝나는 자리 뒤에 run 을 끼운다 — 기존 run 은 안 건드린다.

    2026-10-12: replace_text 는 문단의 run 을 전부 버리고 새로 만든다. 서식이
    섞인 문단(기호가 Cambria Math 기울임, 아래첨자까지 있는 곳)에서 그걸 쓰면
    아래첨자가 통째로 날아간다 — 3.2 절 표기 문단이 정확히 그 모양이라 과거에
    사고가 났다. 글을 **보태기만** 할 때는 이 함수를 쓴다.

    segments 는 [(스타일, 글), …] 이고 스타일은 "" (본문) · "math" (기호
    기울임) · "sub" (아래첨자) 셋이다. 끼우는 자리가 run 한가운데면 그 run 만
    둘로 쪼갠다.
    """
    s, e, frag, _ = find_one(xml, head)
    runs = list(RUN.finditer(frag))
    assert runs, f"{head[:24]!r}: run 이 없음"

    texts, spans, pos = [], [], 0
    for r in runs:
        t = "".join(re.findall(r'<w:t\b[^>]*>(.*?)</w:t>', r.group(0), re.DOTALL))
        texts.append(t)
        spans.append((pos, pos + len(t)))
        pos += len(t)
    whole = "".join(texts)
    assert whole.count(after) == 1, \
        f"{head[:24]!r}: {after!r} 가 {whole.count(after)}번 나온다 (1번이어야 함)"
    j = whole.find(after) + len(after)

    # 2026-10-12 사고: 스타일 "" 는 rPr 없는 run 을 만든다. 본문 문단은 원래 run 도
    # rPr 이 없어 똑같이 찍히지만, ** 제목처럼 run 에 크기·굵기가 박힌 문단 ** 에 넣으면
    # 그 글자만 본문 크기로 떨어진다(5절 제목 "결론 및 향후 연구"가 9.12 → 7.92pt 로
    # 찍혔다). 그래서 "" 는 이제 ** 그 문단에서 글자 수가 가장 많은 run 의 서식 ** 을
    # 따른다 — 본문에서는 전과 같고, 제목에서는 제목 서식이 된다.
    def _rpr_of(r):
        m = re.search(r'<w:rPr\b.*?</w:rPr>', r, re.DOTALL)
        return m.group(0) if m else ""

    best, blen = "", -1
    for r in runs:
        tx = "".join(re.findall(r'<w:t\b[^>]*>(.*?)</w:t>', r.group(0), re.DOTALL))
        if len(tx) > blen:
            best, blen = _rpr_of(r.group(0)), len(tx)

    new_runs = "".join(
        f'<w:r>{best if st == "" else STYLES[st]}<w:t xml:space="preserve">{_esc(tx)}</w:t></w:r>'
        for st, tx in segments)

    # 끼울 자리가 어느 run 에 걸리는지 — 경계면 그 뒤에, 한가운데면 쪼갠다.
    for k, r in enumerate(runs):
        a, b = spans[k]
        if j == b:                                  # run 경계 — 그대로 뒤에 붙인다
            return xml[:s] + frag[:r.end()] + new_runs + frag[r.end():] + xml[e:]
        if a < j < b:                               # run 한가운데 — 둘로 쪼갠다
            rf = r.group(0)
            ts = list(re.finditer(r'(<w:t\b[^>]*>)(.*?)(</w:t>)', rf, re.DOTALL))
            assert len(ts) == 1, f"{head[:24]!r}: run 안 <w:t> 가 {len(ts)}개"
            rpr = re.search(r'<w:rPr\b.*?</w:rPr>', rf, re.DOTALL)
            rpr = rpr.group(0) if rpr else ""
            left, right = texts[k][:j - a], texts[k][j - a:]
            two = (f'<w:r>{rpr}<w:t xml:space="preserve">{_esc(left)}</w:t></w:r>'
                   + new_runs
                   + f'<w:r>{rpr}<w:t xml:space="preserve">{_esc(right)}</w:t></w:r>')
            return xml[:s] + frag[:r.start()] + two + frag[r.end():] + xml[e:]
    raise AssertionError(f"{head[:24]!r}: 끼울 자리를 못 찾음 (j={j})")


# ─────────────────────────────────────────────────────────────────────────
# 표 만들기 — 2026-10-12 추가 (교수님 피드백 대응으로 새 표가 필요해졌다)
#
# 새 표를 맨땅에서 쓰면 서식이 본문과 어긋난다. JOK 본문의 표는 넷 다 같은
# 규격이다 — 단폭 3912 dxa, 글자 6.5pt(sz 13), 머리행만 굵게·가운데·아래 테두리,
# 자료행은 첫 칸 왼쪽 나머지 오른쪽 정렬. 그래서 **기존 표를 본으로 복제**하고
# 글자만 갈아끼운다. 열 수는 본과 같아야 한다(4열).
#
# w14:paraId / w14:textId 는 문서 안에서 유일해야 하므로 복제본에서 지운다 —
# Word 가 다음 저장 때 다시 매긴다.

def _strip_ids(frag):
    return re.sub(r'\s+w14:(?:paraId|textId)="[^"]*"', '', frag)


def _set_cell_text(tc, text):
    """칸 하나의 글을 바꾼다 — 첫 run 의 서식만 남기고 run 들을 하나로 합친다."""
    runs = list(RUN.finditer(tc))
    assert runs, "칸에 run 이 없음"
    m = re.search(r'<w:rPr\b.*?</w:rPr>', runs[0].group(0), re.DOTALL)
    rpr = m.group(0) if m else ""
    new_run = f'<w:r>{rpr}<w:t xml:space="preserve">{_esc(text)}</w:t></w:r>'
    return tc[:runs[0].start()] + new_run + tc[runs[-1].end():]


def set_table_widths(tbl, widths):
    """<w:tbl> 문자열의 열 폭을 바꾼다. 합이 tblW 와 같아야 한다(단폭 3912 dxa).

    clone_table 은 본 표의 tblGrid 를 그대로 물려받는데, 본과 글자 길이가 다른
    표(예: 부록의 설명형 표)는 그 폭으로는 칸마다 줄이 접힌다. 폭만 따로 고친다.
    """
    assert len(widths) >= 1
    grid = "".join(f'<w:gridCol w:w="{w}"/>' for w in widths)
    tbl = re.sub(r'<w:tblGrid>.*?</w:tblGrid>', f'<w:tblGrid>{grid}</w:tblGrid>', tbl, flags=re.DOTALL)
    out, pos = "", 0
    for tr in TR.finditer(tbl):
        out += tbl[pos:tr.start()]
        row, rpos, i = "", 0, 0
        frag = tr.group(0)
        for tc in TC.finditer(frag):
            row += frag[rpos:tc.start()]
            row += re.sub(r'<w:tcW w:w="\d+"', f'<w:tcW w:w="{widths[i % len(widths)]}"', tc.group(0), count=1)
            rpos = tc.end(); i += 1
        out += row + frag[rpos:]
        pos = tr.end()
    return out + tbl[pos:]


def clone_table(xml, src_index, rows):
    """기존 표(0부터 센 src_index)를 본으로 같은 서식의 새 <w:tbl> 문자열을 만든다.

    rows[0] 이 머리행, 나머지가 자료행이다. 본의 첫 행을 머리 틀로, 둘째 행을
    자료 틀로 쓴다. 자료행 수는 본과 달라도 된다(틀을 반복해 찍는다).
    """
    s, e = table_spans(xml)[src_index]
    frag = xml[s:e]
    trs = TR.findall(frag)
    assert len(trs) >= 2, "본 표에 머리행과 자료행이 둘 다 있어야 한다"
    pre = frag[: frag.index(trs[0])]          # <w:tbl> + tblPr + tblGrid
    ncol = len(re.findall(r'<w:gridCol\b[^>]*/>', frag))
    assert all(len(r) == ncol for r in rows), f"모든 행이 {ncol}칸이어야 한다"

    body = []
    for i, row in enumerate(rows):
        tpl = _strip_ids(trs[0] if i == 0 else trs[1])
        tcs = TC.findall(tpl)
        assert len(tcs) == ncol, f"틀 행의 칸이 {len(tcs)}개 (열 {ncol})"
        new_tr, pos = "", 0
        for tc, txt in zip(tcs, row):
            k = tpl.index(tc, pos)
            new_tr += tpl[pos:k] + _set_cell_text(tc, txt)
            pos = k + len(tc)
        body.append(new_tr + tpl[pos:])
    return pre + "".join(body) + "</w:tbl>"


def _clone_para(xml, head, text):
    """기존 문단을 본으로 글만 바꾼 새 <w:p> 문자열을 만든다 (문서에는 안 넣는다)."""
    _, _, frag, _ = find_one(xml, head)
    frag = _strip_ids(frag)
    runs = list(RUN.finditer(frag))
    assert runs, f"{head[:24]!r}: run 이 없음"
    m = re.search(r'<w:rPr\b.*?</w:rPr>', runs[0].group(0), re.DOTALL)
    rpr = m.group(0) if m else ""
    new_run = f'<w:r>{rpr}<w:t xml:space="preserve">{_esc(text)}</w:t></w:r>'
    return frag[: runs[0].start()] + new_run + frag[runs[-1].end():]


def insert_table_after(xml, head, caption_ko, caption_en, rows,
                       src_index=2, ko_tpl="표 3 다섯 방식의", en_tpl="Table 3 Total emissions",
                       widths=None):
    """head 문단 바로 뒤에 [국문 캡션, 영문 캡션, 표] 를 끼운다.

    JOK 10항이 표 제목을 표 위에 두라고 하므로 캡션이 앞선다. 캡션 서식은
    표 3 의 것을 본뜬다(국문은 rPr 없이 본문 크기, 영문은 sz 15 = 7.5pt).
    """
    ko = _clone_para(xml, ko_tpl, caption_ko)
    en = _clone_para(xml, en_tpl, caption_en)
    tbl = clone_table(xml, src_index, rows)
    if widths:
        tbl = set_table_widths(tbl, widths)
    s, e, _, _ = find_one(xml, head)
    return xml[:e] + ko + en + tbl + xml[e:]


def replace_substring(xml, head, target, repl):
    """문단 안 특정 글자를 다른 글자로 바꾼다 — run 서식은 그대로 둔다.

    delete_substring 과 같은 방식으로 run 들을 가로질러 target 을 찾되, 지우기만
    하지 않고 **target 이 처음 걸친 run 에** repl 을 써 넣는다. 표·그림 번호를
    다시 매길 때처럼 "한 낱말만 갈아끼우는" 일에 쓴다 (문단을 다시 쓰지 않으므로
    기울임·메모 표식이 살아남는다).
    """
    s, e, frag, _ = find_one(xml, head)
    runs = list(RUN.finditer(frag))
    assert runs, f"{head[:24]!r}: run 이 없음"

    texts, spans, pos = [], [], 0
    for r in runs:
        t = "".join(re.findall(r'<w:t\b[^>]*>(.*?)</w:t>', r.group(0), re.DOTALL))
        texts.append(t)
        spans.append((pos, pos + len(t)))
        pos += len(t)
    whole = "".join(texts)
    assert whole.count(target) == 1, \
        f"{head[:24]!r}: {target!r} 가 {whole.count(target)}번 (1번이어야 함)"
    i = whole.find(target)
    j = i + len(target)

    hit = [(k, r) for k, r in enumerate(runs) if not (spans[k][1] <= i or spans[k][0] >= j)]
    assert hit, "걸친 run 이 없음"
    first_k = hit[0][0]
    new_frag = frag
    for k, r in reversed(hit):
        a, b = spans[k]
        keep = texts[k][: max(0, i - a)] + (repl if k == first_k else "") + texts[k][max(0, j - a):]
        rf = r.group(0)
        if keep == "":
            new_frag = new_frag[:r.start()] + new_frag[r.end():]
            continue
        ts = list(re.finditer(r'(<w:t\b[^>]*>)(.*?)(</w:t>)', rf, re.DOTALL))
        assert len(ts) == 1, f"{head[:24]!r}: run 안 <w:t> 가 {len(ts)}개"
        t = ts[0]
        new_rf = rf[:t.start()] + f'<w:t xml:space="preserve">{_esc(keep)}</w:t>' + rf[t.end():]
        new_frag = new_frag[:r.start()] + new_rf + new_frag[r.end():]
    return xml[:s] + new_frag + xml[e:]


def insert_para_after(xml, head, text, style_from):
    """head 문단 뒤에, style_from 문단의 서식을 입은 새 문단을 끼운다.

    insert_after 는 **앵커와 같은 서식** 을 쓴다. 부록처럼 "참고문헌 항목 뒤에
    본문 서식 문단을 넣어야" 하는 자리에서는 그게 맞지 않아, 서식을 다른
    문단에서 따로 떠 온다.
    """
    para = _clone_para(xml, style_from, text)
    s, e, _, _ = find_one(xml, head)
    return xml[:e] + para + xml[e:]
