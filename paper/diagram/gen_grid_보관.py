# -*- coding: utf-8 -*-
"""CAST 전체 구조 그림 — 컬러판/흑백판.

의도:
  이 그림은 구현 명세가 아니라 "우리가 하려는 것"을 한 장으로 보여주는 개념도다.
  하이퍼파라미터·공식은 후속 상세 그림(LSTM 구조 / 공간 이동 / 시간 이동)이 맡는다.

핵심 장치 — 공간 × 시간 격자:
  세로축 = 리전, 가로축 = 시각, 음영 = 탄소집약도.
  작업 하나가 (홈 리전, 제출 시각)에서 출발해 세로로(공간 이동) 그리고 가로로(시간 이동)
  옮겨가 저탄소 칸에 도달한다. 시공간 스케줄러라는 논문의 주장 자체가 그림이 된다.
  가장 깨끗한 리전(FR)으로 가는 경로는 용량 때문에 막히고, 마감이 가로 이동을 잘라낸다 —
  이 논문의 두 제약이 그림에 그대로 보인다.

격자는 2025-10-18 실측이다 (coder 확인, lstm_eval/*_eval_records.csv 의 y_true).
  그날은 8리전 각각의 일평균이 연평균에서 가장 적게 벗어난 "가장 평범한 날"로 골랐다 —
  체리피킹의 반대 방향이다. 단위 gCO2/kWh.

  주의: 캘리포니아는 "태양광으로 낮에 하락"이 아니라 "저녁 이후 하락"이다.
  연중 시간대 평균으로 CAL은 10시 최고(211) · 19시 최저(72)로, 독일(11시 최저 188 ·
  20시 최고 329)과 반대 방향이다. 본문 문단 145의 서술과 어긋나므로 본문도 고쳐야 한다.

IEEE 규격: 최종 인쇄 크기 작도(1단위 = 1pt), 글씨 9~10pt,
          색만으로 뜻을 나르지 않기 — 컬러판의 5단계 음영이 흑백판에서 명도 5단계로 대응.
실행: python3 gen_arch.py
"""
W, H = 451, 252
FS, FB = 9, 10
X0, CW, NC = 52, 31, 12          # 격자 원점 · 칸 폭 · 시각 칸 수 (2시간 단위)
Y0, RH = 62, 15                  # 격자 상단 · 행 높이

# 위에서 아래로 = 탄소 높은 리전 → 낮은 리전. 아래로 갈수록 깨끗하다.
# 2025-10-18 실측 (gCO2/kWh), 2시간 간격 12칸. 탄소 높은 순 정렬.
RAW = [
    ("IN",  [611, 545, 443, 415, 429, 505, 594, 587, 614, 617, 625, 623]),
    ("KR",  [380, 373, 371, 368, 375, 374, 374, 378, 360, 358, 359, 353]),
    ("JP",  [290, 268, 299, 364, 386, 391, 402, 402, 399, 399, 396, 367]),
    ("TEX", [385, 346, 331, 306, 312, 333, 350, 285, 229, 218, 230, 259]),
    ("DE",  [425, 416, 433, 441, 303, 179, 195, 343, 440, 387, 344, 284]),
    ("NY",  [246, 244, 249, 237, 228, 222, 227, 220, 223, 230, 235, 230]),
    ("CAL", [164, 207, 211, 236, 251, 263, 266, 224,  67,  55,  59,  74]),
    ("FR",  [ 15,  15,  14,  14,   9,   4,   5,   6,  13,  16,  15,   9]),
]
BINS = [50, 150, 250, 400]        # gCO2/kWh 경계 -> 음영 5단계
def level(v): return sum(v >= b for b in BINS)
ROWS = [(n, [level(v) for v in vs]) for n, vs in RAW]

HOME, DEST, BLOCKED = 4, 6, 7     # DE -> CAL, 막힌 곳은 FR
T_SUB, T_RUN = 0, 9              # 실제 작업 j_087514 : 01:16 제출 -> 18:16 실행     # 제출 · 실행 · 마감 칸

class P:
    def __init__(s, c):
        s.color = c; s.ink = "#000000"
        s.aux  = "#EDEDED" if c else "#EEEEEE"
        s.acc  = "#B5451B" if c else "#000000"
        s.ramp = (["#EEF4E9", "#CFE0BC", "#EBDCA6", "#DDA976", "#C1705C"] if c
                  else ["#FFFFFF", "#DEDEDE", "#BABABA", "#8E8E8E", "#606060"])

def cx(c): return X0 + c * CW + CW / 2
def cy(r): return Y0 + r * RH + RH / 2

def build(color):
    p = P(color); o = []; a = o.append
    a(f'''<!-- CAST 전체 구조 · {"컬러판" if color else "흑백판"} · gen_arch.py 로 생성 (직접 편집 금지)
     1단위 = 1pt, 폭 {W}pt = 본문 폭(2단 span). 100% 크기로 삽입할 것. -->
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}pt" height="{H}pt"
     font-family="'Malgun Gothic','Apple SD Gothic Neo','Noto Sans KR',sans-serif"
     font-size="{FS}" fill="{p.ink}">
<defs>
  <marker id="a" viewBox="0 0 10 10" refX="9.5" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
    <path d="M0,0 L10,5 L0,10 z" fill="{p.ink}"/></marker>
  <marker id="ac" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5.5" markerHeight="5.5" orient="auto-start-reverse">
    <path d="M0,0 L10,5 L0,10 z" fill="{p.acc}"/></marker>
</defs>
<rect width="{W}" height="{H}" fill="#fff"/>''')

    # ───── 상단 : 결정 파이프라인 ─────
    boxes = [("탄소 이력", "작업 요청"), ("LSTM 예측", "향후 24 h"),
             ("공간 이동", "리전 선택"), ("시간 이동", "실행 시각"), ("8 리전", "실행")]
    for i, (t1, t2) in enumerate(boxes):
        x = 6 + i * 82
        fill = p.aux if i in (0, 4) else "#fff"
        a(f'<rect x="{x}" y="10" width="70" height="26" fill="{fill}" stroke="{p.ink}" stroke-width="0.8"/>')
        a(f'<text x="{x+35}" y="21" text-anchor="middle" font-weight="bold">{t1}</text>')
        a(f'<text x="{x+35}" y="32" text-anchor="middle">{t2}</text>')
        if i < 4:
            a(f'<line x1="{x+70}" y1="23" x2="{x+80}" y2="23" stroke="{p.ink}" stroke-width="0.9" marker-end="url(#a)"/>')
    # 예측값을 두 단계가 함께 쓴다
    a(f'''<g stroke="{p.ink}" stroke-width="0.8" fill="none">
  <path d="M123,36 L123,44 L287,44 L287,38" marker-end="url(#a)"/></g>
<rect x="196" y="39" width="18" height="10" fill="#fff"/>
<text x="205" y="47" text-anchor="middle" font-style="italic">Ĉ</text>''')

    # ───── 격자 : 세로 = 리전, 가로 = 시각, 음영 = 탄소집약도 ─────
    for r, (name, lv) in enumerate(ROWS):
        for c, v in enumerate(lv):
            a(f'<rect x="{X0+c*CW}" y="{Y0+r*RH}" width="{CW}" height="{RH}" '
              f'fill="{p.ramp[v]}" stroke="#fff" stroke-width="0.6"/>')
        w = "bold" if r in (HOME, DEST) else "normal"
        a(f'<text x="48" y="{cy(r)+3}" text-anchor="end" font-weight="{w}">{name}</text>')
    a(f'<rect x="{X0}" y="{Y0}" width="{NC*CW}" height="{len(ROWS)*RH}" fill="none" stroke="{p.ink}" stroke-width="0.8"/>')

    a(f'<text x="6" y="{Y0-6}" font-weight="bold">리전</text>')
    for c in range(0, NC, 2):
        a(f'<line x1="{cx(c)}" y1="{Y0+len(ROWS)*RH}" x2="{cx(c)}" y2="{Y0+len(ROWS)*RH+3}" stroke="{p.ink}" stroke-width="0.6"/>')
        a(f'<text x="{cx(c)}" y="{Y0+len(ROWS)*RH+13}" text-anchor="middle">{c*2}</text>')
    a(f'<text x="{X0+NC*CW}" y="{Y0+len(ROWS)*RH+13}" text-anchor="end">시각 (h)</text>')

    # 마감은 격자 밖(익일 04:34)이라 오른쪽 끝에 주석으로 둔다
    xe = X0 + NC * CW
    a(f'<line x1="{xe-52}" y1="{Y0-10}" x2="{xe}" y2="{Y0-10}" stroke="{p.acc}" stroke-width="1" marker-end="url(#ac)"/>')
    a(f'<text x="{xe}" y="{Y0-14}" text-anchor="end" fill="{p.acc}">마감 : 익일 04:34</text>')

    # 제출 · 공간 이동 · 시간 이동 · 실행
    a(f'<rect x="{X0+T_SUB*CW}" y="{Y0+HOME*RH}" width="{CW}" height="{RH}" fill="none" stroke="{p.ink}" stroke-width="1.6"/>')
    a(f'<rect x="{X0+T_RUN*CW}" y="{Y0+DEST*RH}" width="{CW}" height="{RH}" fill="none" stroke="{p.acc}" stroke-width="2"/>')
    xs = cx(T_SUB) - 6
    a(f'<path d="M{xs},{cy(HOME)+9} L{xs},{cy(DEST)-8}" stroke="#fff" stroke-width="4" fill="none"/>')
    a(f'<path d="M{xs},{cy(HOME)+9} L{xs},{cy(DEST)-8}" stroke="{p.acc}" stroke-width="1.8" fill="none" marker-end="url(#ac)"/>')
    a(f'<path d="M{cx(T_SUB)+10},{cy(DEST)} L{cx(T_RUN)-12},{cy(DEST)}" stroke="#fff" stroke-width="4" fill="none"/>')
    a(f'<path d="M{cx(T_SUB)+10},{cy(DEST)} L{cx(T_RUN)-12},{cy(DEST)}" stroke="{p.acc}" stroke-width="1.8" fill="none" marker-end="url(#ac)"/>')
    # 용량 때문에 막힌 경로
    xb = cx(T_SUB) + 7
    a(f'<path d="M{xb},{cy(HOME)+9} L{xb},{cy(BLOCKED)-8}" stroke="#fff" stroke-width="4" fill="none"/>')
    a(f'<path d="M{xb},{cy(HOME)+9} L{xb},{cy(BLOCKED)-8}" stroke="{p.ink}" stroke-width="1" fill="none" stroke-dasharray="2.5 2"/>')
    a(f'<circle cx="{xb}" cy="{cy(BLOCKED)}" r="7" fill="#fff" stroke="none"/>')
    a(f'<path d="M{xb-5},{cy(BLOCKED)-5} L{xb+5},{cy(BLOCKED)+5} M{xb+5},{cy(BLOCKED)-5} L{xb-5},{cy(BLOCKED)+5}" '
      f'stroke="{p.ink}" stroke-width="1.7" fill="none"/>')

    def tag(x, y, s, col=None, anchor="middle", w=None):
        w = w or len(s) * 9 + 6
        a(f'<rect x="{x-w/2}" y="{y-8}" width="{w}" height="11" fill="#fff"/>')
        a(f'<text x="{x}" y="{y}" text-anchor="{anchor}" fill="{col or p.ink}">{s}</text>')

    tag(cx(T_SUB), Y0 - 6, "제출 01:16", w=60)
    tag(cx(T_SUB) + 44, cy(5) + 3, "공간 이동", p.acc, w=54)
    tag(cx(3) + 4, cy(DEST) - 6, "시간 이동", p.acc, w=54)
    tag(cx(T_RUN), cy(DEST) - 14, "실행 18:16", p.acc, w=60)
    tag(cx(T_SUB) + 62, cy(BLOCKED) + 3, "용량 포화 12/12", w=82)

    # ───── 범례 ─────
    yl = Y0 + len(ROWS) * RH + 38
    a(f'<text x="6" y="{yl-14}" font-style="italic">작업 j_087514 (독일 제출, 2025-10-18 실측) · 680 g → 194 g, −71.4 %</text>')
    a(f'<text x="6" y="{yl+8}">탄소집약도</text>')
    for i, col in enumerate(p.ramp):
        a(f'<rect x="{64+i*17}" y="{yl}" width="17" height="10" fill="{col}" stroke="{p.ink}" stroke-width="0.5"/>')
    for i, b in enumerate(BINS):
        a(f'<text x="{64+(i+1)*17}" y="{yl+19}" text-anchor="middle" font-size="8">{b}</text>')
    a(f'<text x="{64+5*17+5}" y="{yl+8}">gCO₂/kWh</text>')
    a(f'<line x1="238" y1="{yl+5}" x2="256" y2="{yl+5}" stroke="{p.acc}" stroke-width="1.8" marker-end="url(#ac)"/>')
    a(f'<text x="260" y="{yl+8}">CAST가 옮긴 경로</text>')
    a(f'<line x1="348" y1="{yl+5}" x2="366" y2="{yl+5}" stroke="{p.ink}" stroke-width="1" stroke-dasharray="2.5 2"/>')
    a(f'<text x="370" y="{yl+8}">용량 때문에 막힌 경로</text>')
    a('</svg>')
    return "\n".join(o)

for n, c in (("fig_architecture.svg", True), ("fig_architecture_bw.svg", False)):
    open(n, "w", encoding="utf-8").write(build(c)); print("wrote", n)
