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

def ic_cloud(x, y, s=1.0, label=""):
    """CO₂ 구름 — 탄소집약도 입력."""
    g = [f'<g transform="translate({x},{y}) scale({s})">']
    g.append(f'<path d="M12,14 a7,7 0 0,1 13,-4 a6,6 0 0,1 10,5 a5.5,5.5 0 0,1 -1,11 '
             f'L10,26 a6,6 0 0,1 2,-12 z" fill="{INK}"/>')
    g.append(f'<circle cx="8" cy="9" r="5" fill="{INK}"/>')
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
    """전체 구조 — 2026-09-24 CASPER 계열 작화로 재설계.

    사용자: "그림들이 너무 네모네모해 diagram 같아서 진짜 그냥 그림처럼 그려주면
    안되나…? 그 casper 논문 보면 되게 그림그림 하잖아."

    CASPER Fig.2 를 뜯어 얻은 것: 사물 아이콘(CO₂ 구름·사람·서버랙), 둥근 모서리
    컨테이너, 굵기가 다른 화살표, 기울어진 리본 라벨. 컬러는 못 쓰므로 선의 굵기와
    채움, 아이콘의 형태로 같은 결을 낸다.

    이 그림이 말하는 것은 전과 같다 — 공간 이동은 현재 값 하나로 족하고 시간 이동은
    24 h 곡선 전체가 필요하다는 대비, 그리고 시간 이동이 잔여 용량을 되받는다는 것.
    """
    W, H = 215, 238
    L = [head(W, H, "그림 1 CAST 전체 구조")]

    # ── 입력: 탄소 이력(구름)과 작업(문서 묶음) ──
    L += [ic_cloud(16, 6, 0.70, "탄소집약도 이력"),
          ic_jobs(148, 8, 0.68, "작업 · 마감")]
    L += [ribbon(62, 20, "N 리전 · 시간별", -10, 6.0)]

    # ── CAST 본체 (둥근 컨테이너) ──
    L += [rbox(10, 54, 195, 116, 10, 1.7),
          txt(18, 67, "CAST", bold=True, size=FB)]

    # 예측 — 신경망 아이콘 + 라벨
    L += [rbox(20, 74, 78, 34, 6, 1.1),
          ic_brain(24, 79, 0.62),
          txt(64, 88, "LSTM 예측", anchor="middle", bold=True, size=FT),
          txt(64, 99, "168 h → 24 h", anchor="middle", size=6.0)]

    # 공간 이동 — 지구 아이콘
    L += [rbox(118, 74, 78, 34, 6, 1.1),
          ic_globe(122, 81, 0.62),
          txt(162, 88, "공간 이동", anchor="middle", bold=True, size=FT),
          txt(162, 99, "ILP · 용량", anchor="middle", size=6.0)]

    # 시간 이동 — 시계 아이콘
    L += [rbox(118, 122, 78, 34, 6, 1.1),
          ic_clock(122, 129, 0.62),
          txt(162, 136, "시간 이동", anchor="middle", bold=True, size=FT),
          txt(162, 147, "마감 · 용량 인지", anchor="middle", size=6.0)]

    # 입력 → 본체
    # 2026-09-24: 가로 구간이 y=66 이라 "CAST" 글자를 관통했다(fd 가 400dpi 에서 발견).
    # 컨테이너 위쪽(y=50)으로 올려 글자 밖으로 뺀다 — 세로 구간 x=48 은 글자 오른쪽 끝을
    # 4pt 차이로 비껴간다.
    L += [path("M31,44 L31,50 L48,50 L48,74", sw=1.3),
          path("M160,38 L160,50 L186,50 L186,74", sw=1.3)]

    # 값 하나(가는 화살표) vs 곡선 전체(굵은 화살표) — 이 대비가 요지
    L += [arr(98, 88, 116, 88, 1.2),
          txt(107, 83, "Ĉ(t)", anchor="middle", it=True, size=6.0),
          txt(107, 97, "값 1개", anchor="middle", size=6.0)]
    # 2026-09-24(b6 지적, 4d 수정): 굵은 화살표의 끝(59,139)과 가로선의 시작
    # (62,139)이 겹쳐 "굵은 화살표가 상자를 가리키는지, 가로선이 그 자리에서
    # 그냥 시작하는지"가 모호했다. 상자를 화살표 축(x=59)에 맞춰 옮겨 굵은
    # 화살표 → 상자 → 상자 오른쪽 변에서 가로선, 순서가 보이게 한다.
    L += [fat_arrow(59, 108, 59, 132, 5),
          f'<rect x="38" y="132" width="42" height="24" fill="#fff"/>',
          box(40, 133, 38, 16, sw=0.8), spark(43, 135, 32, 12),
          path("M78,141 L116,141", sw=1.3),
          txt(59, 154, "24 h 곡선", anchor="middle", size=6.0)]

    # 공간 → 시간 (리전 확정)
    L += [arr(157, 108, 157, 120, 1.2),
          ribbon(120, 112, "리전 r(j)", 0, 6.0)]

    # 되먹임 — 2026-09-24(b6 지적, 4d 재확인): 이전 그림은 이 점선이 시간 이동
    # 상자에서 나와 공간 이동 상자 위로 들어가, 마치 "시간 이동 → 공간 이동"
    # 되먹임처럼 보였다. 코드에는 그런 경로가 없다 — capacity.py:112~115
    # CapacityLedger.__init__ 은 빈 장부로 시작하고(공간 이동의 점유를 물려받지
    # 않음), 그 장부를 채우는 곳은 emit() 안의 led.reserve() 뿐으로 시간 이동
    # 자신의 배치다(capacity.py:341, 372). 공간 이동(simulator.py:226 run_count,
    # :251 avail)은 완전히 별개 장부를 쓴다 — 두 단계 사이의 용량 되먹임은
    # 없다. avail_r 은 시간 이동 상자 **자신**의 자기 되먹임이므로, 상자
    # 밖으로 나가는 화살표가 아니라 같은 상자로 돌아오는 짧은 고리로 바꾼다.
    L += [path("M196,133 L202,133 L202,145 L196,145", sw=0.9, dash="3 1.8"),
          txt(203, 119, "availᵣ", anchor="end", it=True, size=6.0)]

    # ── 출력: 리전 랙 ──
    L += [path("M157,156 L157,176", sw=1.4),
          ribbon(108, 170, "실행 (리전, 시각)", 0, 6.0)]
    # 2026-09-24(b6 지적): 유니코드 아래첨자 문자(₁₂₃)는 선언한 한글
    # 서체가 찍지만 Rₙ(U+2099)만 그 서체에 없어 시스템 서체(SFNS)로
    # 넘어가 넷 중 하나만 굵기·높이가 달라 보였다. sb() tspan 아래첨자로
    # 통일해 네 라벨 모두 같은 서체·크기로 찍히게 한다.
    for k, x in enumerate((14, 62, 110, 158)):
        L.append(ic_rack(x, 182, 0.60, "R" + sb(("1", "2", "3", "n")[k])))
    L.append(txt(107, 232, "동시 실행 수 ≤ availᵣ", anchor="middle", it=True, size=6.0))
    L.append("</svg>")
    return "\n".join(L)

# ═══════════ 그림 2 · 탄소 예측 (전단) ═══════════
def fig_forecast():
    """그림 2 — LSTM 구조 (2026-09-24 CASPER 작화로 재작성, 같은 날 글씨 솎아냄).

    내력: 블록도 → 예측곡선 → 다시 구조도. 사용자가 세 번째로 지적했다 —
    "그림들이 너무 네모네모 해 diagram같아서 진짜 그냥 그림처럼 그려주면 안되나…?
    그 casper논문 보면 되게 그림그림 하잖아." 직전 판은 상자가 21개였다.
    상자를 6개로 줄이고, 아이콘(구름·신경망·곡선)과 둥근 컨테이너로 바꾼다.
    피처 13개는 상자 13개가 아니라 **타일 13장**으로 세어 보이게 한다 —
    개수가 요점이지 이름 하나하나가 요점이 아니다(이름은 캡션과 추가자료에 있다).

    2026-09-24 b6 배분(같은 날 두 번째 손질): 사용자 지적 — "그림에 글씨가 너무
    많아. 그림 아래에 붙인 글씨도 있고 그림2글씨도 있으니까 이건 좀 줄여도 될듯."
    본문 캡션이 이미 하는 말을 그림 안에서 되풀이하던 것을 뺐다: dropout·마지막
    은닉 상태(하이퍼파라미터, 추가자료 소관) 두 줄, "향후 24 h/1시간 간격"(출력
    라벨 Ĉᵣ(t…t+24)와 중복), 맨 아래 모델 개수 한 줄("그림이 아니라 글"이라 뺐고
    문구는 캡션 추가안으로 b6에게 넘긴다). 타일 13장은 그대로 둔다 — 이 그림의
    요점이라 손대지 않는다. 줄어든 글씨만큼 본체·출력 상자를 낮춰 전체 높이도
    200→162로 줄인다.

    2026-09-24 b6 재검토: "LSTM 상자와 출력 상자 아래쪽이 꽤 비었다" — 렌더해서
    픽셀 단위로 재 보니(모서리 곡률을 피한 가운데 스트립만 측정) 맞는 말이었다.
    아이콘을 0.75→0.66로 한 번 더 줄이고 본체 40→35, 출력 30→26으로 낮춰 전체
    높이를 162→154로 더 줄인다(11→10쪽 목표에 보탠다). 이 이상 줄이면 아이콘이
    "LSTM"이라는 텍스트 옆에서 뭉개져 안 읽힌다 — 여기서 멈춘다.

    수치 출처는 그대로다: carbon_forecast_lstm/carbon_forecast.py 의
    BASE_FEATURE_COLS 10 + WEATHER_FEATURE_COLS 3 = 13, HIDDEN_SIZE=64,
    NUM_LAYERS=2, dropout=0.2, SEQ_LEN=168, OUTPUT_SIZE=24, 기상 리전은
    WeatherLSTM.fc 입력이 64+72(dropout·마지막 은닉 상태는 이제 그림엔 없고
    추가자료에만 남는다).
    """
    W, H = 215, 154
    L = [head(W, H, "그림 2 리전별 LSTM 구조")]

    # ── 입력 ── (2026-09-24 손질에서 그대로 둔 구역 — 타일이 이 그림의 요점)
    # 왼쪽은 "무엇을 보나"(탄소 곡선 168시간), 오른쪽은 "몇 개를 보나"(타일 13장).
    # 타일은 10 + 3 으로 띄워 공통 피처와 기상 리전 추가분을 셈으로 읽히게 한다.
    L += [rbox(6, 8, 203, 50, r=8, sw=1.0),
          ic_cloud(14, 14, 0.52), spark(13, 36, 44, 11, n=40),
          txt(35, 55, "탄소집약도 과거 168 h", anchor="middle", size=5.8)]
    TX, TY, TW, TH, G = 76, 16, 9.0, 9.0, 2.2
    for k in range(13):
        col, row = k % 7, k // 7
        x = TX + col * (TW + G) + (7 if k >= 10 else 0)
        y = TY + row * (TH + G)
        fill = "#d9d9d9" if k >= 10 else "#fff"
        L.append(f'<rect x="{x}" y="{y}" width="{TW}" height="{TH}" rx="1.8" '
                 f'fill="{fill}" stroke="{INK}" stroke-width="0.8"/>')
    L += [txt(100, 47, "공통 10", anchor="middle", size=5.8),
          txt(178, 47, "기상 +3", anchor="middle", size=5.8),
          txt(178, 55, "(3개 리전만)", anchor="middle", size=5.8),
          ribbon(163, 26, "피처 13", angle=-11, size=5.8),
          fat_arrow(107, 58, 107, 70, w=6)]

    # ── 본체 ── dropout·마지막 은닉 상태 두 줄을 뺀 만큼 56→40→35로 낮췄다.
    # 아이콘도 0.75→0.66로 줄여 "LSTM" 제목 + 아이콘 + 한 줄(은닉 64·2층)만 남는
    # 높이에 맞춘다 — 하이퍼파라미터 세부는 추가자료 A.9 소관.
    L += [rbox(20, 74, 175, 35, r=10),
          txt(29, 86, "LSTM", size=FB, bold=True),
          ic_brain(26, 88, 0.66)]
    L += [txt(78, 98, "은닉 64 · 2층", size=6.4)]
    # 기상 리전만 미래 24 h 날씨를 출력 직전에 합류시킨다.
    # 점선은 라벨 오른쪽 바깥(x=205)으로 돌려 글자를 관통하지 않게 한다.
    L += [txt(189, 86, "+ 미래 24 h 날씨", anchor="end", size=5.8),
          txt(189, 94, "기상 리전만 · 24×3 = 72", anchor="end", size=5.8),
          # 2026-09-24 b6 지적: 점선 시작이 "72" 글자 바로 뒤(x=188)에 붙어 글자·
          # 상자 테두리·점선이 한 점에 몰렸다. 시작을 2pt 물려(190) 글자와 띄운다.
          path("M190,94 L205,94 L205,127 L197,127", sw=0.8, dash="2.5 1.8")]

    L.append(fat_arrow(107, 109, 107, 118, w=6))

    # ── 출력 ── "향후 24 h/1시간 간격"은 라벨 Ĉᵣ(t…t+24)와 같은 말이라 뺐다.
    L += [rbox(20, 119, 175, 26, r=10),
          txt(29, 131, "출력  Ĉ", size=FT, bold=True),
          txt(50, 133, "r", size=5.8),
          txt(54, 131, "(t … t+24)", size=FT),
          spark(34, 135, 104, 8, n=24)]

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
