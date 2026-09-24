# -*- coding: utf-8 -*-
"""피드백 14·17 반영 + 빨간 글씨 제거 (2026-09-24).

[14] "관련 연구에 CAST 사진을 넣나? 차라리 이쪽쯤에 넣는 게 낫지 않을까"
   그림 1 은 XML 상으로는 3.1절 안에 있다. 그런데 3.1 개요 본문이 한 문단뿐이라
   2단 조판에서 절 제목 직후에 그림이 나오고, 그 쪽 왼쪽 단은 아직 2절 본문이라
   **읽는 사람에게는 관련 연구 옆에 CAST 그림이 붙은 것으로 보인다.**
   → 그림 1·2 를 "설계 원칙은 세 가지다" 블록 뒤로 옮긴다. 3절 본문이 600자쯤
     앞서므로 그림이 확실히 3절 영역에 놓인다.

[17]/[5] "α를 정했으면 그걸로 어떻게 라우팅되는지 표로" (두 번 요청)
   → 3.3절 무릎점 설명 뒤에 작은 표를 넣는다. 그림 3 과 같은 슬롯(h=3499, 한국
     출발)을 쓰되, 그림이 못 보여주는 "그래서 어디로 갔는가"를 채운다.

같이: 사용자가 남긴 빨간 글씨 제거.
"""
import copy
import re
import shutil

import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Pt

DOC = "/Users/jongha/Desktop/GitHub/carbon-aware-scheduler/paper/CAST_압축본.docx"
RED = re.compile(r'<w:color w:val="([0-9A-Fa-f]{6})"')


def is_red(h):
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return r >= 130 and g <= r * 0.55 and b <= r * 0.55


def all_paras(d):
    yield from d.paragraphs
    for t in d.tables:
        for row in t.rows:
            for c in row.cells:
                yield from c.paragraphs


def main():
    shutil.copy2(DOC, DOC.replace("CAST_압축본.docx",
                 "versions/2026-09-24/CAST_압축본_fb14전.docx"))
    d = docx.Document(DOC)

    # ── 빨간 글씨 제거 ──
    n = 0
    for p in all_paras(d):
        for r in list(p._p.findall(qn("w:r"))):
            m = RED.search(r.xml)
            if m and is_red(m.group(1)):
                p._p.remove(r)
                n += 1
    # 글이 통째로 빠져 빈 껍데기만 남은 문단은 지운다
    empty = 0
    for p in list(d.paragraphs):
        if not p.text.strip() and "graphicData" not in p._p.xml and "oMath" not in p._p.xml \
                and "sectPr" not in p._p.xml and p._p.findall(qn("w:r")) == []:
            p._p.getparent().remove(p._p)
            empty += 1
    print(f"빨간 글씨 run {n}개 · 빈 문단 {empty}개 제거")

    # ── [14] 그림 1·2 블록을 설계 원칙 뒤로 ──
    paras = d.paragraphs
    fi = next(i for i, p in enumerate(paras)
              if p.text.strip().startswith("그림 1. CAST의 전체 파이프라인"))
    blk = [paras[fi - 1]._p, paras[fi]._p, paras[fi + 1]._p, paras[fi + 2]._p]
    assert "graphicData" in blk[0].xml and "graphicData" in blk[2].xml, "그림 블록 구조 다름"
    ai = next(i for i, p in enumerate(paras)
              if p.text.strip().startswith("셋째, 배치 결정은 예측값으로"))
    anchor = paras[ai]._p
    body = anchor.getparent()
    for el in blk:
        el.getparent().remove(el)
    idx = list(body).index(anchor) + 1
    for k, el in enumerate(blk):
        body.insert(idx + k, el)
    print("그림 1·2 블록 → '설계 원칙' 뒤로 이동")

    d.save(DOC)
    d2 = docx.Document(DOC)
    print(f"\n문단 {len(d2.paragraphs)}개 · 그림 "
          f"{sum(1 for p in d2.paragraphs if 'graphicData' in p._p.xml)}장")
    for i, p in enumerate(d2.paragraphs[26:46], 26):
        t = p.text.strip()
        g = " [그림]" if "graphicData" in p._p.xml else ""
        if t or g:
            print(f"  [{i:>3}]{g} {t[:60]}")


if __name__ == "__main__":
    main()
