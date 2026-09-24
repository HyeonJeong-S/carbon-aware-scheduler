# -*- coding: utf-8 -*-
"""절 구조를 표준 형식으로 재배치 (2026-09-24, 사용자 지시).

사용자가 준 형식:
    Abstract / 1. Introduction / 2. Related Work / 3. CAST /
    4. Experiments and Analysis / 5. Discussion and Limitations /
    6. Conclusion / References

압축본은 §2 배경지식·§3 문제정의를 잘라내면서 1 다음에 바로 4가 나오고,
5.3 과 6.2 자리도 비어 있었다. 이 판에서 번호를 다시 붙여 구멍을 없앤다.

  4. 관련 연구와 그 한계  →  2. 관련 연구
  5. 제안하는 방법        →  3. CAST
    5.1 → 3.1  5.2 → 3.2  5.4 → 3.3  5.5 → 3.4  5.6 → 3.5  5.7 → 3.6
  6. 검증                 →  4. 실험과 분석
    6.1 → 4.1  6.3 → 4.2  6.4 → 4.3  6.5 → 4.4
  7. 결론                 →  5. 논의와 한계  +  6. 결론 (둘로 나눔)

주의 — 본문의 "6.4절"이 두 뜻으로 쓰인다. 하나는 본 논문의 절이고 하나는
Sukprasert 논문의 절이다. 후자는 절대 바꾸면 안 되므로 문맥으로 가른다.

같이 처리: 사용자가 남긴 빨간 글씨 의견을 전부 제거한다(반영은 별도).
"""
import copy
import re
import shutil

import docx
from docx.oxml.ns import qn
from docx.shared import Pt

DOC = "/Users/jongha/Desktop/GitHub/carbon-aware-scheduler/paper/CAST_압축본.docx"

HEAD = [
    ("4. 관련 연구와 그 한계", "2. 관련 연구"),
    ("5. 제안하는 방법", "3. CAST"),
    ("5.1 개요", "3.1 개요"),
    ("5.2 표기와 형식화", "3.2 표기와 형식화"),
    ("5.4 공간 이동", "3.3 공간 이동"),
    ("5.5 시간 이동", "3.4 시간 이동"),
    ("5.6 용량 인지 온라인 시간 이동", "3.5 용량 인지 온라인 시간 이동"),
    ("5.7 탄소 회계", "3.6 탄소 회계"),
    ("6. 검증", "4. 실험과 분석"),
    ("6.1 실험 설정", "4.1 실험 설정"),
    ("6.3 주요 결과", "4.2 주요 결과"),
    ("6.4 용량 제약과 시간 이동", "4.3 용량 제약과 시간 이동"),
    ("6.5 선행 정책 재현 비교", "4.4 선행 정책 재현 비교"),
    ("7. 결론", "6. 결론"),
]

# 상호참조 — 표기도 "N.N절"로 통일한다(§ 와 절 이 섞여 있었다)
XREF = [
    ("§5.2", "3.2절"), ("§5.4", "3.3절"), ("§5.5", "3.4절"), ("§5.6", "3.5절"),
    ("§5.7", "3.6절"), ("§6.3", "4.2절"), ("§6.4", "4.3절"), ("§6.5", "4.4절"),
    ("5.6절", "3.5절"), ("5.5절", "3.4절"), ("5.4절", "3.3절"), ("5.2절", "3.2절"),
    ("6.3절", "4.2절"), ("6.5절", "4.4절"),
]
RED = re.compile(r'<w:color w:val="([0-9A-Fa-f]{6})"')


def is_red(h):
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return r >= 130 and g <= r * 0.55 and b <= r * 0.55


def strip_red(p):
    """이 문단에서 빨간 글씨 run 을 전부 지운다."""
    n = 0
    for r in list(p._p.findall(qn("w:r"))):
        m = RED.search(r.xml)
        if m and is_red(m.group(1)):
            p._p.remove(r)
            n += 1
    return n


def main():
    shutil.copy2(DOC, DOC.replace("CAST_압축본.docx",
                 "versions/2026-09-24/CAST_압축본_재배치전.docx"))
    d = docx.Document(DOC)

    # ── 1) 빨간 글씨 제거 ──
    red = sum(strip_red(p) for p in d.paragraphs)
    print(f"빨간 글씨 run {red}개 제거")

    # ── 2) 절 제목 ──
    for old, new in HEAD:
        hit = False
        for p in d.paragraphs:
            t = p.text.strip()
            if t.startswith(old):
                for r in p.runs:
                    if old.split()[0] in r.text:
                        r.text = r.text.replace(old.split()[0], new.split()[0], 1)
                        hit = True
                        break
                if not hit and p.runs:            # run 이 쪼개진 경우
                    txt = t.replace(old, new, 1)
                    for r in p.runs:
                        r.text = ""
                    p.runs[0].text = txt
                    hit = True
                print(f"  {old[:28]:<30} → {new}")
                break
        if not hit:
            print(f"  [못 찾음] {old}")

    # ── 3) 상호참조 ──
    # "Sukprasert 등(EuroSys'24) 6.4절" 은 남의 논문 절이므로 손대지 않는다.
    changed = 0
    for p in d.paragraphs:
        t = p.text
        if "Sukprasert 등(EuroSys" in t:
            continue
        for old, new in XREF:
            if old in t:
                for r in p.runs:
                    if old in r.text:
                        r.text = r.text.replace(old, new)
                        changed += 1
    print(f"상호참조 {changed}곳 갱신")

    # ── 4) §7 을 5(논의와 한계) + 6(결론) 으로 나눈다 ──
    paras = d.paragraphs
    ci = next(i for i, p in enumerate(paras) if p.text.strip().startswith("6. 결론"))
    li = next(i for i, p in enumerate(paras) if p.text.strip().startswith("한계는 네 가지다"))
    head_proto = paras[ci]

    new_h = docx.text.paragraph.Paragraph(copy.deepcopy(head_proto._p), head_proto._parent)
    for r in list(new_h._p.findall(qn("w:r"))):
        new_h._p.remove(r)
    r = new_h.add_run("5. 논의와 한계")
    r.bold = True
    r.font.size = Pt(10)

    body = paras[li]._p.getparent()
    body.insert(list(body).index(paras[li]._p), new_h._p)

    # 결론 제목을 한계 뒤로 옮긴다 — 순서: 5.논의와 한계 / 한계 / 향후 / 6.결론 / 요약
    summ = paras[ci + 1]                      # "본 논문은 … 제안하였다"
    sweep = paras[ci + 2]                     # 용량 스윕
    for el in (head_proto._p, summ._p, sweep._p):
        el.getparent().remove(el)
    last = paras[-1]._p
    parent = last.getparent()
    idx = list(parent).index(last) + 1
    for k, el in enumerate((head_proto._p, summ._p, sweep._p)):
        parent.insert(idx + k, el)
    print("§7 을 5(논의와 한계) + 6(결론) 으로 분리")

    d.save(DOC)
    d2 = docx.Document(DOC)
    print("\n=== 새 절 구성 ===")
    for p in d2.paragraphs:
        t = p.text.strip()
        if re.match(r"^\d+(\.\d+)?\s+\S", t) and len(t) < 40:
            print("  ", t)


if __name__ == "__main__":
    main()
