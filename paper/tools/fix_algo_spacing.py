# -*- coding: utf-8 -*-
"""[8] Algorithm 1 과 수식의 줄 간격 (사용자 지적).

사용자: "이부분이 뭔가 줄이나 이런 게 그냥 너무 모여있는 거 같아서 위에 부분
읽기가 어려움. 아마도 페이지를 줄이기 위해서 한 거 같음."

맞는 추정이다. 분량을 맞추느라 수식 문단에 여백을 주지 않았고, Algorithm 1 은
16줄이 줄간격 없이 붙어 있어 덩어리로 보인다. 읽는 사람이 어디서 끊어 읽을지
모른다.

조치
  · Algorithm 1 문단: 줄 간격 1.12 — 16줄이 숨 쉰다
  · 수식 문단: 앞뒤 3pt — 본문과 수식의 경계가 보인다
쪽수가 늘면 본문에서 그만큼 덜어낸다. 읽기가 분량보다 앞선다.
"""
import re
import shutil

import docx
from docx.shared import Pt

DOC = "/Users/jongha/Desktop/GitHub/carbon-aware-scheduler/paper/CAST_압축본.docx"
EQ = re.compile(r"…\s*\(\d{1,2}\)\s*$")


def main():
    shutil.copy2(DOC, DOC.replace("CAST_압축본.docx",
                 "versions/2026-09-24/CAST_압축본_간격전.docx"))
    d = docx.Document(DOC)
    n_eq = n_alg = 0
    for p in d.paragraphs:
        t = p.text.strip()
        if t.startswith("Algorithm 1"):
            pf = p.paragraph_format
            pf.line_spacing = 1.12
            pf.space_before = Pt(4)
            pf.space_after = Pt(4)
            n_alg += 1
        elif EQ.search(t):
            pf = p.paragraph_format
            pf.space_before = Pt(3)
            pf.space_after = Pt(3)
            n_eq += 1
    d.save(DOC)
    print(f"  Algorithm 1 {n_alg}개 줄간격 1.12 · 수식 {n_eq}개 앞뒤 3pt")


if __name__ == "__main__":
    main()
