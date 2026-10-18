# -*- coding: utf-8 -*-
"""띄운 그림·표 자리(FLOAT_SHIFT)를 좌표 하강으로 고른다: 조립 → Word 로 PDF → 쪽수·단 아래 빈 곳·겹침으로 점수.
    ./.venv/bin/python paper/tools/float_search.py <원고.txt> [시작 shift 예: tbl4=-1,fig1=2]
점수 = 쪽수×1000 + 단 아래 빈 곳(pt) 합 + 겹침(쪽당 12곳 넘는 것)×5000. 10-18 줄인 판 2회차에서 손으로 맞추다 만듦."""
import os, re, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PY = os.path.join(ROOT, ".venv/bin/python"); B = os.path.join(ROOT, "paper/tools/build_v2_docx.py")
DOCX = os.path.join(ROOT, "paper/CAST_JOK_v2.docx"); PDF = os.path.join(ROOT, "paper/CAST_JOK_v2.pdf")
sys.path.insert(0, os.path.join(ROOT, "paper/tools"))
from overlap_check import overlaps
import pymupdf

def score(src, sh):
    s = ",".join(f"{k}={v}" for k, v in sorted(sh.items()))   # 0 도 넘긴다 — 빼면 조립기의 기본 자리 옮김이 되살아남
    subprocess.run([PY, B, "--in", src, "--shift", s or "fig1=0"], cwd=ROOT, capture_output=True, check=True)
    r = subprocess.run(["osascript", os.path.join(ROOT, "paper/tools/word_to_pdf.applescript"), DOCX, PDF, "quiet"], capture_output=True, text=True)
    if r.returncode: raise RuntimeError(r.stderr)
    rep = subprocess.run([PY, B, "--in", src, "--report", PDF], cwd=ROOT, capture_output=True, text=True).stdout
    pages = int(re.search(r"(\d+)쪽\n", rep).group(1)); gaps = sum(int(g) for g in re.findall(r"아래 (\d+)pt 빔", rep))
    d = pymupdf.open(PDF); ov = sum(1 for p in d if len(overlaps(p)) > 12)
    return pages * 1000 + gaps + ov * 5000, pages, gaps, ov, s

def main():
    src = sys.argv[1]; sh = {}
    if len(sys.argv) > 2:
        for kv in sys.argv[2].split(","):
            k, v = kv.split("="); sh[k] = int(v)
    keys = ["fig1", "tbl1", "fig2", "alg1", "tbl2", "tbl3", "tbl4", "fig3", "tbl5"]
    best = score(src, sh); print("시작", best, flush=True)
    improved = True
    while improved:
        improved = False
        for k in keys:
            for dv in (-1, 1, -2, 2):
                cand = dict(sh); cand[k] = cand.get(k, 0) + dv
                if abs(cand[k]) > 5: continue
                sc = score(src, cand); print(" ", k, dv, sc[:4], flush=True)
                if sc[0] < best[0]: best, sh, improved = sc, cand, True; print("  → 채택", best, flush=True); break
    print("최종", best, flush=True)

if __name__ == "__main__":
    main()
