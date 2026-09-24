# -*- coding: utf-8 -*-
"""해결한 Word 메모를 docx 에서 지운다 — 번호로 하나씩.

메모 하나는 파일 네 군데에 흩어져 있다. 하나라도 남기면 Word 가 깨진 메모를
띄우거나 조용히 복구해버리므로 전부 같이 지운다.

  word/document.xml  <w:commentRangeStart w:id="N"/> … <w:commentRangeEnd w:id="N"/>
                     그리고 <w:r>…<w:commentReference w:id="N"/></w:r>
  word/comments.xml            <w:comment w:id="N"> … </w:comment>
  word/commentsExtended.xml    paraId 로 연결된 항목
  word/commentsIds.xml         같음

지우기 전에 반드시 무엇을 지우는지 찍고, 스냅샷을 남긴다 — 사용자가 적은 글은
되살릴 방법이 없다.

  ./.venv/bin/python paper/tools/resolve_comment.py 압축본 --list
  ./.venv/bin/python paper/tools/resolve_comment.py 압축본 --drop 2 5
"""
import argparse
import os
import re
import shutil
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime

PAPER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
FILES = {"압축본": "CAST_압축본.docx", "추가자료": "CAST_추가자료.docx",
         "인용포함": "CAST_인용포함.docx"}


def text_of(frag):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", frag)).strip()


def comments(path):
    """(id, 작성자, 날짜, 내용, 달린 자리) 목록."""
    z = zipfile.ZipFile(path)
    if "word/comments.xml" not in z.namelist():
        return []
    doc = z.read("word/document.xml").decode("utf-8")
    cx = z.read("word/comments.xml").decode("utf-8")
    anchored = {m.group(1): text_of(m.group(2)) for m in re.finditer(
        r'<w:commentRangeStart w:id="(\d+)"/>(.*?)<w:commentRangeEnd w:id="\1"/>',
        doc, re.DOTALL)}
    out = []
    for m in re.finditer(r"<w:comment\b([^>]*)>(.*?)</w:comment>", cx, re.DOTALL):
        cid = re.search(r'w:id="(\d+)"', m.group(1))
        who = re.search(r'w:author="([^"]*)"', m.group(1))
        when = re.search(r'w:date="(\d{4}-\d{2}-\d{2})', m.group(1))
        if not cid:
            continue
        out.append((cid.group(1), who.group(1) if who else "?",
                    when.group(1) if when else "", text_of(m.group(2)),
                    anchored.get(cid.group(1), "")))
    return out


def drop(path, ids):
    ids = {str(i) for i in ids}
    z = zipfile.ZipFile(path)
    parts = {n: z.read(n) for n in z.namelist()}
    z.close()

    doc = parts["word/document.xml"].decode("utf-8")
    # 지울 메모가 끼고 있는 paraId 를 먼저 모은다 — Extended/Ids 는 이걸로 연결된다.
    para_ids = set()
    cx = parts["word/comments.xml"].decode("utf-8")
    for m in re.finditer(r"<w:comment\b([^>]*)>(.*?)</w:comment>", cx, re.DOTALL):
        cid = re.search(r'w:id="(\d+)"', m.group(1))
        if cid and cid.group(1) in ids:
            para_ids |= set(re.findall(r'w14:paraId="([0-9A-Fa-f]+)"', m.group(2)))

    for i in sorted(ids):
        # 범위 표식 — 여는 것과 닫는 것
        doc = re.sub(rf'<w:commentRangeStart w:id="{i}"\s*/>', "", doc)
        doc = re.sub(rf'<w:commentRangeEnd w:id="{i}"\s*/>', "", doc)
        # 참조 run 통째로. run 안에 다른 내용이 없는 경우만 지운다.
        doc = re.sub(
            rf'<w:r\b(?:(?!</w:r>).)*?<w:commentReference w:id="{i}"\s*/>(?:(?!</w:r>).)*?</w:r>',
            "", doc, flags=re.DOTALL)
        cx = re.sub(rf'<w:comment\b[^>]*w:id="{i}"[^>]*>.*?</w:comment>', "", cx,
                    flags=re.DOTALL)
    parts["word/document.xml"] = doc.encode("utf-8")
    parts["word/comments.xml"] = cx.encode("utf-8")

    for name, tag in (("word/commentsExtended.xml", "w15:commentEx"),
                      ("word/commentsIds.xml", "w16cid:commentId")):
        if name not in parts:
            continue
        s = parts[name].decode("utf-8")
        for pid in para_ids:
            s = re.sub(rf"<{tag}\b[^>]*paraId=\"{pid}\"[^>]*/>", "", s, flags=re.I)
            s = re.sub(rf"<{tag}\b[^>]*paraId=\"{pid}\"[^>]*>.*?</{tag}>", "", s,
                       flags=re.DOTALL | re.I)
        parts[name] = s.encode("utf-8")

    for n, b in parts.items():
        if n.endswith(".xml"):
            ET.fromstring(b)                      # 깨진 XML 을 저장하지 않는다

    tmp = path + ".new"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as o:
        for n, b in parts.items():
            o.writestr(n, b)
    shutil.move(tmp, path)
    import docx
    docx.Document(path)                            # 적재 검사
    return para_ids


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("which", choices=list(FILES))
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--drop", nargs="+", type=int, default=[])
    a = ap.parse_args()
    path = os.path.normpath(os.path.join(PAPER, FILES[a.which]))

    cs = comments(path)
    if a.list or not a.drop:
        if not cs:
            print("메모 없음")
        for cid, who, when, txt, tgt in cs:
            print(f"[{cid}] {who} · {when}\n     의견: {txt}\n     자리: {tgt[:90]}")
        return

    keep = {c[0] for c in cs}
    miss = [i for i in a.drop if str(i) not in keep]
    assert not miss, f"없는 메모 번호: {miss} (있는 번호: {sorted(keep, key=int)})"

    print("지울 메모:")
    for cid, who, when, txt, tgt in cs:
        if cid in {str(i) for i in a.drop}:
            print(f"  [{cid}] {txt}\n        자리: {tgt[:80]}")

    snap = os.path.join(PAPER, "versions",
                        f"{os.path.basename(path)[:-5]}_{datetime.now():%Y%m%d_%H%M%S}_before_drop.docx")
    os.makedirs(os.path.dirname(snap), exist_ok=True)
    shutil.copy2(path, snap)
    print("스냅샷:", os.path.basename(snap))

    drop(path, a.drop)
    left = comments(path)
    print(f"남은 메모 {len(left)}건:", [c[0] for c in left])


if __name__ == "__main__":
    main()
