# -*- coding: utf-8 -*-
"""v3 장별 원고(paper/v3/원고/*.txt) → docx. 조립은 build_v2_docx 를 그대로 쓴다(v1 Word 문서의 문단을 서식 틀로 복제).
장 하나만 조립하므로 제목·초록·주제어 단락은 뺀다.
    ./.venv/bin/python paper/tools/build_v3_docx.py --in paper/v3/원고/03_CAST.txt --out paper/v3/CAST_JOK_v3_3장.docx
"""
import argparse, os, re

import docx
from docx.oxml.ns import qn

import build_v2_docx as b

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
b.DRAFT = os.path.join(ROOT, "paper", "v3", "원고")     # 식은 v3/원고/omml/eq{n}.xml 에서 읽는다
b.DIAG = os.path.join(ROOT, "paper", "v3", "그림")      # v3 그림은 v3/그림/ 에 따로 둔다(원본 생성 스크립트는 paper/diagram)
b.EQ_CENTER = {3: 1956}                                  # v2 식 (6) = v3 식 (3): 단 가운데 탭
b.EQ_BR_INDENT = {7: 1100}                               # v2 식 (12) = v3 식 (7): 둘째 줄 들여쓰기
b.ALG_KR = {1: "CAST의 슬롯별 배정"}

TITLE = {"제목": "CAST: 리전 용량 제약을 고려한 탄소 인지 시공간 워크로드 스케줄링",
         "Title": "CAST: Carbon-Aware Spatio-Temporal Scheduling under Capacity Constraints"}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="src", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--shift", default="", help="그림·알고리즘 자리 옮김: fig1=19,alg1=-8")
    a = ap.parse_args()
    parse = b.parse
    def parse_with_title(path):
        head, blocks = parse(path)
        for k in ("초록", "주제어", "Abstract", "Keywords"): head.setdefault(k, "")
        for k, v in TITLE.items(): head.setdefault(k, v)
        return head, blocks
    b.parse = parse_with_title
    sh = {}
    for x in filter(None, a.shift.split(",")):
        k, d = x.strip().split("="); sh[(k.rstrip("0123456789"), int(k.lstrip("figtblalg")))] = int(d)
    b.build(a.src, a.out, sh)
    d = docx.Document(a.out); body = d.element.body
    for e in list(body):                                 # 장 하나만 조립하므로 제목부(제목·초록·주제어)는 첫 장 제목 앞에서 모두 뺀다
        t = "".join(x.text or "" for x in e.iter(qn("w:t"))).strip()
        if re.match(r"^\d+\. ", t): break
        if e.tag == qn("w:p"): body.remove(e)
    for t in d.tables:                                   # 첫 칸만 있는 줄은 묶음 머리(Synthetic, Ceiling 등) — 기울임으로 구분
        for row in t.rows[1:]:
            cs = row.cells
            if len(cs) > 1 and cs[0].text.strip() and not any(c.text.strip() for c in cs[1:]):
                for r in cs[0].paragraphs[0].runs: r.italic = True
    d.save(a.out)
    print("saved", a.out)

if __name__ == "__main__":
    main()
