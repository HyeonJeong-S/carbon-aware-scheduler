# -*- coding: utf-8 -*-
"""apply_stage18.py / apply_stage18b.py 의 앵커 프래그먼트를 라이브 CAST.docx 기준으로 재동기화.

왜 필요한가
-----------
두 스크립트는 문단 XML 조각을 통째로 저장해두고 exact match 로 찾는다. 그래서
CAST.docx 의 해당 문단을 조금만 손대도(서식 속성 하나만 추가해도) 앵커가 깨진다.
2026-09-23 하루에만 세 번 깨졌다(τ_j 정의 추가, §1 인과중복 병합, 들여쓰기 전환).

무엇을 보존하는가
-----------------
REPLACEMENTS 의 (old -> new) 는 "old 에서 인용 장치에 해당하는 연속 구간을
잘라낸다"는 규칙이다. 이 스크립트는 그 잘라낸 구간을 old/new 비교로 역산한 뒤,
같은 구간을 라이브 문단에서 찾아 똑같이 잘라 새 new 를 만든다. 즉 규칙 자체는
사람이 정한 그대로 두고, 문단 본문만 최신으로 갈아끼운다.

안전장치: 잘라낼 구간이 라이브 문단에 정확히 1번 없으면 그 항목은 건너뛰고
보고한다(임의 추측 금지). 실행 후 반드시 --dry-run 으로 재확인할 것.
"""
import re
import sys
import zipfile

REPO = "/Users/jongha/Desktop/GitHub/carbon-aware-scheduler"
DOCX = f"{REPO}/paper/CAST.docx"
PARA = re.compile(r'<w:p\b[^>]*?/>|<w:p\b[^>]*?(?<!/)>.*?</w:p>', re.DOTALL)


def live_paragraphs():
    xml = zipfile.ZipFile(DOCX).read("word/document.xml").decode("utf-8")
    out = {}
    for m in PARA.finditer(xml):
        pid = re.search(r'w14:paraId="([0-9A-Fa-f]{8})"', m.group(0))
        if pid:
            out[pid.group(1).upper()] = m.group(0)
    return out


def unesc(s):
    """소스에 적힌 문자열 리터럴 본문 -> 실제 문자열."""
    return s.replace("\\\\", "\x00").replace("\\'", "'").replace("\x00", "\\")


def esc(s):
    """실제 문자열 -> 작은따옴표 리터럴 안에 넣을 수 있는 형태."""
    return s.replace("\\", "\\\\").replace("'", "\\'")


def cut_span(old, new):
    """old -> new 로 가면서 삭제된 연속 구간을 돌려준다(없으면 None)."""
    i = 0
    while i < min(len(old), len(new)) and old[i] == new[i]:
        i += 1
    j = 0
    while j < min(len(old), len(new)) - i and old[len(old)-1-j] == new[len(new)-1-j]:
        j += 1
    removed = old[i:len(old)-j]
    # new 는 old 에서 removed 만 빠진 형태여야 한다
    if old[:i] + old[len(old)-j:] != new:
        return None
    return removed


def resync(path):
    src = open(path, encoding="utf-8").read()
    live = live_paragraphs()
    fixed = skipped = unchanged = 0
    report = []

    # (paraid, old, new) 3-튜플
    for m in list(re.finditer(r"\('([0-9A-F]{8})', '((?:[^'\\]|\\.)*)', '((?:[^'\\]|\\.)*)'\)", src)):
        pid, old, new = m.group(1), unesc(m.group(2)), unesc(m.group(3))
        if pid not in live:
            report.append(f"  SKIP {pid}: 라이브 문서에 없음"); skipped += 1; continue
        if old == live[pid]:
            unchanged += 1; continue
        removed = cut_span(old, new)
        if removed is None:
            report.append(f"  SKIP {pid}: old->new 가 단순 구간삭제가 아님"); skipped += 1; continue
        if live[pid].count(removed) != 1:
            report.append(f"  SKIP {pid}: 삭제구간이 라이브에 {live[pid].count(removed)}번"); skipped += 1; continue
        src = src.replace(m.group(0),
                          f"('{pid}', '{esc(live[pid])}', '{esc(live[pid].replace(removed, '', 1))}')", 1)
        fixed += 1

    # (paraid, old) 2-튜플 = WHOLE_DELETIONS
    for m in list(re.finditer(r"\('([0-9A-F]{8})', '((?:[^'\\]|\\.)*)'\),", src)):
        pid, old = m.group(1), unesc(m.group(2))
        if pid not in live or old == live[pid]:
            continue
        src = src.replace(m.group(0), f"('{pid}', '{esc(live[pid])}'),", 1)
        fixed += 1

    open(path, "w", encoding="utf-8").write(src)
    print(f"{path.split('/')[-1]}: 갱신 {fixed} / 변화없음 {unchanged} / 건너뜀 {skipped}")
    for line in report:
        print(line)
    return skipped


if __name__ == "__main__":
    total_skipped = 0
    for p in (f"{REPO}/paper/tools/apply_stage18.py", f"{REPO}/paper/tools/apply_stage18b.py"):
        total_skipped += resync(p)
    print("\n반드시 --dry-run 으로 재확인할 것.")
    sys.exit(1 if total_skipped else 0)
