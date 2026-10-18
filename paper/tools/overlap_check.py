# -*- coding: utf-8 -*-
"""내보낸 PDF 에서 글자끼리 겹친 곳을 찾는다(띄운 그림·표가 본문·캡션 위에 얹힌 사고, 10-18 줄인 판 8쪽).
    ./.venv/bin/python paper/tools/overlap_check.py paper/CAST_JOK_v2.pdf
단어 상자 둘이 작은 쪽 넓이의 30% 넘게 겹치면 센다. 그림 속 글자(그림은 비트맵이라 안 잡힘)는 해당 없음."""
import sys
import pymupdf

def overlaps(page, frac=0.3):
    ws = sorted(page.get_text("words"), key=lambda w: w[1])
    hits = []
    for i, a in enumerate(ws):
        for b in ws[i + 1:]:
            if b[1] >= a[3]: break
            ix = min(a[2], b[2]) - max(a[0], b[0]); iy = min(a[3], b[3]) - max(a[1], b[1])
            if ix <= 0 or iy <= 0: continue
            small = min((a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1]))
            if small > 0 and ix * iy > frac * small: hits.append((a[4], b[4], round(a[1])))
    return hits

if __name__ == "__main__":
    d = pymupdf.open(sys.argv[1]); total = 0
    for n, p in enumerate(d, 1):
        h = overlaps(p); total += len(h)
        if h: print(f"  {n}쪽 겹침 {len(h)}곳, 예: {h[:3]}")
    print(f"{sys.argv[1]}: {len(d)}쪽, 겹침 {total}곳")
