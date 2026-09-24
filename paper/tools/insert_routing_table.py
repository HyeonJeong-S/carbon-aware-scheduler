# -*- coding: utf-8 -*-
"""[5]/[17] α → 라우팅 표 삽입 (사용자가 두 번 요청).

사용자: "뭔가 알파를 정했는데, 이걸 토대로 어떻게 라우팅되는지도 알려 줬으면
좋겠어! 예를 들어 α가 정해졌을 때 어떤 식으로 나라가 정해지고, 또 용량을 통해서
어떻게 되는지 표로..?"  → 며칠 뒤 다시: "내가 표 이야기 했던 거 같은데."

그림 3이 산점도로 '어디에 무엇이 있는가'는 보여주지만 '그래서 어디로 갔는가'가
없었다. 그 빈자리를 채운다. 그림 3과 **같은 슬롯**(h=3499, 한국 출발)을 써서
두 그림·표가 같은 장면을 말하게 한다.

수치는 논문 3.3절의 정규화·점수식을 그대로 적용해 뽑았다(탄소는 그 슬롯 최댓값,
지연은 244 ms 로 정규화; score = α·C̃ + (1−α)·ℓ̃).
"""
import copy
import shutil

import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Pt

DOC = "/Users/jongha/Desktop/GitHub/carbon-aware-scheduler/paper/CAST_압축본.docx"

ROWS = [
    ("α", "배정 리전", "탄소", "지연"),
    ("0.0 – 0.4", "한국 (홈)", "351", "0"),
    ("0.5 – 0.8", "캘리포니아", "14", "134"),
    ("1.0", "프랑스", "9", "238"),
]
CAP = ("표 2. 가중치 α 에 따른 배정 변화 — 그림 3과 같은 슬롯(한국 출발)이다. α가 커질수록 "
       "목적지가 홈에서 중간 지점을 거쳐 최저 탄소 리전으로 옮겨간다. 이 슬롯의 무릎점은 "
       "0.508로 가운데 구간에 들며, 여기서 탄소는 홈 대비 96% 줄고 지연은 상한의 55%만 쓴다. "
       "실제 배정은 리전별 잔여 용량 avail_r 안에서만 이루어지므로, 같은 α라도 그 슬롯에 "
       "자리가 없으면 다음 후보로 넘어간다.")
LEAD = ("가중치가 배정을 어떻게 바꾸는지는 한 슬롯을 열어 보면 분명하다. 표 2는 그림 3과 같은 "
        "슬롯에서 α를 0에서 1까지 옮겼을 때 목적지가 어떻게 달라지는지 보인 것이다. 세 구간으로 "
        "갈리며, 무릎점은 그 가운데 구간을 고른다.")


def main():
    shutil.copy2(DOC, DOC.replace("CAST_압축본.docx",
                 "versions/2026-09-24/CAST_압축본_라우팅표전.docx"))
    d = docx.Document(DOC)
    paras = d.paragraphs

    # 삽입 위치: 3.3절 "평균적으로 같은 가중치(α≈0.508)를 쓰는 셈이지만…" 뒤
    ai = next(i for i, p in enumerate(paras)
              if p.text.strip().startswith("평균적으로 같은 가중치"))
    anchor = paras[ai]
    proto = anchor
    cap_proto = next(p for p in paras if p.text.strip().startswith("표 1."))
    src_tbl = d.tables[0]._tbl

    def clone_para(proto_p, text, size=9.0, align=None):
        el = copy.deepcopy(proto_p._p)
        p = docx.text.paragraph.Paragraph(el, proto_p._parent)
        for r in list(p._p.findall(qn("w:r"))):
            p._p.remove(r)
        r = p.add_run(text)
        r.font.size = Pt(size)
        r.bold = False
        if align is not None:
            p.alignment = align
        return p

    new = [clone_para(proto, LEAD, 9.0, WD_ALIGN_PARAGRAPH.JUSTIFY)]

    t = d.add_table(rows=len(ROWS), cols=4)
    old_pr = t._tbl.find(qn("w:tblPr"))
    if old_pr is not None:
        t._tbl.remove(old_pr)
    t._tbl.insert(0, copy.deepcopy(src_tbl.find(qn("w:tblPr"))))
    hdr = src_tbl.findall(qn("w:tr"))[0].findall(qn("w:tc"))[0].find(qn("w:tcPr"))
    W = [1120, 1500, 840, 840]
    from docx.oxml import OxmlElement
    for i, row in enumerate(ROWS):
        for j, val in enumerate(row):
            c = t.cell(i, j)
            if i == 0 and hdr is not None:
                cp = c._tc.find(qn("w:tcPr"))
                if cp is not None:
                    c._tc.remove(cp)
                c._tc.insert(0, copy.deepcopy(hdr))
            tcPr = c._tc.find(qn("w:tcPr"))
            if tcPr is None:
                tcPr = OxmlElement("w:tcPr")
                c._tc.insert(0, tcPr)
            e = OxmlElement("w:tcW")
            e.set(qn("w:w"), str(W[j]))
            e.set(qn("w:type"), "dxa")
            tcPr.append(e)
            c.text = ""
            p = c.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            rr = p.add_run(str(val))
            rr.font.size = Pt(7.5)
            rr.bold = (i == 0)
            if j >= 2:
                p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    t._tbl.getparent().remove(t._tbl)
    new.append(t._tbl)
    new.append(clone_para(cap_proto, CAP, 9.0))

    body = anchor._p.getparent()
    idx = list(body).index(anchor._p) + 1
    for k, el in enumerate(new):
        body.insert(idx + k, el._p if hasattr(el, "_p") else el)

    d.save(DOC)
    d2 = docx.Document(DOC)
    print(f"표 삽입 완료 — 표 {len(d2.tables)}개, 문단 {len(d2.paragraphs)}개")
    for p in d2.paragraphs:
        if p.text.strip().startswith("표 "):
            print("  ", p.text.strip()[:70])


if __name__ == "__main__":
    main()
