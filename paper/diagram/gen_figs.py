# -*- coding: utf-8 -*-
"""CAST 논문 그림 4종 생성기 — 흑백 SVG 만.

  fig1_architecture   전체 구조   전단 451pt  (통합/개요 그림 — 유일하게 전단)
  fig2_forecast       탄소 예측   단내 215pt  (본문에서 빠짐, 목차.txt 결정)
  fig3_loadbalancer   로드밸런서  단내 215pt
  fig4_scheduler      스케줄러    단내 215pt

  2026-09-21 배치 규칙 확정(be): "통합(개요) 그림만 전단, 개별 설명 그림은
  단내." 이전엔 이 표가 fig3·4를 "단내"라 적어놓고 실제 코드는 451pt 전단으로
  만들어(9pt 글씨 기준이 안 맞음, E9에서 발견) 표와 코드가 어긋나 있었다 —
  이번에 fig3·4를 실제로 세로 스택 215pt로 재설계해서 표가 처음으로 코드와
  맞는다. fig1(구조)만 세 단계를 한눈에 보여주는 통합 그림이라 전단 유지.

설계 원칙
  · 식은 넣지 않는다. 식 (6)~(11)은 본문에 이미 조판돼 있어 그림에 다시 넣으면
    순수 중복이고, 본문을 한 줄도 줄여주지 못하면서 그림만 커진다.
    그림은 구조와 흐름만 맡고, 화살표에 흐르는 기호(Ĉ · ℓ · x_jr · avail_r)만 남긴다.
  · 개별 설명 그림(로드밸런서·스케줄러)은 단내(215pt) 세로 스택. 전단 그림은
    높이만큼 양쪽 단을 동시에 막지만 단내는 한쪽만 막아 실효 비용이 절반이다.
    9pt 글씨를 지키려고 요소 수를 줄인다 — 캡션과 겹치는 각주, 본문 수식과
    겹치는 산식(avail_r=⌊η·cap_r⌋−…)은 그림에서 빼고 본문에만 남긴다.
  · IEEE : 최종 인쇄 크기 작도(1단위 = 1pt), 글씨 9pt · 부제 8pt · 아래첨자 6.5pt.

칠판 스케치와 동료 세션 검증 반영
  · 로드밸런서 산출물은 '예약 시간표'가 아니라 그 슬롯의 배정 x_jr.
    실행 시각은 다음 단계(시간 이동) 소관.
  · avail_r 은 ⌊η·cap_r⌋ 에서 실행 중 작업 수를 뺀 값 — 칠판의 ⊕ 가 이것이다.
  · 사후 용량 강제(칠판의 loop)는 §6.4 검증 단계 전용이며 온라인 구성요소가 아니다.
    본문 [686] "용량 제약을 온라인으로 반영하는 구현은 수행하지 않았다".
  · 미배정 변수는 u_j — 본문 §5.2 의 제출 시각 s_j 와 충돌하므로 그림에서 분리.

실행: python3 gen_figs.py
"""
import math
import os

INK, FS, FB, FT = "#000000", 9, 10, 8

def spark(x, y, w, h, n=24):
    """24점 일간 탄소 곡선 아이콘 — 야간 높고 정오 낮은 형태.

    그림 1에서 '값 하나'가 아니라 '곡선'이 흐른다는 것을 보이는 데 쓴다.
    공간 이동은 현재 슬롯 값 1점으로 족하지만 시간 이동은 곡선 전체가 필요하다 —
    이 대비가 §6.2(1 h 지평은 지속성 기준선이 우세, 6 h 이후만 LSTM 우세)의 예고다.
    """
    p = []
    for i in range(n):
        f = i / (n - 1)
        v = 0.5 + 0.5 * math.cos(2 * math.pi * f)     # f=0,1 고탄소 / f=0.5 저탄소
        p.append(f"{x + f * w:.1f},{y + (1 - v) * h:.1f}")
    return (f'<polyline points="{" ".join(p)}" fill="none" stroke="{INK}" '
            f'stroke-width="0.9" stroke-linejoin="round"/>')

def dot(x, y, r=1.9):
    """값 하나를 뜻하는 점 — spark() 와 대비시켜 쓴다."""
    return f'<circle cx="{x}" cy="{y}" r="{r}" fill="{INK}"/>'

def bar1(x, y, w, h):
    """세로 막대 하나 — 한 시각의 값 하나. spark()(곡선 전체)와 짝을 이뤄 공간
    이동(그 슬롯의 값 1개)과 시간 이동(24 h 곡선 전체)의 차이를 글자 없이 보인다.
    2026-09-24(4c 배분, 사용자 메모): "24h랑 Ĉ(t)랑 왜 나눈거지" — '무엇'만 있고
    '왜'가 없던 것을 "막대 대 곡선" 모양 대비로 채운다."""
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{INK}"/>'

def slots(x, y, cell, n, filled):
    """자리 칸 — 채운 칸(검정)과 빈 칸(흰색)을 나란히 그린다. avail_r(=K_r−n_r(t))을
    수식이 아니라 그림으로 보인다. 2026-09-24(4c 배분, 사용자 메모): "avail은 뭐고"
    — 라벨 하나로는 뜻이 안 잡혀 시간 이동 상자 안에 이 칸 그림을 덧붙인다."""
    parts = []
    for i in range(n):
        cx = x + i * (cell + 1.0)
        fill = INK if i < filled else "#fff"
        parts.append(f'<rect x="{cx:.1f}" y="{y}" width="{cell}" height="{cell}" '
                      f'fill="{fill}" stroke="{INK}" stroke-width="0.6"/>')
    return "\n".join(parts)

def head(w, h, note):
    return (f'<!-- {note} · gen_figs.py 로 생성 (직접 편집 금지)\n'
            f'     1단위 = 1pt, 폭 {w}pt. 100% 크기로 삽입할 것. -->\n'
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}pt" height="{h}pt"\n'
            f'     xml:space="preserve"\n'
            # 아래첨자 tspan 뒤에 이어지는 선행 공백이 기본 XML 공백정리 규칙으로
            # 사라져 글자가 붙어 보이는 문제(2026-09-21, avail_r 라벨에서 발견)
            # 를 막는다 — SVG는 xml:space 미지정 시 공백을 압축한다.
            f'     font-family="\'Malgun Gothic\',\'Apple SD Gothic Neo\',\'Noto Sans KR\',sans-serif"\n'
            f'     font-size="{FS}" fill="{INK}">\n<defs>\n'
            f'  <marker id="a" viewBox="0 0 10 10" refX="9.5" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">\n'
            f'    <path d="M0,0 L10,5 L0,10 z" fill="{INK}"/></marker>\n'
            f'</defs>\n<rect width="{w}" height="{h}" fill="#fff"/>')

def sb(t, rest=""):   # 아래첨자. rest가 있으면 dy 복귀 tspan 안에 같이 넣는다 —
    # 빈 tspan으로 dy만 되돌리면(rest="") 그 바깥의 평문(특히 한글)과의 커서
    # 위치 계산이 렌더러마다 달라 글자가 붙거나 겹친다(2026-09-21, pymupdf는
    # 심하게 겹치고 Chrome은 살짝 붙는 정도로 다르게 틀렸음 — fe 발견).
    # 뒤에 텍스트가 이어지면 반드시 rest로 넘길 것, 문자열 이어붙이기(+) 금지.
    return f'<tspan font-size="6.5" dy="1.5">{t}</tspan><tspan dy="-1.5">{rest}</tspan>'
def box(x, y, w, h, **kw):
    d = kw.get("dash", "")
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#fff" stroke="{INK}" '
            f'stroke-width="{kw.get("sw",1)}"' + (f' stroke-dasharray="{d}"' if d else "") + '/>')
def txt(x, y, t, **kw):
    at = f' text-anchor="{kw["anchor"]}"' if "anchor" in kw else ""
    fs = f' font-size="{kw["size"]}"' if "size" in kw else ""
    fw = ' font-weight="bold"' if kw.get("bold") else ""
    st = ' font-style="italic"' if kw.get("it") else ""
    return f'<text x="{x}" y="{y}"{at}{fs}{fw}{st}>{t}</text>'
def arr(x1, y1, x2, y2, sw=1.1):
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{INK}" stroke-width="{sw}" marker-end="url(#a)"/>'
def path(d, sw=1.1, dash=None, head_=True):
    da = f' stroke-dasharray="{dash}"' if dash else ""
    mk = ' marker-end="url(#a)"' if head_ else ""
    return f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="{sw}"{da}{mk}/>'


# ══════════════════════ 아이콘 (CASPER 계열 작화) ══════════════════════
# 사용자 요청: "그림들이 너무 네모네모해서 diagram 같다. CASPER 논문처럼 그림그림
# 하게 그려달라." CASPER Fig.2 를 뜯어보니 (a) CO₂ 구름·사람·서버랙 같은 사물
# 아이콘, (b) 둥근 모서리 컨테이너, (c) 굵기가 다른 화살표, (d) 기울어진 리본
# 라벨을 쓴다. 흑백이라는 제약 안에서 같은 결을 낸다.

def ic_cloud(x, y, s=1.0, label="", co2=True):
    """CO₂ 구름 — 탄소집약도 입력.
    co2=False: 구름 안 "CO₂" 글자를 뺀다. 2026-10-18(82 점검4 E [4]): 그림 2 는 s=0.45 라 글자가 인쇄 약 2.5 pt 로 뭉개졌다 —
    키우면(6 pt 이상) 구름이 2배 넘게 커져 옆 탄소 곡선과 부딪혀, 글자를 빼고 아이콘만 남긴다. 그림 1 판(s=0.70)은 그대로."""
    g = [f'<g transform="translate({x},{y}) scale({s})">']
    g.append(f'<path d="M12,14 a7,7 0 0,1 13,-4 a6,6 0 0,1 10,5 a5.5,5.5 0 0,1 -1,11 '
             f'L10,26 a6,6 0 0,1 2,-12 z" fill="{INK}"/>')
    g.append(f'<circle cx="8" cy="9" r="5" fill="{INK}"/>')
    if co2:
        g.append(f'<text x="21" y="24" font-size="7" fill="#fff" text-anchor="middle" '
                 f'font-weight="bold">CO₂</text>')
    g.append("</g>")
    if label:
        g.append(txt(x + 21 * s, y + 38 * s, label, anchor="middle", size=FT))
    return "\n".join(g)

def ic_rack(x, y, s=1.0, label=""):
    """서버 랙 — 리전/데이터센터."""
    g = [f'<g transform="translate({x},{y}) scale({s})">']
    g.append(f'<rect x="0" y="0" width="30" height="34" rx="2.5" fill="#fff" '
             f'stroke="{INK}" stroke-width="1.6"/>')
    for k in range(4):
        yy = 4 + k * 7.5
        g.append(f'<rect x="4" y="{yy}" width="22" height="5" fill="#fff" '
                 f'stroke="{INK}" stroke-width="0.9"/>')
        g.append(f'<circle cx="23" cy="{yy+2.5}" r="1.0" fill="{INK}"/>')
    g.append("</g>")
    if label:
        g.append(txt(x + 15 * s, y + 34 * s + 9, label, anchor="middle", size=FT, bold=True))
    return "\n".join(g)

def ic_jobs(x, y, s=1.0, label=""):
    """작업 묶음 — 겹친 문서."""
    g = [f'<g transform="translate({x},{y}) scale({s})">']
    for k, (dx, dy) in enumerate(((6, 0), (3, 3), (0, 6))):
        f = "#fff"
        g.append(f'<path d="M{dx},{dy} h18 l5,5 v19 h-23 z" fill="{f}" stroke="{INK}" '
                 f'stroke-width="1.3"/>')
    for k in range(3):
        g.append(f'<line x1="4" y1="{12+k*4}" x2="17" y2="{12+k*4}" stroke="{INK}" '
                 f'stroke-width="0.9"/>')
    g.append("</g>")
    if label:
        g.append(txt(x + 13 * s, y + 30 * s + 9, label, anchor="middle", size=FT))
    return "\n".join(g)

def ic_brain(x, y, s=1.0):
    """LSTM — 층이 보이는 신경망 표식."""
    g = [f'<g transform="translate({x},{y}) scale({s})">']
    for c, xs in ((0, 4), (1, 15), (2, 26)):
        n = 3 if c != 1 else 4
        for k in range(n):
            yy = 5 + k * 7 + (0 if n == 3 else -3.5)
            g.append(f'<circle cx="{xs}" cy="{yy}" r="2.4" fill="{"#fff" if c else INK}" '
                     f'stroke="{INK}" stroke-width="1"/>')
    g.append(f'<g stroke="{INK}" stroke-width="0.45" opacity="0.75">')
    for a in range(3):
        for b in range(4):
            g.append(f'<line x1="6.4" y1="{5+a*7}" x2="12.6" y2="{1.5+b*7}"/>')
    for a in range(4):
        for b in range(3):
            g.append(f'<line x1="17.4" y1="{1.5+a*7}" x2="23.6" y2="{5+b*7}"/>')
    g.append("</g></g>")
    return "\n".join(g)

def ic_clock(x, y, s=1.0):
    """시계 — 시간 축."""
    return (f'<g transform="translate({x},{y}) scale({s})">'
            f'<circle cx="11" cy="11" r="10" fill="#fff" stroke="{INK}" stroke-width="1.6"/>'
            f'<line x1="11" y1="11" x2="11" y2="4.5" stroke="{INK}" stroke-width="1.5"/>'
            f'<line x1="11" y1="11" x2="15.5" y2="13" stroke="{INK}" stroke-width="1.5"/>'
            f'<circle cx="11" cy="11" r="1.3" fill="{INK}"/></g>')

def ic_globe(x, y, s=1.0):
    """지구 — 공간 축."""
    return (f'<g transform="translate({x},{y}) scale({s})">'
            f'<circle cx="11" cy="11" r="10" fill="#fff" stroke="{INK}" stroke-width="1.6"/>'
            f'<ellipse cx="11" cy="11" rx="4.2" ry="10" fill="none" stroke="{INK}" stroke-width="1"/>'
            f'<line x1="1" y1="11" x2="21" y2="11" stroke="{INK}" stroke-width="1"/>'
            f'<line x1="3" y1="5.5" x2="19" y2="5.5" stroke="{INK}" stroke-width="0.8"/>'
            f'<line x1="3" y1="16.5" x2="19" y2="16.5" stroke="{INK}" stroke-width="0.8"/></g>')

def ribbon(x, y, text, angle=-14, size=None):
    """기울어진 리본 라벨 — CASPER 의 'Forecasts', 'SLOs' 같은 것."""
    size = size or FT
    w = 7 + len(text) * 4.6
    return (f'<g transform="translate({x},{y}) rotate({angle})">'
            f'<rect x="0" y="-8" width="{w}" height="12" fill="#fff" stroke="{INK}" '
            f'stroke-width="1"/>'
            f'<text x="{w/2}" y="0.5" font-size="{size}" text-anchor="middle">{text}</text>'
            f'</g>')

def fat_arrow(x1, y1, x2, y2, w=7):
    """두꺼운 속 빈 화살표 — CASPER 의 User Requests 화살표."""
    import math
    dx, dy = x2 - x1, y2 - y1
    L = math.hypot(dx, dy)
    ux, uy = dx / L, dy / L
    px, py = -uy, ux
    hl = min(11, L * 0.42)
    bx, by = x2 - ux * hl, y2 - uy * hl
    pts = [(x1 + px * w / 2, y1 + py * w / 2), (bx + px * w / 2, by + py * w / 2),
           (bx + px * w, by + py * w), (x2, y2), (bx - px * w, by - py * w),
           (bx - px * w / 2, by - py * w / 2), (x1 - px * w / 2, y1 - py * w / 2)]
    d = "M" + " L".join(f"{a:.1f},{b:.1f}" for a, b in pts) + " Z"
    return f'<path d="{d}" fill="#fff" stroke="{INK}" stroke-width="1.2"/>'

def rbox(x, y, w, h, r=9, sw=1.6):
    """둥근 모서리 컨테이너 — CASPER 의 본체 상자."""
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="#fff" '
            f'stroke="{INK}" stroke-width="{sw}"/>')

# ═══════════ 그림 1 · 전체 구조 (전단) ═══════════
def fig_architecture():
    """전체 구조 — 2026-10-08 전단(가로형)으로 재배치.

    왜 바꿨나: JOK 단 폭은 69mm(195.6pt)인데 이 그림은 215pt 설계였다. 단에 넣으면
    0.910배로 줄어 가장 작은 글자가 5.1pt 로 찍힌다(5d 가 잰 JOK 실물 하한 5.7~5.9).
    글자만 키우면 "Deadline · capacity-aware"(65.2pt)가 상자 폭을 넘어 안 들어간다.
    사용자 결정(2026-10-08): 그림1·2 는 전단(403.7pt)으로 돌린다.

    ** 그냥 키우면 안 된다. ** 옛 설계(215×218, 거의 정사각)를 전단에 균등확대하면
    403×409 가 되어 한 쪽의 2/3 를 먹는다(단내 대비 지면 4.26배). 세로로 쌓인 흐름을
    가로로 펴야 전단의 이득이 난다 — 입력을 왼쪽, 본체를 가운데, 리전 랙을 오른쪽에
    두어 404×155 으로 맞췄다(단내 대비 1.61배 — 한 쪽의 15.6% → 25%).

    배치 규칙 셋:
      · 작업(굵은 선)은 위로 들어와 공간 → 시간 → 실행으로 흐른다. 탄소(가는 선)는
        왼쪽에서 LSTM 으로 들어가 두 단계에 서로 다른 모양으로 공급된다.
      · 리전 랙은 2×2 로 두고 R3 와 Rn 사이에 점 셋을 넣어 "그 사이에도 있다"를
        그림으로 말한다(옛 가로 한 줄과 같은 규약).
      · 글자는 하나도 바꾸지 않았다. 자리만 옮겼다.
    """
    W, H = 404, 155
    L = [head(W, H, "그림 1 CAST 전체 구조 (전단)")]

    # ── 입력 ① 작업: 왼쪽 위, 라벨을 아이콘 오른쪽에 둬 본체 위 띠를 비운다 ──
    L += [ic_jobs(8, 5, 0.68),
          txt(32, 18, "Jobs · deadlines", size=FT)]

    # ── 입력 ② 탄소 이력: 왼쪽 가운데 ──
    L += [ic_cloud(24, 56, 0.70, "Carbon intensity"),
          txt(38.7, 90, "History · per region · 1 h", anchor="middle", size=6.0)]

    # ── CAST 본체 ──
    L += [rbox(84, 24, 232, 116, 10, 1.1),
          txt(92, 37, "CAST", bold=True, size=FB)]

    # 예측
    # 2026-10-09(그림 교차반박 3라운드): ic_brain() 을 뺐다. 3→4→3 전부연결
    # 다층퍼셉트론이라 LSTM 이 아니었다(96 발견, b0 소스 확인). 노드 수도
    # 168/64/24 어디와도 안 맞았다 — 없는 구조를 주장하는 아이콘이라 지운다.
    # 안쪽 상자는 rbox→box(각진 사각형). 참고 논문 3편은 바깥 컨테이너만
    # 둥글고 안쪽은 각지다(CASPER: CASPER 테두리만 둥글고 CAP·CAS 는 각짐).
    L += [box(94, 48, 96, 34, sw=0.8),
          txt(143, 62, "LSTM forecast", anchor="middle", bold=True, size=FT),
          txt(143, 73, "168 h → 24 h", anchor="middle", size=6.0)]

    # 공간 이동
    L += [box(212, 48, 96, 34, sw=0.8),
          ic_globe(216, 55, 0.56),
          txt(266, 62, "Spatial shift", anchor="middle", bold=True, size=FT),
          txt(266, 73, "ILP · capacity", anchor="middle", size=6.0)]

    # 시간 이동
    # slots(■■■■□□) 를 뺐다 — 본문·캡션 어디에도 설명이 없는 글리프였고,
    # "capacity-aware" 라는 말이 이미 같은 뜻을 전달한다.
    L += [box(212, 100, 96, 34, sw=0.8),
          ic_clock(216, 107, 0.56),
          txt(266, 114, "Temporal shift", anchor="middle", bold=True, size=FT),
          txt(266, 125, "Deadline · capacity-aware", anchor="middle", size=6.0)]

    # 입력 → 본체. 화살표 어휘를 뜻에 고정한다(2026-10-09, 96 기준 3):
    #   굵은 실선 1.8 = 작업이 지나는 길   가는 실선 1.0 = 탄소 자료
    #   점선 0.9 = 되먹임
    # 뜻당 하나씩만 쓴다. 전에는 LSTM→24h곡선 하나에만 속 빈 블록 화살표를
    # 써서 네 번째 어휘가 생겼는데, 그 간선도 탄소 자료라 가는 실선으로 바꿨다.
    # 참고: 종류 수 자체는 쟁점이 아니다 — CASPER Fig.2 는 6종을 쓴다. 다만
    # 거기선 종류마다 뜻이 하나로 고정돼 있다.
    L += [path("M88,16 L266,16 L266,46", sw=1.8),
          path("M58,63 L92,63", sw=1.0),
          txt(75, 59, "C", anchor="middle", it=True, size=6.0)]

    # 한 슬롯의 값 Ĉ(t) 는 공간 이동으로, 24 h 곡선 전체는 시간 이동으로 간다.
    # 전에는 이 대비를 설명 없는 글리프(검은 막대 하나)로 그렸는데 지웠다 —
    # "Ĉ(t)"(한 시각)와 "24 h curve"(구간 전체)라는 라벨이 이미 같은 말을 한다.
    L += [arr(190, 62, 210, 62, 1.0),
          txt(200, 57, "Ĉ(t)", anchor="middle", it=True, size=6.0)]
    L += [arr(143, 82, 143, 97, 1.0),
          txt(147, 92, "Ĉ(t … t+24)", it=True, size=6.0),
          f'<rect x="122" y="98" width="42" height="24" fill="#fff"/>',
          box(124, 99, 38, 16, sw=0.8), spark(127, 101, 32, 12),
          dot(143, 113, 1.6),
          path("M162,107 L210,107", sw=1.0),
          txt(143, 127, "24 h curve", anchor="middle", size=6.0)]

    # 공간 → 시간 (리전 확정). "Region" 은 평문, r(j) 만 기울임 — 전에는 줄
    # 전체가 평문이라 같은 그림 안의 Ĉ(t)·a_r(t) 와 어긋났다(96 발견).
    L += [arr(266, 82, 266, 98, 1.8),
          f'<text x="258" y="92" text-anchor="end" font-size="6.0">Region '
          f'<tspan font-style="italic">r(j)</tspan></text>']

    # 되먹임 — 시간 이동 자신의 잔여 용량(자기 상자로 돌아오는 짧은 고리)
    L += [path("M308,106 L314,106 L314,120 L308,120", sw=0.9, dash="3 1.8"),
          txt(314, 96, "a" + sb("r", "(t)"), anchor="end", it=True, size=6.0)]

    # ── 출력: 리전 랙 (오른쪽 2×2) ──
    # 출력은 **시간 이동**에서 나온다(공간 이동이 아니다). 되먹임 고리(y 106~120)
    # 와 엉키지 않게 그 아래(y=130)에서 곧장 오른쪽으로 뺀다 — 꺾으면 고리와
    # 겹쳐 읽히고, 짧은 마지막 구간에서는 화살촉 방향도 흐려진다.
    # 이 간선에는 따로 라벨을 달지 않는다. 오른쪽 "Execution (region, time)"
    # 이 흐르는 것(배정 리전과 실행 시각)을 이미 그대로 이름 짓고 있어서,
    # x_jr · τ_j 를 덧붙이면 같은 말을 두 번 하는 것이 된다 — 이번 라운드에서
    # 없애기로 한 중복과 같은 종류다. 넣어 보니 짧은 화살표(26pt) 위에서
    # 아래첨자가 선에 닿기도 했다.
    # 2026-10-10 사용자 메모: "R1,Rn까지 있는 게 쭉 나열되어 있는 게 좋을듯,
    # 위에서부터 아래로 주르륵... 지금은 사각형 4개 그린 거잖아."
    # 2×2 격자는 "리전이 넷"으로 읽히는데 뜻은 "리전이 n개"다. 세로 목록 +
    # 가운데 세로 점 셋으로 바꾼다 — 목록이라는 게 모양으로 드러난다.
    # 출력 화살표는 한 랙이 아니라 묶음 전체를 가리켜야 하므로, 세로 등뼈를
    # 세우고 거기서 랙마다 짧은 가지를 뻗는다.
    L += [txt(368, 13, "Execution (region, time)", anchor="middle", size=6.0)]
    RX, RS = 338, 0.42
    rows = [(20, "1"), (44, "2"), (68, "3"), (106, "n")]
    for ry, name in rows:
        L.append(ic_rack(RX, ry, RS))
        L.append(txt(RX + 30 * RS + 5, ry + 34 * RS * 0.72, "R" + sb(name),
                     size=FT, bold=True))
    # 세로 점 셋 — R3 와 Rn 사이에 더 있다는 뜻
    cx = RX + 30 * RS / 2
    L += [dot(cx, 90, 1.3), dot(cx, 95.5, 1.3), dot(cx, 101, 1.3)]
    # 등뼈와 가지
    # 되먹임 점선이 상자 오른쪽 y 106~120 에 있으므로 출력선은 그 아래(y=128)로
    # 뺀다 — y=117 로 두면 점선 고리를 가로질러 둘이 엉켜 읽힌다(렌더해서 확인).
    ytop = 20 + 34 * RS / 2
    L += [path("M308,128 L326,128", sw=1.8, head_=False),
          path(f"M326,{ytop:.1f} L326,128", sw=1.8, head_=False)]
    for ry, _ in rows:
        yc = ry + 34 * RS / 2
        L.append(arr(326, yc, RX - 1.5, yc, 0.9))
    L.append("</svg>")
    return "\n".join(L)

# ═══════════ 그림 2 · 탄소 예측 (전단) ═══════════
def fig_forecast():
    """그림 2 — 리전별 LSTM 구조. 2026-10-10 단내(세로 스택)로 재배치.

    왜 또 바꿨나: 사용자 메모 — "본문 중간에 2단 다 차지하는 걸 바꿔".
    전단(404×110)이라 쪽 한가운데서 2단을 통째로 갈라 본문이 위아래로 끊겼다.
    60 이 실물 11편을 재보니 전단 그림은 ** 전부 쪽 맨 위 ** 에 붙고, 쪽 중간에
    떠서 단을 가르는 전례가 하나도 없었다.
    처음엔 그림1 바로 뒤로 옮겨 "그림-그림-본문"으로 만들었는데, 사용자 뜻은
    위치가 아니라 ** 전단을 단내로 바꾸라 ** 는 것이었다. 그래서 단내로 다시 그린다.

    단내 폭(195.6pt)에 맞추려고 가로 3열(입력→LSTM→출력)을 세로 3단으로 세웠다.
    ** 설계 폭 = 지면 폭 ** 이라 축소가 없다 — gen_figs_data.py 쪽 단내 그림들이
    쓰는 1.099배 글자 부풀리기가 여기엔 필요 없다(그것은 215pt 설계를 195.6pt 에
    넣을 때의 보정이다). 가장 작은 글자 6.5pt(10-18 전 6.0)가 그대로 찍힌다.

    담은 것은 전과 같다: 리전마다 독립(× 8 regions), 피처 13장(공통 10 + 기상 3),
    은닉 64·2층, 미래 24 h 기상이 FC 에서 합류(24×3=72), 출력 Ĉ_r(t…t+23).
    2026-10-18(82 점검4 E [5]): 출력 "t … t+24" 는 값 25개로 읽혔다 — 본문은 24개(3.2절 "i=24 는 t+23 의 예측")라 t+23.
    """
    W, H = 196, 212
    # 2026-10-18(82 점검4 E [4]): 작은 글자 6.0 → 6.5 pt. 설계 폭 196 = 지면 폭이라 그대로 찍히는데, 대문자 높이로 재면
    # (÷0.72) 5.7 pt 로 6 pt 기준 아래였다(이 서체 대문자 높이는 글자 크기의 약 0.67~0.69). 6.5 면 약 6.1~6.3 pt.
    SM = 6.5
    L = [head(W, H, "그림 2 리전별 LSTM 구조 (단내)")]

    # 바깥 틀 하나만 둥글다. 안쪽 상자는 전부 각진다(모서리 위계).
    L.append(rbox(4, 4, 188, 204, r=10, sw=0.9))
    L.append(txt(186, 15, "\u00d7 8 regions", anchor="end", size=SM))

    # ── ① 입력: 탄소 이력 + 피처 13장 ──
    L += [box(12, 21, 172, 62, sw=1.0),
          ic_cloud(20, 27, 0.45, co2=False),
          spark(48, 28, 64, 11, n=40),
          txt(98, 48, "Carbon intensity, past 168 h", anchor="middle", size=SM)]
    TW, TH, G = 7.0, 7.0, 1.6
    TX, TY = 34, 54
    for k in range(13):
        x = TX + k * (TW + G) + (6 if k >= 10 else 0)
        fill = "#d9d9d9" if k >= 10 else "#fff"
        L.append(f'<rect x="{x:.1f}" y="{TY}" width="{TW}" height="{TH}" '
                 f'fill="{fill}" stroke="{INK}" stroke-width="0.7"/>')
    L += [txt(TX + 5 * (TW + G) - G / 2, 72, "Common 10", anchor="middle", size=SM),
          txt(TX + 6 + 11.5 * (TW + G) - G / 2, 72, "Weather +3", anchor="middle", size=SM)]
    L.append(fat_arrow(98, 85, 98, 97, w=5))

    # ── ② LSTM ──
    L += [box(12, 101, 172, 62, sw=1.0),
          txt(20, 115, "LSTM", size=FB, bold=True),
          txt(20, 127, "Hidden 64 \u00b7 2 layers", size=SM),
          txt(176, 115, "+ future 24 h weather", anchor="end", size=SM),
          txt(176, 125, "Weather regions only \u00b7 24\u00d73 = 72", anchor="end", size=SM),
          # 미래 기상은 출력이 아니라 FC 에서 합류한다(2026-10-08, 70 지적).
          path("M148,129 L148,137", sw=0.8, dash="2.5 1.8")]
    # 마지막 은닉 상태 h(64) 가 FC 로 간다 — FC 입력이 64+72 라는 것을 라벨로 말한다.
    L += [arr(24, 148, 132, 148, 0.9),
          f'<text x="76" y="144" text-anchor="middle" font-size="{SM}">'
          f'<tspan font-style="italic">h</tspan> (64)</text>',
          box(134, 138, 26, 20, sw=0.8),
          txt(147, 152, "FC", anchor="middle", bold=True, size=FT)]
    L.append(fat_arrow(98, 165, 98, 177, w=5))

    # ── ③ 출력 ──
    L += [box(12, 181, 172, 20, sw=1.0),
          f'<text x="20" y="194" font-size="{FT}"><tspan font-weight="bold">Output  \u0108</tspan>'
          f'<tspan font-size="{SM}" dy="1.5">r</tspan><tspan dy="-1.5"> (t \u2026 t+23)</tspan></text>',
          spark(116, 184, 62, 14, n=24)]

    L.append("</svg>")
    return "\n".join(L)

# ═══════════ 그림 2 · 로드밸런서 (단내, 세로 스택) ═══════════
# 2026-09-21 재설계: "통합(개요) 그림만 전단, 개별 설명 그림은 단내"로 배치
# 규칙이 확정됨(be) — 451pt 가로 배치를 215pt 세로 스택으로 바꾸고, 9pt 글씨를
# 유지하려고 요소 수를 줄였다. 뺀 것: 지연행렬 아이콘, "직전 1h 작업" 별도 박스
# (하나의 입력 박스로 통합), avail_r 원(⊕) 도식과 그 산식(본문 §5.4/식(3)에
# 이미 있어 중복) — 대신 로드밸런서 박스 안 문장에 "avail_r 이하로"만 남겨
# 용량 제약이 있다는 사실 자체는 유지한다. 하단 각주도 뺐다(캡션이 이미
# "슬롯 단위 ILP"라고 말해 반복이었음).
def fig_loadbalancer():
    """공간 이동 — 무릎점 선택을 그림 안에서 실제로 보여준다.

    2026-09-24 재설계(사용자 지시: "그림을 조금 수정해봐, 무턱대고 중복이라 하지 말고").
    이전 판은 "① α 자동 결정 — 슬롯마다 파레토 무릎점"이라고 글로만 적어서, 본문과
    그림 1이 이미 말한 것을 세 번째로 되풀이할 뿐이었다. 이 판은 그 문장을 지우고
    그 자리에 파레토 곡선과 무릎점을 직접 그린다 — 본 논문의 기여가 글이 아니라
    그림으로 보이게 하는 것이 이 그림의 존재 이유다.
    """
    W, H = 215, 232
    L = [head(W, H, "그림 3 공간 이동 · 로드밸런서")]
    L += [txt(107, 13, "공간 이동", anchor="middle", bold=True, size=FB),
          txt(107, 25, "슬롯 단위 ILP 로드밸런서", anchor="middle", size=FT),
          box(10, 33, 195, 24, sw=0.9),
          txt(107, 43, "입력", anchor="middle", size=FT, bold=True),
          txt(107, 53, "예측 Ĉᵣ(t) · 지연 ℓ · 잔여 용량", anchor="middle", size=6.8),
          arr(107, 57, 107, 69),
          box(10, 69, 195, 94, sw=1.3),
          txt(18, 82, "① 슬롯마다 α 를 파레토 무릎점에서", size=6.8, bold=True),
          '<g stroke="%s" stroke-width="0.9" fill="none">'
          '<path d="M34,90 L34,148"/>'
          '<path d="M34,148 L192,148" marker-end="url(#a)"/></g>' % INK,
          txt(30, 94, "탄소", anchor="end", size=6),
          txt(190, 158, "지연", anchor="end", size=6.5),
          '<path d="M38,96 C46,96 54,104 64,117 C74,130 90,138 114,142 '
          'C142,146 170,145 186,144" fill="none" stroke="%s" stroke-width="1.3"/>' % INK,
          '<circle cx="48" cy="98" r="2.4" fill="#fff" stroke="%s" stroke-width="1"/>' % INK,
          txt(48, 94, "α=0", anchor="middle", size=6),
          '<circle cx="186" cy="144" r="2.4" fill="#fff" stroke="%s" stroke-width="1"/>' % INK,
          txt(184, 139, "α=1", anchor="middle", size=6),
          '<path d="M71,123 l2.1,4.4 4.8,0.6 -3.5,3.4 0.9,4.8 -4.3,-2.3 -4.3,2.3 '
          '0.9,-4.8 -3.5,-3.4 4.8,-0.6 z" fill="%s"/>' % INK,
          txt(81, 119, "무릎점 → α*", size=6.5, bold=True),
          txt(81, 129, "한계수익이 정점", size=6),
          arr(107, 163, 107, 175),
          box(10, 175, 195, 32, sw=1.3),
          txt(107, 188, "② ILP 배정", anchor="middle", bold=True, size=FT),
          txt(107, 200, "리전별 동시 실행 ≤ availᵣ  (식 3)", anchor="middle", size=6.8),
          arr(107, 207, 107, 218),
          txt(107, 227, "배정 xⱼᵣ  →  R₁ … R\u2099", anchor="middle", bold=True, size=FT)]
    L.append("</svg>")
    return "\n".join(L)

# ═══════════ 그림 3 · 시간 이동 스케줄러 (단내, 세로 스택) ═══════════
def fig_scheduler():
    """시간 이동 — 용량으로 막힌 슬롯을 그림 안에서 보여준다.

    2026-09-24 재설계. 이전 판은 탄소 곡선에서 최저점을 고르는 그림이었는데, 그것만
    으로는 §5.5(용량을 보지 않는 시간 이동)와 §5.6(Algorithm 1)이 구분되지 않는다.
    본 논문의 기여는 "최저점을 고른다"가 아니라 "자리가 없는 슬롯을 빼고 고른다"이므로,
    막힌 슬롯을 빗금으로 표시해 선택이 최저점이 아닌 곳으로 가는 것을 한 그림에 담는다.
    """
    W, H = 215, 244
    L = [head(W, H, "그림 4 시간 이동 · 용량 인지 스케줄러")]
    L += ['<defs><pattern id="hx" width="4" height="4" patternUnits="userSpaceOnUse" '
          'patternTransform="rotate(45)">'
          '<line x1="0" y1="0" x2="0" y2="4" stroke="%s" stroke-width="0.7"/>'
          '</pattern></defs>' % INK,
          txt(107, 13, "시간 이동", anchor="middle", bold=True, size=FB),
          txt(107, 25, "용량 인지 마감 스케줄러", anchor="middle", size=FT),
          box(10, 33, 195, 24, sw=0.9),
          txt(107, 43, "입력", anchor="middle", size=FT, bold=True),
          txt(107, 53, "작업 j · 리전 r(j) · 예측 Ĉ · 잔여 자리",
              anchor="middle", size=6.8),
          arr(107, 57, 107, 69),
          box(10, 69, 195, 122, sw=1.3),
          txt(107, 81, "마감 안에서, 자리 있는 슬롯 중 최소", anchor="middle",
              size=6.8, bold=True),
          txt(16, 93, "gCO₂", size=6), txt(16, 101, "/kWh", size=6),
          '<g stroke="%s" stroke-width="1" fill="none">'
          '<path d="M32,88 L32,158"/>'
          '<path d="M32,158 L192,158" marker-end="url(#a)"/></g>' % INK,
          '<path d="M36,96 C56,104 68,140 90,150 C110,158 132,146 152,118 '
          'C162,104 168,98 174,96" fill="none" stroke="%s" stroke-width="1.4"/>' % INK,
          '<rect x="76" y="94" width="26" height="64" fill="url(#hx)" opacity="0.45"/>',
          '<rect x="76" y="94" width="26" height="64" fill="none" stroke="%s" '
          'stroke-width="0.8" stroke-dasharray="2 1.5"/>' % INK,
          txt(89, 106, "자리", anchor="middle", size=6, bold=True),
          txt(89, 115, "없음", anchor="middle", size=6, bold=True),
          '<path d="M36,96 C56,104 68,140 90,150 C110,158 132,146 152,118 '
          'C162,104 168,98 174,96" fill="none" stroke="%s" stroke-width="1.4"/>' % INK,
          '<rect x="104" y="141" width="25" height="15" fill="#fff" stroke="%s" '
          'stroke-width="1.7"/>' % INK,
          txt(116, 152, "선택", anchor="middle", size=6.5),
          '<line x1="170" y1="88" x2="170" y2="158" stroke="%s" stroke-width="1.1" '
          'stroke-dasharray="3 2"/>' % INK,
          txt(170, 85, "마감", anchor="middle", size=6.5),
          '<g stroke="%s" stroke-width="0.8" fill="none"><path d="M36,164 L170,164"/>'
          '<path d="M36,161 L36,167"/><path d="M170,161 L170,167"/></g>' % INK,
          txt(103, 174, "탐색 윈도우", anchor="middle", size=6.5),
          txt(107, 186, "막힌 슬롯을 빼므로 최저점이 아닐 수 있다",
              anchor="middle", size=6),
          arr(107, 191, 107, 203),
          box(45, 203, 124, 28, sw=1.1),
          txt(107, 215, "실행 시각 τⱼ", anchor="middle", bold=True, size=FT),
          txt(107, 226, "마감은 하드 · 용량은 소프트", anchor="middle", size=6.3)]
    L.append("</svg>")
    return "\n".join(L)

# 2026-09-24: 뒤 두 개의 이름을 바꾼다. gen_figs_data.py 가 같은 이름의 .png 를
# 내므로(fig3_loadbalancer.png, fig4_scheduler.png), 이 SVG 를 PNG 로 굽는 순간
# 실측 그림이 덮여 사라진다. 실제로 그림 7 이 개념도로 바뀌어 있었다.
# 본문에 실린 것은 실측 그림 쪽이고, 아래 둘은 보관용 개념도다.
for fn, name in ((fig_architecture, "fig1_architecture"), (fig_forecast, "fig2_forecast"),
                 (fig_loadbalancer, "figS_loadbalancer_개념도"),
                 (fig_scheduler, "figS_scheduler_개념도")):
    # 2026-09-24: cwd에 쓰던 것을 스크립트 옆으로 고정한다. 저장소 루트에서
    # 실행하면 루트가 오염되고, 정작 paper/diagram의 파일은 갱신되지 않았다.
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), name + ".svg")
    open(out, "w", encoding="utf-8").write(fn())
    print("wrote", out)
