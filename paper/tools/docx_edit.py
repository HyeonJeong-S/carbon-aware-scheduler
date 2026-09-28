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
