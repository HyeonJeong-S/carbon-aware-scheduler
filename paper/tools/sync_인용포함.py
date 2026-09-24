# -*- coding: utf-8 -*-
"""CAST_압축본 의 초록·서론·결론 개정을 CAST_인용포함 에도 반영 (묶음 단위).

2026-09-24 1차 시도에서 낸 사고와 그 교훈
-------------------------------------
편집 항목을 낱개로 처리했더니, "여러 문단을 한 문단으로 합치는" 편집에서
합칠 **대상** 문단이 인용을 품고 있어 건너뛰어졌는데도 **재료** 문단들은
그대로 삭제되어, 인용포함본에서만 내용이 소실됐다(리전별 탄소집약도 수치
239자 등). 편집은 낱개가 아니라 **묶음**이다.

그래서 이 판은 GROUPS 단위로 처리한다 — 묶음의 대상 문단이 인용 때문에
건너뛰어지면 **그 묶음 전체를 건드리지 않는다**. 인용포함본은 분량 제한이
없으므로 원문이 그대로 남는 편이 안전하고, 두 판본이 그 문단에서만 달라지는
것은 설계상 허용된다(압축본=10쪽 본편, 인용포함=완전판).
"""
import sys
sys.path.insert(0, "/Users/jongha/Desktop/GitHub/carbon-aware-scheduler/paper/tools")
import docx_edit as D
from apply_abstract_intro import ABSTRACT, ABSTRACT_EN, INTRO
from apply_trim2 import EDITS

P = "/Users/jongha/Desktop/GitHub/carbon-aware-scheduler/paper/CAST_인용포함.docx"


def build_groups():
    """(대상 머리글, 새 텍스트, [함께 지울 머리글들]) 목록으로 재구성."""
    groups, cur = [], None
    for head, new in INTRO + EDITS:
        if new is not None:
            cur = [head, new, []]
            groups.append(cur)
        else:
            assert cur is not None, f"묶음 대상 없이 삭제 지시: {head!r}"
            cur[2].append(head)
    return [["초록", ABSTRACT, []], ["Abstract", ABSTRACT_EN, []]] + groups


def cited(xml, head):
    try:
        _, _, frag, _ = D.find_one(xml, head)
    except AssertionError:
        return None
    return "<w:hyperlink" in frag or "w:instrText" in frag


def main():
    z, xml = D.load(P)
    n0 = len(D.paragraphs(xml))
    before = sum(len(t) for *_, t in D.paragraphs(xml) if t)
    d0 = xml.count("<w:drawing>")
    removed = ok = skip = 0

    for head, new, drops in build_groups():
        c = cited(xml, head)
        if c is None:
            print(f"  [대상없음] {head[:32]}…")
            skip += 1
            continue
        if c:
            print(f"  [인용보존 → 묶음 전체 유지] {head[:26]}…"
                  + (f"  (동반 삭제 {len(drops)}건도 취소)" if drops else ""))
            skip += 1
            continue
        xml, o, n = D.replace_text(xml, head, new)
        print(f"  수정 {o:>4} → {n:>4}자  {head[:28]}…")
        for dh in drops:
            if cited(xml, dh):
                print(f"      [주의] 삭제 대상에 인용 있음, 남김: {dh[:26]}…")
                continue
            xml, od = D.delete(xml, dh)
            removed += 1
            print(f"      삭제 {od:>4}자  {dh[:28]}…")
        ok += 1

    after = sum(len(t) for *_, t in D.paragraphs(xml) if t)
    n1 = len(D.paragraphs(xml))
    assert n1 == n0 - removed, f"문단 수 이상 {n0}→{n1}"
    assert xml.count("<w:drawing>") == d0, "그림 손실"
    D.save(P, z, xml, -removed)
    print(f"\n묶음 적용 {ok} · 건너뜀 {skip} · 문단 삭제 {removed}")
    print(f"프로즈 {before:,} → {after:,}자 ({after-before:+,})")


if __name__ == "__main__":
    main()
