# -*- coding: utf-8 -*-
"""CAST 전체 아키텍처 그림 — 컬러판/흑백판.

구성은 사용자가 제시한 두 예시를 따른다.
  · CASPER (ACM) 아키텍처 그림 — 시스템 경계 박스, 바깥에서 들어오는 입력 화살표,
    아래에 배치한 리전들, 그리고 화살표마다 붙은 데이터 이름.
  · 사용자 칠판 스케치 — Jobs → 로드밸런서 → 스케줄러 → R1..Rn,
    LSTM이 로드밸런서와 스케줄러 **양쪽**에 공급.

리전 수는 N으로 둔다. 실험은 8개로 했지만 설계상 고정이 아니다.

데이터 흐름을 화살표마다 명시한다:
  탄소집약도 이력 → LSTM      : 과거 168 h 시계열
  LSTM → 공간 이동 / 시간 이동 : Ĉ(r, t)  예측 탄소집약도 N × 24 h
  작업 요청 → 공간 이동        : 작업 j (자원 · 마감)
  리전 간 지연 → 공간 이동     : ℓ(o, r)  지연 행렬 N × N
  공간 이동 → 시간 이동        : 배정 리전 r(j)
  시간 이동 → 리전             : 실행 (리전, 시각)
  리전 → 공간 이동             : avail_r  슬롯별 잔여 용량  ← 되먹임

IEEE 규격: 최종 인쇄 크기 작도(1단위 = 1pt), 글씨 9~10pt,
          색만으로 뜻을 나르지 않기 — 컬러판과 흑백판이 형태로 1:1 대응.
실행: python3 gen_arch.py
"""
W, H = 451, 250
FS, FB = 9, 10
SUB = '<tspan font-size="6.5" dy="1.5">%s</tspan><tspan dy="-1.5"></tspan>'

class P:
    def __init__(s, c):
        s.color = c; s.ink = "#000000"
        s.aux  = "#EDEDED" if c else "#EFEFEF"
        s.sys  = "#F7F9FB" if c else "#FFFFFF"
        s.pred = "#EFE9F5" if c else "#FFFFFF"
        s.spc  = "#E4EDF5" if c else "#FFFFFF"
        s.tim  = "#E5EFE5" if c else "#FFFFFF"
        s.reg  = "#F2F2F2" if c else "#FFFFFF"

def build(color):
    p = P(color); o = []; a = o.append
    a(f'''<!-- CAST 전체 아키텍처 · {"컬러판" if color else "흑백판"} · gen_arch.py 로 생성 (직접 편집 금지)
     1단위 = 1pt, 폭 {W}pt = 본문 폭(2단 span). 100% 크기로 삽입할 것. -->
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}pt" height="{H}pt"
     font-family="'Malgun Gothic','Apple SD Gothic Neo','Noto Sans KR',sans-serif"
     font-size="{FS}" fill="{p.ink}">
<defs>
  <marker id="a" viewBox="0 0 10 10" refX="9.5" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
    <path d="M0,0 L10,5 L0,10 z" fill="{p.ink}"/></marker>
</defs>
<rect width="{W}" height="{H}" fill="#fff"/>''')

    # ══ 시스템 경계를 먼저 : 뒤에 그리면 입력 화살표를 덮는다 ══
    a(f'''<rect x="82" y="60" width="304" height="118" rx="7" fill="{p.sys}" stroke="{p.ink}" stroke-width="1.5"/>
<text x="89" y="72" font-weight="bold" font-size="{FB}">CAST</text>''')

    # ══ 바깥 입력 : 위에서 ══
    a(f'''<text x="192" y="12" text-anchor="middle" font-weight="bold">작업 요청</text>
<g stroke="{p.ink}" stroke-width="0.8"><rect x="168" y="16" width="48" height="22" fill="{p.aux}"/></g>
<g stroke="{p.ink}" stroke-width="0.6" fill="none">
  <line x1="174" y1="22" x2="210" y2="22"/><line x1="174" y1="27" x2="210" y2="27"/>
  <line x1="174" y1="32" x2="210" y2="32" stroke-dasharray="2 1.5"/></g>
<text x="192" y="50" text-anchor="middle" font-size="8">작업 j · 자원 · 마감</text>
<path d="M192,52 L192,68 L215,68 L215,86" fill="none" stroke="{p.ink}" stroke-width="1.4" marker-end="url(#a)"/>

<text x="274" y="12" text-anchor="middle" font-weight="bold">리전 간 지연</text>
<g stroke="{p.ink}" stroke-width="0.8"><rect x="250" y="16" width="48" height="22" fill="{p.aux}"/></g>
<g stroke="{p.ink}" stroke-width="0.7" fill="none"><path d="M260,33 L274,22 L288,33 Z"/></g>
<g fill="{p.ink}"><circle cx="260" cy="33" r="1.4"/><circle cx="288" cy="33" r="1.4"/><circle cx="274" cy="22" r="1.4"/></g>
<text x="274" y="50" text-anchor="middle" font-size="8">ℓ(o, r) · N × N</text>
<path d="M274,52 L274,68 L240,68 L240,86" fill="none" stroke="{p.ink}" stroke-width="1.4" marker-end="url(#a)"/>''')

    # ══ 바깥 입력 : 왼쪽에서 ══
    a(f'''<g stroke="{p.ink}" stroke-width="0.8"><rect x="8" y="92" width="56" height="28" fill="{p.aux}"/></g>
<text x="36" y="103" text-anchor="middle" font-size="8">gCO₂/kWh</text>
<path d="M14,115 L26,107 L36,111 L48,105 L60,104" fill="none" stroke="{p.ink}" stroke-width="1"/>
<text x="36" y="132" text-anchor="middle" font-weight="bold">탄소집약도 이력</text>
<text x="36" y="143" text-anchor="middle">N 리전 · 시간별</text>
<line x1="64" y1="106" x2="90" y2="106" stroke="{p.ink}" stroke-width="1.4" marker-end="url(#a)"/>
<rect x="64" y="93" width="26" height="10" fill="#fff"/>
<text x="77" y="101" text-anchor="middle" font-size="8">168 h</text>''')

    # ══ 시스템 경계 ══
    for x, fill, t1, t2 in ((92, p.pred, "LSTM 예측", "168 h → 24 h"),
                            (204, p.spc, "공간 이동", "ILP · 용량"),
                            (316, p.tim, "시간 이동", "마감 인지")):
        a(f'<rect x="{x}" y="86" width="66" height="46" fill="{fill}" stroke="{p.ink}" stroke-width="1"/>')
        a(f'<text x="{x+33}" y="106" text-anchor="middle" font-weight="bold">{t1}</text>')
        a(f'<text x="{x+33}" y="120" text-anchor="middle" font-size="8">{t2}</text>')

    # ══ 단계 사이 데이터 흐름 ══
    a(f'''<line x1="158" y1="109" x2="202" y2="109" stroke="{p.ink}" stroke-width="1.1" marker-end="url(#a)"/>
<text x="180" y="103" text-anchor="middle" font-style="italic">Ĉ(r, t)</text>
<text x="180" y="121" text-anchor="middle" font-size="8">N × 24 h</text>
<line x1="270" y1="109" x2="314" y2="109" stroke="{p.ink}" stroke-width="1.1" marker-end="url(#a)"/>
<text x="292" y="103" text-anchor="middle">리전 r(j)</text>
<text x="292" y="121" text-anchor="middle" font-size="8">배정 결과</text>

<path d="M125,132 L125,168 L349,168 L349,134" fill="none" stroke="{p.ink}" stroke-width="1.1" marker-end="url(#a)"/>
<rect x="212" y="162" width="34" height="11" fill="{p.sys}"/>
<text x="229" y="171" text-anchor="middle" font-style="italic">Ĉ(r, t)</text>''')

    # ══ 출력과 되먹임 ══
    a(f'''<path d="M365,132 L365,196" fill="none" stroke="{p.ink}" stroke-width="1.3" marker-end="url(#a)"/>
<rect x="368" y="146" width="62" height="24" fill="#fff"/>
<text x="371" y="156" font-size="8">실행 결정</text>
<text x="371" y="167" font-size="8">(리전, 시각)</text>

<path d="M398,210 L432,210 L432,76 L262,76 L262,84" fill="none" stroke="{p.ink}" stroke-width="1.1"
      stroke-dasharray="4 2.5" marker-end="url(#a)"/>
<rect x="270" y="62" width="116" height="12" fill="{p.sys}"/>
<text x="384" y="72" text-anchor="end" font-size="8">avail{SUB % "r"} · 슬롯별 잔여 용량</text>''')

    # ══ 리전 : 개수는 N ══
    a(f'<text x="6" y="192" font-weight="bold">리전 R<tspan font-size="6.5" dy="1.5">1</tspan>'
      f'<tspan dy="-1.5"> … R</tspan><tspan font-size="6.5" dy="1.5">N</tspan></text>')
    for x, lab in ((70, "1"), (154, "2"), (238, "3"), (334, "N")):
        a(f'<rect x="{x}" y="196" width="64" height="28" rx="3" fill="{p.reg}" stroke="{p.ink}" stroke-width="0.9"/>')
        for j in range(3):
            a(f'<rect x="{x+9}" y="{201+j*7}" width="46" height="4" fill="#fff" stroke="{p.ink}" stroke-width="0.5"/>')
        a(f'<text x="{x+32}" y="236" text-anchor="middle">R<tspan font-size="6.5" dy="1.5">{lab}</tspan></text>')
    a(f'<text x="318" y="214" text-anchor="middle" font-weight="bold">⋯</text>')
    a(f'<text x="150" y="192" font-style="italic">동시 실행 수 ≤ avail{SUB % "r"}</text>')
    a('</svg>')
    return "\n".join(o)

for n, c in (("fig_architecture.svg", True), ("fig_architecture_bw.svg", False)):
    open(n, "w", encoding="utf-8").write(build(c)); print("wrote", n)
