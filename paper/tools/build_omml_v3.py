# -*- coding: utf-8 -*-
"""v3 수식 (1)~(11) LaTeX → OMML. 변환은 build_omml_v2.to_omml 을 그대로 쓴다.
번호는 paper/v3/원고/03_CAST.txt 기준. v2 번호와의 대응: 1←1, 2←4, 3←6, 4·5←8, 6←11a+11b, 7←12, 8←7, 9←9, 10←10, 11←13.
산출: paper/v3/원고/omml/eq{n}.xml + eq{n}.tex
    ./.venv/bin/python paper/tools/build_omml_v3.py
"""
import os

from build_omml_v2 import EQ as EQ_V2, to_omml

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, "..", "v3", "원고", "omml"))

EQ = {
 1: EQ_V2[1],                                   # 배출
 2: EQ_V2[4],                                   # 마감
 3: EQ_V2[6],                                   # 용량과 초과
 4: r"\tilde{\ell}(o,r)=\frac{\ell(o,r)}{244}",   # 지연 비용(v2 식 8 뒷부분)
 5: r"\tilde{C}_{j}(r,i)=\frac{\hat{C}_{r}^{(t)}(t+i,\,d_{j})}{\max_{r',t'}\hat{C}_{r'}^{(t)}(t')}",   # 탄소 비용(v2 식 8 앞부분)
 # v2 (11a)(11b)를 하나로: κ 는 이번 슬롯의 시작 순간(U_t)과 미래 슬롯을 함께 가리킨다
 6: r"\sum_{(j,i)\ni\kappa}x_{jri}+n_{r}(\kappa)\le\mathrm{cap}_{r}+z^{A}_{r\kappa} @@ \qquad\qquad\forall r,\ \kappa\in U_{t}\cup[t+1,t+H]",
 7: r"\sum_{(j,i)\ni\sigma,\ j\in Q^{\mathrm{def}}}x_{jri}+n_{r}(\sigma) @@ \qquad\le\mathrm{cap}_{r}-\rho_{r}+z^{B}_{r\sigma}",   # 예약(11-03: 정의역은 본문으로 빼서 두 줄)
 8: EQ_V2[7],                                   # 후보 비용
 9: EQ_V2[9],                                   # 슬롯 목적식
 10: EQ_V2[10],                                 # 한 자리
 11: EQ_V2[13],                                 # 무릎점
}

def main():
    os.makedirs(OUT, exist_ok=True)
    for n, tex in EQ.items():
        xml, om, ns = to_omml(tex)
        open(os.path.join(OUT, f"eq{n}.xml"), "w", encoding="utf-8").write(xml)
        open(os.path.join(OUT, f"eq{n}.tex"), "w", encoding="utf-8").write(tex + "\n")
        txt = "".join(om.xpath(".//m:t/text()", namespaces=ns))
        print(f"({n}) {txt[:90]}")
    print("wrote", OUT)

if __name__ == "__main__":
    main()
