# -*- coding: utf-8 -*-
"""사용자가 docx 안에 남긴 피드백을 뽑아 읽는다.

세 가지 방식을 모두 읽는다 — 사용자가 어느 쪽을 쓰든 걸리게.
  1. 빨간 글씨      : run 의 <w:color w:val="FF0000"/> (또는 붉은 계열)
  2. 형광펜         : <w:highlight w:val="yellow"/> 등
  3. Word 메모      : word/comments.xml (검토 > 새 메모)
  4. 변경 내용 추적  : <w:ins>/<w:del>

각 피드백이 **어느 문단에 붙어 있는지**를 함께 낸다. 그래야 "여기 이상하다"가
어디를 가리키는지 알 수 있다.

실행: ./.venv/bin/python paper/tools/read_feedback.py [파일]
"""
import re
import os
import sys
import zipfile

# 색을 흰 목록으로 열거하면 반드시 새는 색이 나온다(실제로 EE0000 을 놓쳤다).
# "붉은 계열"을 값으로 판정한다 — R 이 충분히 크고 G·B 가 충분히 작으면 빨강.
_COLOR = re.compile(r'<w:color w:val="([0-9A-Fa-f]{6})"')


def _is_red(hexv):
    r, g, b = (int(hexv[i:i + 2], 16) for i in (0, 2, 4))
    return r >= 130 and g <= r * 0.55 and b <= r * 0.55


def _has_red(run):
    m = _COLOR.search(run)
    return bool(m) and _is_red(m.group(1))
HL = re.compile(r'<w:highlight w:val="(yellow|red|green|cyan|magenta)"', re.I)
RUN = re.compile(r'<w:r\b(?:(?!</w:r>).)*?</w:r>', re.DOTALL)
PARA = re.compile(r'<w:p\b[^>]*?/>|<w:p\b[^>]*?(?<!/)>.*?</w:p>', re.DOTALL)


def text_of(x):
    return re.sub(r"<[^>]+>", "", x).strip()


def main(path):
    z = zipfile.ZipFile(path)
    names = set(z.namelist())
    xml = z.read("word/document.xml").decode("utf-8")
    found = 0

    print(f"═══ {path.split('/')[-1]} ═══\n")

    # ── 1·2. 빨간 글씨 / 형광펜 ──
    # Word 는 한 번에 입력한 글도 어절 단위 run 으로 쪼개 저장한다. run 마다
    # 출력하면 같은 문장이 수십 번 나오므로, **이어진 같은 종류의 run 을 하나로
    # 합쳐서** 한 덩어리를 한 건으로 센다.
    for pi, m in enumerate(PARA.finditer(xml)):
        frag = m.group(0)
        ptxt = text_of(frag)
        runs = []
        for r in RUN.finditer(frag):
            run = r.group(0)
            kind = "빨간 글씨" if _has_red(run) else ("형광펜" if HL.search(run) else None)
            runs.append((kind, re.sub(r"<[^>]+>", "", run)))
        # 이어진 덩어리로 묶기
        i = 0
        while i < len(runs):
            if runs[i][0] is None:
                i += 1
                continue
            kind = runs[i][0]
            j = i
            buf = []
            while j < len(runs) and runs[j][0] == kind:
                buf.append(runs[j][1])
                j += 1
            t = "".join(buf).strip()
            if t:
                found += 1
                ctx = ptxt.replace(t, " ◀여기▶ ", 1)
                print(f"─── [{kind}] 문단 {pi} ───")
                print(f"  의견 : {t}")
                print(f"  자리 : …{ctx[:150]}…\n")
            i = j

    # ── 3. Word 메모 ──
    # 메모는 본문과 따로 저장된다 — comments.xml 에 내용이, document.xml 에
    # <w:commentRangeStart w:id="N"> … <w:commentRangeEnd w:id="N"> 로 어디에
    # 달렸는지가 있다. 둘을 이어야 "무엇에 대한 메모인지"를 알 수 있다.
    if "word/comments.xml" in names:
        c = z.read("word/comments.xml").decode("utf-8")
        # 메모가 걸린 범위의 본문을 id 별로 모은다
        anchored = {}
        for mm in re.finditer(
                r'<w:commentRangeStart w:id="(\d+)"/>(.*?)<w:commentRangeEnd w:id="\1"/>',
                xml, re.DOTALL):
            anchored[mm.group(1)] = text_of(mm.group(2))
        for m in re.finditer(
                r'<w:comment\b([^>]*)>(.*?)</w:comment>', c, re.DOTALL):
            attrs, body = m.group(1), m.group(2)
            t = text_of(body)
            if not t:
                continue
            found += 1
            aid = re.search(r'w:id="(\d+)"', attrs)
            who = re.search(r'w:author="([^"]*)"', attrs)
            when = re.search(r'w:date="(\d{4}-\d{2}-\d{2})', attrs)
            tgt = anchored.get(aid.group(1)) if aid else None
            print(f"─── [Word 메모] {who.group(1) if who else '작성자 미상'}"
                  f"{' · ' + when.group(1) if when else ''} ───")
            print(f"  의견 : {t}")
            print(f"  자리 : {tgt if tgt else '(문단 전체 또는 범위 정보 없음)'}\n")

    # ── 4. 변경 내용 추적 ──
    for tag, lab in (("w:ins", "추가"), ("w:del", "삭제")):
        for m in re.finditer(rf'<{tag}\b[^>]*w:author="([^"]*)"[^>]*>(.*?)</{tag}>',
                             xml, re.DOTALL):
            t = text_of(m.group(2))
            if t:
                found += 1
                print(f"[변경 추적 · {lab}] {m.group(1)}\n    내용 : {t}\n")

    print("─" * 50)
    print(f"피드백 {found}건" if found else
          "피드백 없음 — 빨간 글씨·형광펜·메모·변경 추적 어느 것도 찾지 못했다.")
    return found


PAPER = "/Users/jongha/Desktop/GitHub/carbon-aware-scheduler/paper/"
# 인자가 없으면 두 문서를 다 본다 — 한쪽만 보고 "피드백 없다"고 보고한 적이 있다.
DEFAULT = [PAPER + "CAST_압축본.docx", PAPER + "CAST_추가자료.docx"]

if __name__ == "__main__":
    paths = sys.argv[1:] or DEFAULT
    total = 0
    for p in paths:
        if not os.path.exists(p):
            print(f"\n═══ {os.path.basename(p)} ═══\n  파일 없음: {p}")
            continue
        total += main(p) or 0
    if len(paths) > 1:
        print(f"\n합계 {total}건")
