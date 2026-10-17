# -*- coding: utf-8 -*-
"""v2 그림 1 · CAST 전체 구조 (전단 404pt) — v1 그림 1 골격 그대로, 가운데 단계만 바꾼다.

2026-10-16 사용자 결정 "v1 그림 문법 유지"(paper/문서/v2_draft/01_v1문체_그림문법.txt C5).
gen_figs.py 의 fig_architecture() 를 복사해 고쳤다 — 좌표·아이콘·선 어휘가 v1 과 같다.

v1 → v2 에서 바뀐 것
  · 가운데 단계 상자 둘("Spatial shift" / "Temporal shift")을 하나("Joint rolling
    assignment")로 합쳤다. 이것이 v2 의 핵심 변화(4.3절: 리전과 시작 슬롯을 한 LP 로).
    지구·시계 아이콘은 그 상자 안에 나란히 둔다 — 공간과 시간이 한 상자에 있다는 뜻.
  · 예측 상자 제목 "LSTM forecast" → "Forecast", 부제 "LSTM · 168 h → 24 h".
    LSTM → 24 h 곡선 → 배정 상자 한 길만 남긴다(v1 의 Ĉ(t) → Spatial 직행은 없어짐).
  · 위 입력에 지연 행렬 아이콘("Latency ℓ(o, r)")을 더했다 — 가는 선(자료).
  · 되먹임 둘: 점선 "n_r(τ)"(장부의 남은 용량, v1 의 a_r(t) 자리) 와 굵은 자기 고리
    "i ≥ 1 → next slot"(확정 안 된 작업이 다음 슬롯 LP 로) — 배정 상자 아래로 돈다.
  · 출력 화살표에 "(r(j), τ_j)" 를 적었다(본문 기호).
  · cost·capacity·α 수식 조각, Ledger 칸, Accounting, 범례는 없다 — 캡션·본문 몫.

규약
  · 1단위 = 1pt, 폭 404pt(JOK 전단 실측 403.7). 글씨 10 / 8 / 6.5pt(최소). 영문만.
  · 선 어휘(v1 과 같다): 굵은 실선 1.8 = 작업, 가는 실선 1.0 = 자료, 점선 0.9 = 되먹임.
  · 그리스 글자·수식 기호(ℓ·τ·Ĉ·C 와 라틴 변수)는 MATH 서체(Times New Roman →
    STIX Two Text → STIXGeneral → serif) 기울임. 기본 서체(Apple SD Gothic Neo)에는
    기울임이 없어 Helvetica-Oblique 로 대체되는데 α 가 라틴 'a' 처럼 보였다(2026-10-16).
  · PDF·PNG 는 Chrome headless 로 굽는다 — cairosvg 는 글자별 서체 대체를 안 해서
    Ĉ·− 가 두부로 찍혔다(2026-10-16 확인).

출력(스크립트 옆): v2_fig1_pipeline.svg / .pdf / .png / _zoom.png(배정 상자 400%)
실행: ./.venv/bin/python paper/diagram/gen_v2_fig1.py
"""
import math
import os
import pathlib
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from palette import INK, AUX_GRAY, EXCEPT_GRAY, BG_WASH  # noqa: E402

FS, FB, FT, FN = 9, 10, 8, 6.5    # 기본 / 제목 / 부제 / 최소
NAME = "v2_fig1_pipeline"
FONT = "'Malgun Gothic','Apple SD Gothic Neo','Noto Sans KR',sans-serif"
MATH = "'Times New Roman','STIX Two Text','STIXGeneral',serif"   # 기울임 수식 글자
CHROME = {
    "darwin": "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "win32": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
}.get(sys.platform, "google-chrome")
STRINGS = []   # (문구, 크기, x, x상한, 굵게, anchor) — 폭 검사용


# ── gen_figs.py 와 같은 원시 도형 ───────────────────────────────────────────
def head(w, h, note):
    return (f'<!-- {note} · gen_v2_fig1.py 로 생성 (직접 편집 금지)\n'
            f'     1단위 = 1pt, 폭 {w}pt. 100% 크기로 삽입할 것. -->\n'
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}pt" height="{h}pt"\n'
            f'     xml:space="preserve"\n'
            f'     font-family="{FONT}"\n'
            f'     font-size="{FS}" fill="{INK}">\n<defs>\n'
            f'  <marker id="a" viewBox="0 0 10 10" refX="9.5" refY="5" markerUnits="userSpaceOnUse" markerWidth="5" markerHeight="5" orient="auto-start-reverse">\n'
            f'    <path d="M0,0 L10,5 L0,10 z" fill="{INK}"/></marker>\n'
            f'</defs>\n<rect width="{w}" height="{h}" fill="#fff"/>')


def sb(t, rest="", size=None):
    # 아래첨자 뒤에 글이 이어지면 rest 로 넘긴다(gen_figs.py 주석 참조).
    # 글자 첨자(r, j, n)는 본문 수식처럼 기울이고 숫자(R₁)는 세운다 — 92 비평 6.
    # 크기는 본문 글자의 0.8배(FN 라벨 안에서는 5.2pt) — 같은 크기면 첨자로 안 읽힌다(렌더 확인).
    size = size or round(FN * 0.8, 1)
    st = f' font-family="{MATH}" font-style="italic"' if t.isalpha() else ""
    return f'<tspan font-size="{size}" dy="1.5"{st}>{t}</tspan><tspan dy="-1.5">{rest}</tspan>'


def it(t):
    """수식 글자 — MATH 서체 기울임(모듈 설명 참조)."""
    return f'<tspan font-family="{MATH}" font-style="italic">{t}</tspan>'


def box(x, y, w, h, **kw):
    d = kw.get("dash", "")
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{kw.get("fill", "#fff")}" stroke="{kw.get("stroke", INK)}" '
            f'stroke-width="{kw.get("sw", 1)}"' + (f' stroke-dasharray="{d}"' if d else "") + '/>')


def rbox(x, y, w, h, r=9, sw=1.6):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="#fff" '
            f'stroke="{INK}" stroke-width="{sw}"/>')


def txt(x, y, t, **kw):
    at = f' text-anchor="{kw["anchor"]}"' if "anchor" in kw else ""
    fs = f' font-size="{kw["size"]}"' if "size" in kw else ""
    fw = ' font-weight="bold"' if kw.get("bold") else ""
    st = ' font-style="italic"' if kw.get("it") else ""
    if "xmax" in kw:
        STRINGS.append((t, kw.get("size", FS), x, kw["xmax"], kw.get("bold", False),
                        kw.get("anchor", "start")))
    return f'<text x="{x}" y="{y}"{at}{fs}{fw}{st}>{t}</text>'


def rtxt(x, y, size, inner, plain, xmax=None, anchor=None, bold=False):
    """tspan 이 섞인 글(아래첨자·기울임). plain 은 폭 검사용 평문."""
    if xmax is not None:
        STRINGS.append((plain, size, x, xmax, bold, anchor or "start"))
    at = f' text-anchor="{anchor}"' if anchor else ""
    fw = ' font-weight="bold"' if bold else ""
    return f'<text x="{x}" y="{y}" font-size="{size}"{at}{fw}>{inner}</text>'


def arr(x1, y1, x2, y2, sw=1.1):
    return (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{INK}" '
            f'stroke-width="{sw}" marker-end="url(#a)"/>')


def path(d, sw=1.1, dash=None, head_=True):
    da = f' stroke-dasharray="{dash}"' if dash else ""
    mk = ' marker-end="url(#a)"' if head_ else ""
    return f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="{sw}"{da}{mk}/>'


def spark(x, y, w, h, n=24):
    p = []
    for i in range(n):
        f = i / (n - 1)
        v = 0.5 + 0.5 * math.cos(2 * math.pi * f)
        p.append(f"{x + f * w:.1f},{y + (1 - v) * h:.1f}")
    return (f'<polyline points="{" ".join(p)}" fill="none" stroke="{INK}" '
            f'stroke-width="0.9" stroke-linejoin="round"/>')


def dot(x, y, r=1.9):
    return f'<circle cx="{x}" cy="{y}" r="{r}" fill="{INK}"/>'


# ── 아이콘 (gen_figs.py 그대로) ───────────────────────────────────────────
def ic_cloud(x, y, s=1.0, label=""):
    g = [f'<g transform="translate({x},{y}) scale({s})">',
         f'<path d="M12,14 a7,7 0 0,1 13,-4 a6,6 0 0,1 10,5 a5.5,5.5 0 0,1 -1,11 '
         f'L10,26 a6,6 0 0,1 2,-12 z" fill="{INK}"/>',
         f'<circle cx="8" cy="9" r="5" fill="{INK}"/>',
         f'<text x="21" y="24" font-size="7" fill="#fff" text-anchor="middle" '
         f'font-weight="bold">CO₂</text>', "</g>"]
    if label:
        g.append(txt(x + 21 * s, y + 38 * s, label, anchor="middle", size=FT, xmax=x + 21 * s + 40))
    return "\n".join(g)


def ic_rack(x, y, s=1.0):
    g = [f'<g transform="translate({x},{y}) scale({s})">',
         f'<rect x="0" y="0" width="30" height="34" rx="2.5" fill="#fff" '
         f'stroke="{INK}" stroke-width="1.6"/>']
    for k in range(4):
        yy = 4 + k * 7.5
        g.append(f'<rect x="4" y="{yy}" width="22" height="5" fill="#fff" '
                 f'stroke="{INK}" stroke-width="0.9"/>')
        g.append(f'<circle cx="23" cy="{yy+2.5}" r="1.0" fill="{INK}"/>')
    g.append("</g>")
    return "\n".join(g)


def ic_jobs(x, y, s=1.0):
    g = [f'<g transform="translate({x},{y}) scale({s})">']
    for dx, dy in ((6, 0), (3, 3), (0, 6)):
        g.append(f'<path d="M{dx},{dy} h18 l5,5 v19 h-23 z" fill="#fff" stroke="{INK}" '
                 f'stroke-width="1.3"/>')
    for k in range(3):
        g.append(f'<line x1="4" y1="{12+k*4}" x2="17" y2="{12+k*4}" stroke="{INK}" '
                 f'stroke-width="0.9"/>')
    g.append("</g>")
    return "\n".join(g)


def ic_clock(x, y, s=1.0):
    return (f'<g transform="translate({x},{y}) scale({s})">'
            f'<circle cx="11" cy="11" r="10" fill="#fff" stroke="{INK}" stroke-width="1.6"/>'
            f'<line x1="11" y1="11" x2="11" y2="4.5" stroke="{INK}" stroke-width="1.5"/>'
            f'<line x1="11" y1="11" x2="15.5" y2="13" stroke="{INK}" stroke-width="1.5"/>'
            f'<circle cx="11" cy="11" r="1.3" fill="{INK}"/></g>')


def ic_globe(x, y, s=1.0):
    return (f'<g transform="translate({x},{y}) scale({s})">'
            f'<circle cx="11" cy="11" r="10" fill="#fff" stroke="{INK}" stroke-width="1.6"/>'
            f'<ellipse cx="11" cy="11" rx="4.2" ry="10" fill="none" stroke="{INK}" stroke-width="1"/>'
            f'<line x1="1" y1="11" x2="21" y2="11" stroke="{INK}" stroke-width="1"/>'
            f'<line x1="3" y1="5.5" x2="19" y2="5.5" stroke="{INK}" stroke-width="0.8"/>'
            f'<line x1="3" y1="16.5" x2="19" y2="16.5" stroke="{INK}" stroke-width="0.8"/></g>')


def ic_matrix(x, y, cell=4.2, n=4):
    """지연 행렬 아이콘(v2 에서 더함) — 대각은 0(흰색), 멀수록 짙다. palette.py 회색만."""
    g = []
    for i in range(n):
        for j in range(n):
            d = abs(i - j)
            fill = "#fff" if d == 0 else (BG_WASH if d == 1 else (AUX_GRAY if d == 2 else EXCEPT_GRAY))
            g.append(f'<rect x="{x + j*cell:.1f}" y="{y + i*cell:.1f}" width="{cell}" height="{cell}" '
                     f'fill="{fill}" stroke="{INK}" stroke-width="0.5"/>')
    return "\n".join(g)


# ═══════════ 그림 1 · v2 전체 구조 (v1 골격) ═══════════
def fig_architecture_v2():
    """fig_architecture()(gen_figs.py) 를 복사해 가운데만 바꿨다. 좌표는 v1 과 같다:
    입력 왼쪽·위, CAST 둥근 상자 84~316, 리전 랙 세로 목록 338~. 높이만 155 → 170
    (배정 상자 아래 자기 고리 자리)."""
    W, H = 404, 150
    L = [head(W, H, "그림 1 CAST v2 전체 구조 (전단)")]

    # ── 입력 ① 작업: 왼쪽 위 (v1 그대로) ──
    L += [ic_jobs(8, 5, 0.68),
          txt(32, 18, "Jobs · deadlines", size=FT, xmax=86)]

    # ── 입력 ② 탄소 이력: 왼쪽 가운데 (v1 그대로, 6.0 → 6.5pt 라 3pt 오른쪽으로) ──
    L += [ic_cloud(27, 56, 0.70, "Carbon intensity"),
          txt(41.7, 90, "History · per region · 1 h", anchor="middle", size=FN, xmax=84)]

    # ── 입력 ③ 지연 행렬: 위, 배정 상자 바로 위 (v2 에서 더함, 가는 선) ──
    L += [ic_matrix(256, 3),
          rtxt(277, 14, FN, f'Latency {it("ℓ")}({it("o")}, {it("r")})', "Latency ℓ(o, r)", 324)]

    # ── CAST 본체 (v1 과 같은 자리, 높이 +16) ──
    L += [rbox(84, 24, 232, 112, 10, 1.1),
          txt(92, 37, "CAST", bold=True, size=FB, xmax=140)]

    # 예측 — v1 "LSTM forecast / 168 h → 24 h" → "Forecast / LSTM · 168 h → 24 h"
    L += [box(94, 48, 96, 34, sw=0.8),
          txt(142, 62, "Forecast", anchor="middle", bold=True, size=FT, xmax=188),
          txt(142, 73, "LSTM · 168 h → 24 h", anchor="middle", size=FN, xmax=188)]

    # 결합 롤링 배정 — v1 의 Spatial(48~82)·Temporal(100~134) 두 상자를 하나로.
    # 지구·시계 아이콘을 나란히 두어 "공간과 시간이 한 상자"를 말한다.
    JX, JW = 206, 94            # 10-17: 94 로 좁혀 오른쪽 16pt 에 되먹임 고리와 n_r(τ) 라벨 자리를 둔다
    JC = JX + JW / 2                            # 257
    # 10-17(사용자: v1 처럼 LSTM→로드밸런서→스케줄러 흐름; 92 제안): 두 상자를 점선 테두리 "One LP per slot" 로 감싸
    # "한 문제의 두 축"을 보인다. 아이콘은 v1 처럼 제목 왼쪽. 테두리 48~112, 상자 두 개 세로 쌓기.
    # 테두리는 회색 가는 실선(점선은 이 그림에서 "장부 되먹임" 뜻으로 이미 쓰임 — 92 지적)
    L += [box(JX, 48, JW, 64, sw=1.0, stroke="#bfbfbf"),
          rtxt(JC, 56.5, FN, f'One LP per slot · knee {it("α")}', "One LP per slot · knee α", JX + JW - 3, anchor="middle"),
          box(JX + 5, 60, JW - 10, 23, sw=0.8),
          ic_globe(JX + 9, 65.5, 0.50),
          txt(JX + 23, 69, "Load balancer", bold=True, size=FT, xmax=JX + JW - 6),
          txt(JX + 23, 78.5, "region", size=FN, xmax=JX + JW - 6),
          box(JX + 5, 86, JW - 10, 23, sw=0.8),
          ic_clock(JX + 9, 91.5, 0.50),
          txt(JX + 23, 95, "Scheduler", bold=True, size=FT, xmax=JX + JW - 6),
          txt(JX + 23, 104.5, "start slot · capacity", size=FN, xmax=JX + JW - 6)]

    # 입력 → 본체. 선 어휘는 v1 과 같다(굵은 1.8 = 작업, 가는 1.0 = 자료).
    L += [path(f"M88,16 L{JC - 30},16 L{JC - 30},46.5", sw=1.8),        # 작업 → 배정 상자 위 (지연 화살표와 37pt 간격)
          path("M60,63 L92,63", sw=1.0),                                 # 탄소 이력 → 예측
          rtxt(76, 59, FN, it("C"), "C", anchor="middle"),
          path(f"M264,21 L264,46.5", sw=1.0)]                             # 지연 행렬 → 배정 상자 위

    # 예측 → 24 h 곡선 → 배정 (v1 의 아래 길 그대로; Ĉ(t) → Spatial 직행은 없어짐)
    L += [arr(142, 82, 142, 97, 1.0),
          rtxt(146, 92, FN, f'{it("Ĉ")}{sb("r", "(")}{it("t")})', "Ĉr(t)", 190),
          '<rect x="122" y="98" width="42" height="24" fill="#fff"/>',
          box(124, 99, 38, 16, sw=0.8), spark(127, 101, 32, 12),
          dot(143, 113, 1.6),
          path(f"M162,107 L{JX - 1.5},107", sw=1.0),
          txt(143, 127, "24 h curve", anchor="middle", size=FN, xmax=175)]

    # 되먹임 ① 점선: 장부의 남은 용량 n_r(τ) — v1 의 a_r(t) 고리 자리(상자 오른쪽)
    L += [path(f"M{JX + JW},84 L312,84 L312,96 L{JX + JW},96", sw=0.9, dash="3 1.8"),
          # 라벨은 고리 위 테두리 바깥 — "ledger" 단어는 캡션이 설명하므로 뺀다(글자 최소)
          rtxt(315, 81, FN, f'{it("n")}{sb("r", "(")}{it("τ")})', "nr(τ)", anchor="end")]

    # 되먹임 ② 굵은 자기 고리: i ≥ 1 작업은 확정하지 않고 다음 슬롯 LP 로 (상자 아래)
    L += [path(f"M{JX + JW - 18},112 L{JX + JW - 18},126 L{JX + 20},126 L{JX + 20},113.5", sw=1.8),
          rtxt(JC, 121.5, FN, f'{it("i")} ≥ 1 → next slot', "i ≥ 1 → next slot",
               JX + JW - 24, anchor="middle")]

    # ── 출력: 리전 랙 세로 목록 (v1 그대로) ──
    # 출력선은 점선 고리(100~114) 아래 y=126 에서 곧장 오른쪽으로 뺀다(v1 과 같은 이유).
    L += [txt(402, 13, "Execution (region, time)", anchor="end", size=FN, xmax=403)]
    RX, RS = 338, 0.42
    rows = [(20, "1"), (44, "2"), (68, "3"), (106, "n")]
    for ry, name in rows:
        L.append(ic_rack(RX, ry, RS))
        L.append(rtxt(RX + 30 * RS + 5, ry + 34 * RS * 0.72, FT, "R" + sb(name, size=6.0), "R" + name, bold=True))
    cx = RX + 30 * RS / 2
    L += [dot(cx, 90, 1.3), dot(cx, 95.5, 1.3), dot(cx, 101, 1.3)]
    ytop = 20 + 34 * RS / 2
    ybot = 106 + 34 * RS / 2
    L += [path(f"M{JX + JW},106 L326,106", sw=1.8, head_=False),
          path(f"M326,{ytop:.1f} L326,{ybot:.1f}", sw=1.8, head_=False)]
    for ry, _ in rows:
        yc = ry + 34 * RS / 2
        L.append(arr(326, yc, RX - 1.5, yc, 0.9))
    L.append("</svg>")
    return "\n".join(L)


# ── 폭 검사 (Apple SD Gothic Neo 로 잰다 — 이 Mac 에서 실제로 찍히는 서체) ──
def check_widths():
    try:
        from PIL import ImageFont
    except ImportError:
        print("PIL 없음 — 폭 검사 생략"); return
    ttc = "/System/Library/Fonts/AppleSDGothicNeo.ttc"
    if not os.path.exists(ttc):
        print("Apple SD Gothic Neo 없음 — 폭 검사 생략"); return
    bad = 0
    for s, size, x, xmax, bold, anchor in STRINGS:
        f = ImageFont.truetype(ttc, int(round(size * 10)), index=6 if bold else 0)
        w = f.getlength(s) / 10.0
        right = x + w / 2 if anchor == "middle" else (x if anchor == "end" else x + w)
        left = x - w / 2 if anchor == "middle" else (x - w if anchor == "end" else x)
        flag = "  <-- 넘침" if right > xmax or left < 0 else ""
        bad += bool(flag)
        print(f"  {w:6.1f}pt  {left:6.1f}~{right:6.1f} / 한계 {xmax:6.1f}{flag}  {s!r}")
    print("폭 검사:", "전부 들어감" if not bad else f"{bad}개 넘침")


# ── Chrome 렌더 ───────────────────────────────────────────────────────────
def chrome(svg_path, out, pw, ph, pdf=False):
    uri = pathlib.Path(svg_path).resolve().as_uri()
    html = os.path.splitext(out)[0] + ".render_tmp.html"
    if pdf:
        css = (f"@page{{size:{pw}pt {ph}pt;margin:0}}html,body{{margin:0;padding:0}}"
               f"img{{display:block;width:{pw}pt;height:{ph}pt}}")
    else:
        css = f"html,body{{margin:0;padding:0}}img{{display:block;width:{pw}px;height:{ph}px}}"
    open(html, "w", encoding="utf-8").write(
        f'<!DOCTYPE html><html><head><meta charset="utf-8"><style>{css}</style></head>'
        f'<body><img src="{uri}"></body></html>')
    args = [CHROME, "--headless", "--disable-gpu", "--no-sandbox", "--force-device-scale-factor=1",
            "--default-background-color=FFFFFFFF"]
    if pdf:
        args += ["--no-pdf-header-footer", f"--print-to-pdf={out}"]
    else:
        args += [f"--window-size={pw},{ph}", f"--screenshot={out}"]
    try:
        subprocess.run(args + [pathlib.Path(html).resolve().as_uri()],
                       check=True, capture_output=True, timeout=60)
    finally:
        os.remove(html)
    print("wrote", out)


def main():
    svg_path = os.path.join(HERE, NAME + ".svg")
    svg = fig_architecture_v2()
    open(svg_path, "w", encoding="utf-8").write(svg)
    print("wrote", svg_path)
    check_widths()

    w, h = map(float, re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', svg).groups())
    if not os.path.exists(CHROME):
        print("Chrome 없음 — PDF/PNG 생략:", CHROME); return

    # PDF: 쪽 크기 = 그림 크기, 글꼴은 SVG 와 같은 대체 규칙(Chrome)
    chrome(svg_path, os.path.join(HERE, NAME + ".pdf"), w, h, pdf=True)
    # PNG: render_svg.py 와 같은 해상도 규약(215pt → 1728px)
    scale = 1728 / 215.0
    chrome(svg_path, os.path.join(HERE, NAME + ".png"), round(w * scale), round(h * scale))
    # 배정 상자 400% 확대 (화면 400% = 4 × 96/72 px/pt)
    z = 4 * 96 / 72
    full = os.path.join(HERE, NAME + "_zoom_full.tmp.png")
    chrome(svg_path, full, round(w * z), round(h * z))
    try:
        from PIL import Image
        im = Image.open(full)
        x0, y0, x1, y1 = 196, 0, 336, 150      # 배정 상자 + 되먹임 둘 + 지연 입력 (pt)
        crop = im.crop((int(x0 * z), int(y0 * z), int(x1 * z), int(y1 * z)))
        zp = os.path.join(HERE, NAME + "_zoom.png")
        crop.save(zp)
        print("wrote", zp, crop.size)
    finally:
        os.remove(full)


if __name__ == "__main__":
    main()
