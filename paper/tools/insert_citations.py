# -*- coding: utf-8 -*-
"""압축본 본문에 [n] 인용 표시를 넣는다.

압축본에는 인용 표시가 한 건도 없었다(하이퍼링크 0, [n] 0). 위치 대조는
fd 가 인용포함본의 하이퍼링크 37개를 URL 로 역추적해 만들었다 —
paper/문서/인용위치_대조.txt.

번호는 **압축본에서의 첫 등장 순서**로 새로 매겼다. 참고문헌_초안.txt 의
17항목 중 셋([3]Google 24/7 CFE, [5]Asadov 리뷰, [13]CarbonCast 확장판)은
압축본이 그 내용을 말하지 않아 뺐다 — 인용되지 않는 항목을 목록에 두는 것은
서식 오류다. 반대로 셋([2]EU 지침, [11]DACF, [12]CarbonCast)은 본문이 근거
없이 주장하던 자리가 있어 짧은 구절과 함께 살렸다.

문단 번호가 아니라 **앵커 문자열**로 위치를 찾는다. 문단 번호는 편집마다
밀리므로 믿을 수 없다(fd 가 오프바이원을 경고했다).
"""
import shutil
import sys

import docx

DOC = "/Users/jongha/Desktop/GitHub/carbon-aware-scheduler/paper/CAST_압축본.docx"

# (앵커, 붙일 표시) — 앵커 바로 뒤에 삽입한다. 앵커는 문서에서 유일해야 한다.
MARKS = [
    # §1 서론
    ("AI를 가장 큰 요인으로 지목했다",              "[1]"),
    ("에너지 사용의 투명성이 규제 대상이 된 이상",     "[2]"),
    ("시간 축에서는 구글의 CICS",                   "[3]"),
    ("공간 축에서는 CASPER",                        "[4]"),
    ("와 VMware GSLB",                             "[5]"),
    ("두 축을 함께 다룬 Sukprasert 등의 상한 분석",   "[6]"),
    ("단일 클러스터 내 시간 이동에 한정된다",          "[7]"),
    ("단일 클러스터 맥락에서 지적했을 뿐",            "[7]"),
    # §2 관련 연구
    ("두 축을 결합한 분석에서는 용량을 두지 않았고",    "[6]"),
    ("자원이 항상 가용하다고 가정한다",               "[8]"),
    ("캘리포니아와 버지니아를 지목하였다",             "[6]"),
    ("결과가 달라질 것이라고 밝혔다",                 "[4]"),
    ("CICS 역시 탄소 비용과",                       "[3]"),
    ("신중하게 정해야 한다고 결론지었다",             "[9]"),
    ("마감은 목적함수의 페널티로 두는 소프트 제약이다", "[9]"),
    # §3 CAST
    ("전 지구 평균 절감이 8.4%에 그친다고 보고하였다", "[6]"),
    ("두 축을 결합한 분석에서는 도입하지 않았다",       "[6]"),
    # §4 실험과 분석
    ("Electricity Maps API를 통해 1시간 해상도로 수집하였다", "[10]"),
    ("전과정 배출계수 체계를 쓰는 공식 방법론이다",     "[11]"),
]

# 번호만 붙여서는 본문에 그 번호가 무엇인지 남지 않는 자리 — 구절을 함께 되살린다.
PHRASES = [
    # 압축 과정에서 "Azure 리전 간 왕복 지연 통계다"가 통째로 빠지고 숫자만 남았다
    ("비대각 최솟값은 12 ms다.",
     "비대각 최솟값은 12 ms이며, Azure 리전 간 왕복 지연 통계[12]에서 가져왔다."),
    # 예측 선행 연구가 압축본에서 모두 사라졌다 — 기여가 아님을 밝히는 자리에 되살린다
    ("예측 모듈 자체는 본 연구의 기여가 아니므로",
     "탄소집약도의 하루 앞 예측은 선행 연구가 따로 다룬 문제이며[13], 예측 모듈 "
     "자체는 본 연구의 기여가 아니므로"),
    # 향후 과제의 "24시간을 넘는 예측 지평"이 가리키는 선행 연구
    ("24시간을 넘는 예측 지평",
     "24시간을 넘는 예측 지평[14]"),
]


def _edit(ps, anchor, repl_of_anchor):
    """앵커를 찾아 그 자리를 repl_of_anchor 로 바꾼다. 문서 전체에서 1회만 일치해야 한다."""
    hits = []
    for i, p in enumerate(ps):
        if anchor in p.text:
            hits.append(i)
    if len(hits) != 1:
        raise AssertionError(f"앵커가 {len(hits)}곳에서 일치: {anchor!r} → {hits}")
    p = ps[hits[0]]
    runs = p.runs
    acc = ""
    spans = []
    for r in runs:
        spans.append((len(acc), len(acc) + len(r.text)))
        acc += r.text
    k = acc.find(anchor)
    e = k + len(anchor)
    t = [j for j, (a, b) in enumerate(spans) if b > k and a < e]
    runs[t[0]].text = acc[spans[t[0]][0]:k] + repl_of_anchor + acc[e:spans[t[-1]][1]]
    for j in t[1:]:
        runs[j]._r.getparent().remove(runs[j]._r)
    return hits[0]


def main():
    out = DOC
    if len(sys.argv) > 1:
        out = sys.argv[1]
        shutil.copy2(DOC, out)
    d = docx.Document(out)
    ps = d.paragraphs
    n0 = len(ps)
    figs0 = sum("<w:drawing" in p._p.xml for p in ps)
    eqs0 = sum(p._p.xml.count("<m:oMath>") for p in ps)

    for anchor, new in PHRASES:
        i = _edit(ps, anchor, new)
        print(f"  구절 복원 [{i}] {anchor[:30]}…")
    for anchor, mark in MARKS:
        i = _edit(ps, anchor, anchor + mark)
        print(f"  {mark:<5} [{i}] …{anchor[-26:]}")

    d.save(out)
    d2 = docx.Document(out)
    import re
    got = sorted({int(x) for p in d2.paragraphs for x in re.findall(r"\[(\d+)\]", p.text)})
    print(f"\n문단 {n0}→{len(d2.paragraphs)} · "
          f"그림 {figs0}→{sum('<w:drawing' in p._p.xml for p in d2.paragraphs)} · "
          f"수식 {eqs0}→{sum(p._p.xml.count('<m:oMath>') for p in d2.paragraphs)}")
    print("본문에 등장한 번호:", got)
    missing = [n for n in range(1, 15) if n not in got]
    print("목록에만 있고 본문에 없는 번호:", missing or "없음")


if __name__ == "__main__":
    main()
