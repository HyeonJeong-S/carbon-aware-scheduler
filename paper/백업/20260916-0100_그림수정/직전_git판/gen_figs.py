# -*- coding: utf-8 -*-
"""CAST 논문 그림 4종 생성기 — 흑백 SVG 만.

  fig1_architecture   전체 구조   전단 451pt
  fig2_forecast       탄소 예측   단내 215pt
  fig3_loadbalancer   로드밸런서  단내 215pt
  fig4_scheduler      스케줄러    단내 215pt

설계 원칙
  · 식은 넣지 않는다. 식 (6)~(11)은 본문에 이미 조판돼 있어 그림에 다시 넣으면
    순수 중복이고, 본문을 한 줄도 줄여주지 못하면서 그림만 커진다.
    그림은 구조와 흐름만 맡고, 화살표에 흐르는 기호(Ĉ · ℓ · x_jr · avail_r)만 남긴다.
  · 상세 3장은 단내(215pt). 전단 그림은 높이만큼 양쪽 단을 동시에 막지만
    단내는 한쪽만 막아 실효 비용이 절반이다.
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
INK, FS, FB, FT = "#000000", 9, 10, 8

def head(w, h, note):
    return (f'<!-- {note} · gen_figs.py 로 생성 (직접 편집 금지)\n'
            f'     1단위 = 1pt, 폭 {w}pt. 100% 크기로 삽입할 것. -->\n'
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}pt" height="{h}pt"\n'
            f'     font-family="\'Malgun Gothic\',\'Apple SD Gothic Neo\',\'Noto Sans KR\',sans-serif"\n'
            f'     font-size="{FS}" fill="{INK}">\n<defs>\n'
            f'  <marker id="a" viewBox="0 0 10 10" refX="9.5" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">\n'
            f'    <path d="M0,0 L10,5 L0,10 z" fill="{INK}"/></marker>\n'
            f'</defs>\n<rect width="{w}" height="{h}" fill="#fff"/>')

def sb(t):   # 아래첨자
    return f'<tspan font-size="6.5" dy="1.5">{t}</tspan><tspan dy="-1.5"></tspan>'
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

# ═══════════ 그림 1 · 전체 구조 (전단) ═══════════
def fig_architecture():
    W, H = 451, 236
    L = [head(W, H, "그림 1 CAST 전체 구조")]
    L += [txt(178, 12, "작업 요청", anchor="middle", bold=True),
          box(154, 16, 48, 22),
          f'<g stroke="{INK}" stroke-width="0.6" fill="none"><line x1="160" y1="22" x2="196" y2="22"/>'
          f'<line x1="160" y1="27" x2="196" y2="27"/><line x1="160" y1="32" x2="196" y2="32" stroke-dasharray="2 1.5"/></g>',
          txt(178, 50, "작업 j · 마감", anchor="middle", size=FT),
          path("M178,52 L178,68 L200,68 L200,86", sw=1.4),
          txt(276, 12, "리전 간 지연", anchor="middle", bold=True),
          box(252, 16, 48, 22),
          f'<g stroke="{INK}" stroke-width="0.7" fill="none"><path d="M262,33 L276,22 L290,33 Z"/></g>',
          txt(276, 50, "ℓ(o, r) · N × N", anchor="middle", size=FT),
          path("M276,52 L276,68 L242,68 L242,86", sw=1.4)]
    L += [box(8, 92, 56, 28),
          txt(36, 105, "gCO₂/kWh", anchor="middle", size=FT),
          f'<path d="M14,115 L26,107 L36,111 L48,105 L60,104" fill="none" stroke="{INK}" stroke-width="1"/>',
          txt(36, 134, "탄소집약도 이력", anchor="middle", bold=True),
          txt(36, 145, "N 리전 · 시간별", anchor="middle"),
          arr(64, 106, 90, 106, 1.4)]
    L += [f'<rect x="82" y="60" width="304" height="118" rx="7" fill="#fff" stroke="{INK}" stroke-width="1.5"/>',
          txt(89, 72, "CAST", bold=True, size=FB)]
    for x, t1, t2 in ((92, "LSTM 예측", "168 h → 24 h"), (204, "공간 이동", "ILP · 용량"), (316, "시간 이동", "마감 인지")):
        L += [box(x, 86, 66, 46),
              txt(x + 33, 106, t1, anchor="middle", bold=True),
              txt(x + 33, 120, t2, anchor="middle", size=FT)]
    L += [arr(158, 109, 202, 109), txt(180, 103, "Ĉ", anchor="middle", it=True),
          txt(180, 121, "N × 24 h", anchor="middle", size=FT),
          arr(270, 109, 314, 109), txt(292, 103, "리전 r(j)", anchor="middle"),
          path("M125,132 L125,168 L349,168 L349,134"),
          f'<rect x="216" y="162" width="26" height="11" fill="#fff"/>',
          txt(229, 171, "Ĉ", anchor="middle", it=True)]
    L += [path("M365,132 L365,196", sw=1.3),
          f'<rect x="368" y="146" width="62" height="24" fill="#fff"/>',
          txt(371, 156, "실행 결정", size=FT), txt(371, 167, "(리전, 시각)", size=FT),
          path("M398,210 L432,210 L432,76 L262,76 L262,84", dash="4 2.5"),
          f'<rect x="270" y="62" width="116" height="12" fill="#fff"/>',
          txt(384, 72, f"avail{sb('r')} · 슬롯별 잔여 용량", anchor="end", size=FT)]
    L += [txt(6, 192, f"리전 R{sb('1')} … R{sb('N')}", bold=True),
          txt(150, 192, f"동시 실행 수 ≤ avail{sb('r')}", it=True)]
    for x, lab in ((70, "1"), (154, "2"), (238, "3"), (334, "N")):
        L.append(box(x, 196, 64, 28, sw=0.9))
        for j in range(3):
            L.append(f'<rect x="{x+9}" y="{201+j*7}" width="46" height="4" fill="#fff" stroke="{INK}" stroke-width="0.5"/>')
        L.append(txt(x + 32, 236, f"R{sb(lab)}", anchor="middle"))
    L.append(txt(318, 214, "⋯", anchor="middle", bold=True))
    L.append("</svg>")
    return "\n".join(L)

# ═══════════ 그림 2 · 탄소 예측 (전단) ═══════════
def fig_forecast():
    W, H = 451, 142
    L = [head(W, H, "그림 2 탄소집약도 예측")]
    L += [f'<rect x="6" y="12" width="439" height="104" rx="7" fill="#fff" stroke="{INK}" stroke-width="1.5"/>',
          txt(14, 25, "탄소집약도 예측 · 리전마다 독립된 LSTM", bold=True, size=FB),
          box(18, 38, 104, 44), txt(70, 54, "입력 168 h", anchor="middle", bold=True),
          txt(70, 70, "10종 계통 · 시간 피처", anchor="middle", size=FT),
          arr(122, 60, 142, 60, 1.3),
          box(144, 38, 100, 44), txt(194, 54, "LSTM 2층", anchor="middle", bold=True),
          txt(194, 70, "h = 64 · dropout 0.2", anchor="middle", size=FT),
          arr(244, 60, 272, 60, 1.3), txt(258, 54, "hidden 64", anchor="middle", size=FT),
          box(274, 38, 92, 44), txt(320, 54, "Linear", anchor="middle", bold=True),
          txt(320, 70, "64 \u2192 24", anchor="middle", size=FT),
          arr(366, 60, 386, 60, 1.3),
          txt(392, 54, "\u0108" + sb("r") + "(t)", it=True, size=FB), txt(392, 70, "향후 24 h", size=FT),
          box(144, 90, 222, 20, sw=0.9, dash="3 2"),
          txt(255, 104, "기상 3 리전 : 미래 기상 24 \u00d7 3 을 별도 헤드로 결합", anchor="middle", size=FT),
          path("M194,82 L194,88", sw=0.9, dash="2.5 2"),
          path("M366,100 L378,100 L378,72", sw=0.9, dash="2.5 2"),
          txt(6, 134, "리전마다 독립된 모델 N개 · 출력은 gCO\u2082/kWh 단위의 예측 원값", size=FT)]
    L.append("</svg>")
    return "\n".join(L)

# ═══════════ 그림 3 · 로드밸런서 (전단) ═══════════
def fig_loadbalancer():
    W, H = 451, 192
    L = [head(W, H, "그림 3 공간 이동 · 로드밸런서")]
    def oplus(cx, cy, r=11):
        return (f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="#fff" stroke="{INK}" stroke-width="1.1"/>'
                f'<line x1="{cx-5}" y1="{cy}" x2="{cx+5}" y2="{cy}" stroke="{INK}" stroke-width="1.1"/>'
                f'<line x1="{cx}" y1="{cy-5}" x2="{cx}" y2="{cy+5}" stroke="{INK}" stroke-width="1.1"/>')
    L += [txt(8, 16, "공간 이동 · 슬롯 단위 ILP 로드밸런서", bold=True, size=FB),
          f'<rect x="6" y="26" width="439" height="140" rx="7" fill="#fff" stroke="{INK}" stroke-width="1" stroke-dasharray="5 3"/>',
          txt(438, 38, "점선 안이 한 슬롯(1 h) 처리 단위", anchor="end", size=FT, it=True),
          box(14, 44, 72, 18, sw=0.9), txt(50, 57, "LSTM 예측", anchor="middle", size=FT),
          arr(86, 53, 122, 53), txt(104, 48, "\u0108", anchor="middle", it=True),
          f'<g stroke="{INK}" stroke-width="0.9" fill="none"><rect x="30" y="72" width="40" height="28"/>'
          f'<line x1="43.3" y1="72" x2="43.3" y2="100"/><line x1="56.6" y1="72" x2="56.6" y2="100"/>'
          f'<line x1="30" y1="81.3" x2="70" y2="81.3"/><line x1="30" y1="90.6" x2="70" y2="90.6"/></g>',
          txt(50, 112, "지연 행렬 N \u00d7 N", anchor="middle", size=FT),
          arr(70, 86, 122, 86), txt(96, 81, "\u2113", anchor="middle", it=True),
          box(14, 122, 72, 18, sw=0.9), txt(50, 135, "직전 1 h 작업", anchor="middle", size=FT),
          arr(86, 131, 122, 131), txt(104, 126, "작업들", anchor="middle", size=FT),
          box(124, 44, 144, 88, sw=1.3), txt(196, 58, "로드밸런서", anchor="middle", bold=True),
          f'<line x1="124" y1="64" x2="268" y2="64" stroke="{INK}" stroke-width="0.5"/>',
          txt(132, 80, "\u2460 \u03b1 결정 — 슬롯마다 자동", size=FT),
          txt(132, 98, "\u2461 ILP 배정 — 용량 제약", size=FT),
          f'<rect x="132" y="110" width="128" height="16" rx="8" fill="#fff" stroke="{INK}" stroke-width="1.1"/>',
          txt(196, 122, "배정 x" + sb("jr"), anchor="middle", size=FT),
          arr(268, 78, 390, 78, 1.3), txt(329, 72, "배정 확정", anchor="middle", size=FT),
          f'<g stroke="{INK}" stroke-width="1.1" fill="none"><path d="M402,50 L394,50 L394,132 L402,132"/></g>',
          txt(406, 54, "R" + sb("1")), txt(406, 95, "\u22ee", bold=True), txt(406, 136, "R" + sb("N")),
          oplus(300, 150), txt(300, 164, "avail" + sb("r") + " 계산", anchor="middle", size=FT),
          txt(222, 153, "\u230a\u03b7 \u00b7 cap" + sb("r") + "\u230b", anchor="middle", size=FT),
          arr(252, 150, 287, 150, 0.9),
          path("M394,132 L394,150 L313,150", sw=0.9),
          txt(354, 145, "실행 중 작업 수", anchor="middle", size=FT),
          path("M300,139 L300,136 L196,136 L196,132", sw=1, dash="4 2.5"),
          txt(6, 186, "실행 시각은 이 단계에서 정하지 않는다 — 다음 단계인 시간 이동이 정한다.", size=FT)]
    L.append("</svg>")
    return "\n".join(L)

# ═══════════ 그림 4 · 스케줄러 (전단) ═══════════
def fig_scheduler():
    W, H = 451, 196
    L = [head(W, H, "그림 4 시간 이동 · 마감 인지 스케줄러")]
    L += [txt(8, 16, "시간 이동 · 마감 인지 스케줄러", bold=True, size=FB),
          box(14, 42, 76, 18, sw=0.9), txt(52, 55, "작업 j", anchor="middle", size=FT),
          arr(90, 51, 108, 51),
          f'<circle cx="52" cy="96" r="15" fill="#fff" stroke="{INK}" stroke-width="1.1"/>',
          txt(52, 100, "r(j)", anchor="middle", size=FT), txt(52, 124, "배정 리전", anchor="middle", size=FT),
          arr(67, 96, 108, 96),
          box(14, 136, 76, 18, sw=0.9), txt(52, 149, "LSTM 예측", anchor="middle", size=FT),
          arr(90, 145, 108, 145),
          box(110, 30, 190, 136, sw=1.3),
          txt(205, 44, "탐색 윈도우 안에서 점수 최소 슬롯", anchor="middle", size=FT, bold=True),
          txt(122, 104, "gCO\u2082/kWh", anchor="middle", size=FT),
          f'<g stroke="{INK}" stroke-width="1" fill="none"><path d="M130,54 L130,140"/>'
          f'<path d="M130,140 L292,140" marker-end="url(#a)"/></g>',
          txt(290, 152, "t (h)", anchor="end", size=FT),
          f'<path d="M134,62 C154,70 168,108 192,122 C214,134 240,118 264,82 C274,68 282,62 290,60" '
          f'fill="none" stroke="{INK}" stroke-width="1.5"/>',
          f'<rect x="180" y="116" width="34" height="18" fill="#fff" stroke="{INK}" stroke-width="1.8"/>',
          txt(197, 110, "선택", anchor="middle", size=FT),
          f'<line x1="272" y1="54" x2="272" y2="140" stroke="{INK}" stroke-width="1.1" stroke-dasharray="3 2"/>',
          txt(270, 52, "마감", anchor="end", size=FT),
          f'<g stroke="{INK}" stroke-width="0.8" fill="none"><path d="M134,152 L272,152"/>'
          f'<path d="M134,149 L134,155"/><path d="M272,149 L272,155"/></g>',
          txt(203, 164, "탐색 윈도우", anchor="middle", size=FT),
          arr(302, 98, 322, 98, 1.3),
          box(326, 84, 114, 30, sw=1.1), txt(383, 97, "실행 시각 T", anchor="middle", bold=True),
          txt(383, 109, "UTC 절대 시각", anchor="middle", size=FT),
          txt(326, 134, "작업별 결정", bold=True, size=FT),
          txt(326, 148, "(r" + sb("1") + ", T" + sb("1") + ")  (r" + sb("2") + ", T" + sb("2") + ")  \u22ef", size=FT),
          txt(326, 162, "용량 제약은 두지 않는다.", size=FT),
          txt(6, 188, "사후 용량 강제는 \u00a76.4 검증 단계에서만 수행한다. 온라인 구성요소가 아니다.", size=FT)]
    L.append("</svg>")
    return "\n".join(L)

for fn, name in ((fig_architecture, "fig1_architecture"), (fig_forecast, "fig2_forecast"),
                 (fig_loadbalancer, "fig3_loadbalancer"), (fig_scheduler, "fig4_scheduler")):
    open(name + ".svg", "w", encoding="utf-8").write(fn())
    print("wrote", name + ".svg")
