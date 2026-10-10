# -*- coding: utf-8 -*-
"""docx 를 PDF 로 내보낸다 — 메모가 있어도 배율이 안 깨지게.

왜 따로 만들었나 (2026-10-10 사고)
----------------------------------
문서에 Word 메모가 달려 있으면 Word 가 메모 여백을 만들려고 ** 본문 전체를
0.69배로 줄여서 ** PDF 를 뽑는다. 글자가 7.92pt → 5.49pt 로 찍힌다.
그걸 모르고 PDF 를 재면 "캡션 줄간격을 11.65pt 로 늘렸는데 7.98pt 로 줄었다"
같은 유령 결과가 나온다 — 실제로 한 번 속았다.

AppleScript 로 메모 표시를 끄는 것(show comments false)은 Mac Word 에서
안 먹었다. 그래서 ** 메모를 뺀 사본을 임시로 만들어 거기서 내보낸다. **
원본 docx 의 메모는 건드리지 않는다 — 사용자가 docx 로 메모를 보기 때문이다.

메모 하나는 파일 네 군데에 흩어져 있어 전부 지워야 Word 가 안 깨진다
(resolve_comment.py 주석과 같은 목록).

실행:
  ./.venv/bin/python paper/tools/export_pdf.py paper/CAST_JOK_본문.docx
  ./.venv/bin/python paper/tools/export_pdf.py <docx> [출력.pdf]
"""
import os
import re
import shutil
import subprocess
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
SCRIPT = os.path.join(HERE, "word_to_pdf.applescript")

DROP_PARTS = ("word/comments.xml", "word/commentsExtended.xml",
              "word/commentsIds.xml", "word/commentsExtensible.xml")


def strip_comments(src, dst):
    """메모를 뺀 사본을 만든다. 지운 메모 수를 돌려준다."""
    z = zipfile.ZipFile(src)
    parts = {i.filename: z.read(i.filename) for i in z.infolist()}
    infos = [i for i in z.infolist() if i.filename not in DROP_PARTS]
    z.close()

    doc = parts["word/document.xml"].decode("utf-8")
    n = len(re.findall(r'<w:commentRangeStart\b', doc))
    doc = re.sub(r'<w:commentRange(?:Start|End)\b[^>]*/>', '', doc)
    # commentReference 를 품은 run 을 통째로 들어낸다
    doc = re.sub(r'<w:r\b(?:(?!</w:r>).)*?<w:commentReference\b[^>]*/>'
                 r'(?:(?!</w:r>).)*?</w:r>', '', doc, flags=re.DOTALL)
    parts["word/document.xml"] = doc.encode("utf-8")

    # 관계와 Content_Types 에서도 뺀다 — 남기면 Word 가 깨진 메모를 띄운다
    rels = parts["word/_rels/document.xml.rels"].decode("utf-8")
    rels = re.sub(r'<Relationship[^>]*comments[^>]*/>', '', rels)
    parts["word/_rels/document.xml.rels"] = rels.encode("utf-8")
    ct = parts["[Content_Types].xml"].decode("utf-8")
    ct = re.sub(r'<Override[^>]*comments[^>]*/>', '', ct)
    parts["[Content_Types].xml"] = ct.encode("utf-8")

    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as o:
        for it in infos:
            o.writestr(it, parts[it.filename])
    return n


def main():
    src = os.path.abspath(sys.argv[1])
    out = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 \
        else os.path.splitext(src)[0] + ".pdf"
    tmp = os.path.splitext(src)[0] + "__nocomment.docx"
    try:
        n = strip_comments(src, tmp)
        print(f"  메모 {n}개를 뺀 사본으로 내보낸다 (원본은 그대로)")
        r = subprocess.run(["osascript", SCRIPT, tmp, out],
                           capture_output=True, text=True)
        if r.returncode:
            print(r.stdout, r.stderr)
            sys.exit("내보내기 실패")
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    print(f"  → {out}")


if __name__ == "__main__":
    main()
