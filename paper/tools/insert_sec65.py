# -*- coding: utf-8 -*-
"""§6.5 선행 정책 재현 비교 절을 압축본에 삽입 (표 + 그림 7 + 프로즈).

초안: fd 세션(paper/문서/벤치마크절_초안.txt). 숫자는 2d 가 공용 채점기
(scheduler/prior_harness.py, §5.7 식(16) 회계)로 전건 재검증한 값이다.
Caspian 행은 실험이 끝나지 않아 비워둔다 — 추정치를 넣지 않는다.

삽입 위치: §7 결론 바로 앞. python-docx 로 문단·표·그림을 만들고 XML 수준에서
결론 앞으로 옮긴다. 기존 문단은 건드리지 않는다.
"""
import copy
import shutil

import docx
from docx.oxml.ns import qn
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt

REPO = "/Users/jongha/Desktop/GitHub/carbon-aware-scheduler/"
DOC = REPO + "paper/CAST_압축본.docx"
FIG = REPO + "paper/diagram/fig7_benchmark.png"

ROWS = [
    ("정책", "총배출(kg)", "절감률", "위반(건)"),
    ("기준 — 홈 리전 즉시 실행", "29,225.6", "—", "0"),
    ("CICS 가상 용량 곡선", "25,203.4", "13.76%", "0"),
    ("본 연구 — 시간 이동만", "23,789.1", "18.60%", "24"),
    ("본 연구 — 공간 이동만", "12,609.8", "56.85%", "0"),
    ("본 연구 — 전체(온라인 용량 인지)", "10,805.0", "63.03%", "227"),
    ("본 연구 — 시간 무제약(반사실)", "9,958.2", "65.93%", "20,208"),
    ("Sukprasert — 시간(완전예지)", "9,583.6", "67.21%", "49,356"),
    ("CASPER CAP(α=0.9)", "1,379.1", "95.28%", "69,310"),
    ("Sukprasert — 공간+시간(완전예지)", "990.8", "96.61%", "120,186"),
]

PROSE = [
 "CICS·CASPER·Sukprasert의 정책을 원문의 수식과 공개 코드 그대로 본 연구의 데이터 위에 "
 "다시 구현하고, 동일한 회계(식 (16))로 채점하였다. 구현 판단과 세부 파라미터는 추가자료에 "
 "정리하였다.",

 "절감률만 보면 CASPER(95.28%)와 Sukprasert의 완전예지 정책(96.61%)이 본 연구(63.03%)를 "
 "앞선다. 다만 절감률이 커지는 순서는 용량 상한 위반이 커지는 순서와 정확히 겹친다. CASPER의 "
 "지연·용량 제약은 본 연구의 워크로드 규모에서 수학적으로 항상 느슨하다 — 리전 간 최대 지연 "
 "244 ms가 상한 500 ms보다 작고, 시간당 최대 수요 38건이 리전 하나의 수용량 1,000건에 크게 "
 "못 미친다. 그래서 매 시간 전체 요청이 그 순간 가장 깨끗한 리전 하나로 몰리며, 평균 네트워크 "
 "지연은 120.4 ms로 본 연구 무릎점(36.2 ms)의 3.3배가 된다. Sukprasert의 상한은 미래 "
 "탄소집약도를 완전히 아는 오프라인 오라클을 전제하므로, 작업이 실시간으로 도착하는 온라인 "
 "시스템으로는 얻을 수 없는 값이다.",

 "같은 축으로 좁혀 보면 결과가 뒤집힌다. 홈 리전을 고정하고 시간만 옮기는 조건에서 CICS의 "
 "가상 용량 곡선은 13.76%에 그쳐 본 연구의 18.60%에 못 미친다. CICS는 하루 전에 산정한 "
 "시간별 자원 곡선 하나로 다음 날 전체를 처리해 개별 작업의 마감을 보지 못하는 반면, 본 "
 "연구는 슬롯마다 남은 여유를 다시 계산한다.",
]

CAPTION = ("그림 7. 탄소 절감률과 용량 상한 위반 — ★ 본 연구, ○ 선행 정책 재현. "
           "왼쪽 위가 좋은 자리이며, 본 연구를 앞서는 정책은 모두 오른쪽 바깥에 있다.")
TCAP = ("표 2. 선행 정책을 원문 그대로 재구현해 같은 회계로 채점한 결과. 위반은 본 연구의 "
        "유효 상한 K_r=12을 모든 정책에 같은 정의(6.4절)로 적용해 센 값이며, 각 정책이 그 "
        "상한을 지키도록 설계된 것은 아니다. Caspian은 재현 실험이 진행 중이다.")


def style(run, size=9, bold=False):
    run.font.size = Pt(size)
    run.bold = bold
    return run


def main():
    shutil.copy2(DOC, REPO + "paper/versions/2026-09-24/CAST_압축본_65삽입전.docx")
    d = docx.Document(DOC)

    # 기준: §7 결론 문단. d.paragraphs 는 호출할 때마다 새 객체를 만들므로
    # 한 번만 받아서 쓴다(index() 가 실패하는 원인이었다).
    paras = d.paragraphs
    target = ti = None
    for i, p in enumerate(paras):
        if p.text.strip().startswith("7. 결론"):
            target, ti = p, i
            break
    assert target is not None, "§7 결론을 찾지 못했다"
    body = target._p.getparent()
    idx = list(body).index(target._p)

    # 기존 본문 문단 서식을 그대로 물려받기 위해 앞 문단을 본뜬다
    proto = None
    for p in reversed(paras[:ti]):
        if len(p.text.strip()) > 80:
            proto = p
            break
    assert proto is not None

    new_elems = []

    def add_para(text, bold=False, align=None, size=9, from_proto=True):
        p = copy.deepcopy(proto._p) if from_proto else None
        np = d.add_paragraph()
        if p is not None:
            np._p.getparent().remove(np._p)
            np = docx.text.paragraph.Paragraph(p, proto._parent)
            for r in list(np._p.findall(docx.oxml.ns.qn("w:r"))):
                np._p.remove(r)
        r = np.add_run(text)
        style(r, size, bold)
        if align is not None:
            np.alignment = align
        new_elems.append(np._p)
        return np

    # 절 제목
    h = add_para("6.5 선행 정책 재현 비교", bold=True, size=10)

    for t in PROSE:
        add_para(t, align=WD_ALIGN_PARAGRAPH.JUSTIFY)

    # 표 — 기존 표(3선 booktabs 형식)의 서식을 그대로 물려받는다.
    # 이 문서에는 "Table Grid" 스타일이 없고, 학술지 관례대로 위·아래 선만 쓴다.
    t = d.add_table(rows=len(ROWS), cols=4)
    src = d.tables[0]._tbl
    old_pr = t._tbl.find(qn("w:tblPr"))
    if old_pr is not None:
        t._tbl.remove(old_pr)
    t._tbl.insert(0, copy.deepcopy(src.find(qn("w:tblPr"))))
    # 머리글 행 아래 가는 선 — 원본 표의 첫 행 셀 서식을 그대로 복사
    src_hdr = src.findall(qn("w:tr"))[0].findall(qn("w:tc"))[0].find(qn("w:tcPr"))
    for i, row in enumerate(ROWS):
        for j, cell in enumerate(row):
            c = t.cell(i, j)
            if i == 0 and src_hdr is not None:
                cpr = c._tc.find(qn("w:tcPr"))
                if cpr is not None:
                    c._tc.remove(cpr)
                c._tc.insert(0, copy.deepcopy(src_hdr))
            c.text = ""
            p = c.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            style(p.add_run(cell), 7.5, i == 0)
            if j > 0:
                p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    t._tbl.getparent().remove(t._tbl)
    new_elems.append(t._tbl)
    add_para(TCAP, size=7.5, align=WD_ALIGN_PARAGRAPH.LEFT)

    # 그림
    fp = d.add_paragraph()
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fp.add_run().add_picture(FIG, width=docx.shared.Pt(200))
    fp._p.getparent().remove(fp._p)
    new_elems.append(fp._p)
    add_para(CAPTION, size=7.5, align=WD_ALIGN_PARAGRAPH.LEFT)

    for k, el in enumerate(new_elems):
        body.insert(idx + k, el)

    d.save(DOC)
    d2 = docx.Document(DOC)
    n_fig = sum(1 for p in d2.paragraphs if "graphicData" in p._p.xml)
    print(f"삽입 완료 — 문단 {len(d2.paragraphs)}개, 그림 {n_fig}개, 표 {len(d2.tables)}개")


if __name__ == "__main__":
    main()
