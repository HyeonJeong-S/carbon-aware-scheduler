# -*- coding: utf-8 -*-
"""그림 밑에 깔린 글줄 찾기 — overlap_check 는 글자끼리만 봐서 흰 바탕 그림이 표를 덮은 것(10-19 전체판 20쪽 그림 7 이 표 8 을 덮음)을 못 잡는다.
    ./.venv/bin/python paper/tools/under_image_check.py <pdf>"""
import sys

import pymupdf


def hidden(page):
    """그림 영역 안에 중심이 들어가는 글자 낱말 중, 그림 위에 그려지지 않은 것(= 그림 밑에 깔림)."""
    out = []
    imgs = [pymupdf.Rect(i["bbox"]) for i in page.get_image_info()]
    for x0, y0, x1, y1, w, *_ in page.get_text("words"):
        c = pymupdf.Point((x0 + x1) / 2, (y0 + y1) / 2)
        for r in imgs:
            if r.width > 30 and r.height > 30 and pymupdf.Rect(r.x0 + 2, r.y0 + 2, r.x1 - 2, r.y1 - 2).contains(c):
                out.append((w, round(y0)))
                break
    return out


if __name__ == "__main__":
    d = pymupdf.open(sys.argv[1])
    for i, p in enumerate(d):
        h = hidden(p)
        if len(h) > 3:
            print(f"{i + 1}쪽: 그림 영역 안 글자 {len(h)} — {h[:6]}")
