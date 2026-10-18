# -*- coding: utf-8 -*-
"""v2 수식 (1)~(14) LaTeX → OMML. 번호·꼴은 paper/문서/v2_draft/30_CAST.txt(92 초안) 기준.
파이프라인(v1 A11 과 같음): latex2mathml → Word.app mathml2omml.xsl(lxml XSLT) → <m:oMath>.
산출: paper/문서/v2_draft/omml/eq{n}.xml (docx 삽입용 조각) + 같은 폴더 eq{n}.tex (원자재).
검사: <m:t> 뿐 아니라 <m:d>(괄호)·<m:f>(분수)·<m:rad>(근호)·<m:nary>(Σ∫) 요소 수를 같이 센다(A11 교훈).
    ./.venv/bin/python paper/tools/build_omml_v2.py
"""
import os, re
import latex2mathml.converter as l2m
from lxml import etree

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, "..", "문서", "v2_draft", "omml"))
XSL = "/Applications/Microsoft Word.app/Contents/Resources/mathml2omml.xsl"

EQ = {
 1: r"E=\sum_{j\in J}P\int_{\tau_{j}}^{\tau_{j}+d_{j}}C_{r(j)}(t)\,dt",
 2: r"\Lambda=\sum_{j\in J}d_{j}\,\ell(o_{j},r(j))",
 3: r"Z=\sum_{r\in R}\int\max\{0,\,n_{r}(t)-\mathrm{cap}_{r}\}\,dt",
 4: r"s_{j}\le\tau_{j},\quad\tau_{j}+d_{j}\le D_{j}\qquad\forall j\in J",
 5: r"\ell(o_{j},r(j))\le L_{j}\qquad\forall j\in J",
 6: r"n_{r}(t)\le\mathrm{cap}_{r}+z_{r}(t),\ z_{r}(t)\ge 0\quad\forall r\in R,\ \forall t",        # 간격을 넓히면 단폭을 넘어 번호 (6)이 다음 줄로 떨어진다
 7: r"c_{j}(r,i)=d_{j}\left[\alpha\,\tilde{C}_{j}(r,i)+(1-\alpha)\,\tilde{\ell}(o_{j},r)\right]",
 8: r"\tilde{C}_{j}(r,i)=\frac{\hat{C}_{r}^{(t)}(t+i,\,d_{j})}{\max_{r',t'}\hat{C}_{r'}^{(t)}(t')},\qquad\tilde{\ell}(o,r)=\frac{\ell(o,r)}{244}",
 # 식 9: 합의 몸을 {}로 묶는다 — 안 묶으면 XSL 이 c_j 만 Σ 의 몸(m:e)에 넣고 "(r,i)" 를 Σ 밖에 두어 c_j 와 괄호 사이가 벌어졌다(84 [10])
 9: r"\min\ \sum_{j\in Q}\sum_{r,i}{c_{j}(r,i)\,x_{jri}}+M_{A}\sum_{r,\kappa}z^{A}_{r\kappa} @@ \qquad+M_{B}\sum_{r,\sigma\ge t+1}z^{B}_{r\sigma}+\varepsilon\sum_{j\in Q}\sum_{r,i}i\,x_{jri}",   # 3회차 B[10]: κ 는 순간 u∈U_t 와 미래 슬롯 σ 를 함께(해설 문장). 세 줄로 나누면 Word 가 가운데 줄 Σ 를 크게 그렸다
 10: r"\sum_{r,i}x_{jri}=1,\qquad\forall j\in Q",                                      # "= 1, ∀j"(89 [24]: 붙어 있던 것)
 "11a": r"\sum_{(j,0)\ni u}x_{jr0}+n_{r}(u)\le\mathrm{cap}_{r}+z^{A}_{ru}",   # 3회차 B[10]: 지금 슬롯의 시작 순간 행. (j,0)∋u = 지금 시작하는 j 의 실행 [max(t,s_j), +d_j) 가 u 를 포함(해설 문장에)
 "11b": r"\sum_{(j,i)\ni\sigma}x_{jri}+n_{r}(\sigma)\le\mathrm{cap}_{r}+z^{A}_{r\sigma}",        # 미래 슬롯 σ∈[t+1,t+H] 는 해설 문장에
 12: r"\sum_{(j,i)\ni\sigma,\ j\in Q^{\mathrm{def}}}x_{jri}+n_{r}(\sigma) @@ \qquad\le\mathrm{cap}_{r}-\rho_{r}+z^{B}_{r\sigma}",   # ∀ r, σ∈[t+1,t+H] 는 해설 문장에. 한 줄이면 번호 (12)가 식에 붙는다(89 [7]) — 두 줄
 13: r"\alpha^{*}=\underset{\alpha\in\mathcal{A}}{\mathrm{arg\,min}}\sqrt{\tilde{\lambda}_{\alpha}^{2}+\tilde{e}_{\alpha}^{2}}",
 14: r"E_{j}\approx P\,d_{j}\,\frac{1}{|T_{j}|}\sum_{\tau\in T_{j}}C_{r(j)}(\tau)",
}

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

M_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"
# \quad·\qquad 는 MathML <mspace> 가 되어 Word XSL 에서 사라진다(식 (4)(10) "1∀j" 붙음, 89 [24]).
# 자리표시 글자로 바꿔 변환한 뒤 m:t 안에서 전각 공백(U+2003)으로 되돌린다.
SPACES = [(r"\qquad", "QQSPACE", "  "), (r"\quad", "QSPACE", " ")]
FUNCS = {"min", "max", "argmin", "arg min", "arg min", "log", "exp"}   # 함수 이름은 바른 글꼴(89 [24]: min 이 이탤릭)

def _one(tex):
    for tx, ph, _ in SPACES: tex = tex.replace(tx, r"\mathrm{%s}" % ph)
    mml = l2m.convert(tex)
    doc = etree.fromstring(mml.encode("utf-8"))
    res = etree.XSLT(etree.parse(XSL))(doc)
    root = res.getroot()
    ns = {"m": M_NS}
    om = root if root.tag.endswith("}oMath") else root.find(".//m:oMath", ns)
    for t in om.iter("{%s}t" % M_NS):
        for _, ph, sp in SPACES:
            if t.text and ph in t.text: t.text = t.text.replace(ph, sp)
    for r in list(om.iter("{%s}r" % M_NS)):                 # "∫max{0," 처럼 한 run 에 섞인 함수 이름은 떼어 낸다
        t = r.find("{%s}t" % M_NS)
        if t is None or not t.text or r.find("{%s}rPr" % M_NS) is not None: continue
        parts = [x for x in re.split(r"(?<![A-Za-z])(min|max)(?![A-Za-z])", t.text) if x]
        if len(parts) < 2: continue
        t.text = parts[0]; at = r
        for x in parts[1:]:
            nr = etree.Element("{%s}r" % M_NS); etree.SubElement(nr, "{%s}t" % M_NS).text = x
            at.addnext(nr); at = nr
    for r in om.iter("{%s}r" % M_NS):                       # min·max 바른 글꼴
        t = r.find("{%s}t" % M_NS)
        if t is not None and (t.text or "").strip() in FUNCS:
            rp = r.find("{%s}rPr" % M_NS)
            if rp is None: rp = etree.Element("{%s}rPr" % M_NS); r.insert(0, rp)
            for e in rp.findall("{%s}sty" % M_NS): rp.remove(e)
            etree.SubElement(rp, "{%s}sty" % M_NS).set("{%s}val" % M_NS, "p")
    for lu in list(om.iter("{%s}limUpp" % M_NS)):           # \tilde → latex2mathml 이 <mover>~ 로 내고 XSL 이 limUpp(위 한계)로
        lim = lu.find("{%s}lim" % M_NS)                     # 만든다 — 물결이 글자 왼쪽 위로 비껴 찍혔다(식 7·8·13). 악센트(m:acc)로 바꾼다
        if lim is None or "".join(lim.itertext()).strip() not in ("~", "˜"): continue
        acc = etree.Element("{%s}acc" % M_NS); apr = etree.SubElement(acc, "{%s}accPr" % M_NS)
        etree.SubElement(apr, "{%s}chr" % M_NS).set("{%s}val" % M_NS, "̃")
        acc.append(lu.find("{%s}e" % M_NS)); lu.getparent().replace(lu, acc)
    for npr in om.iter("{%s}naryPr" % M_NS):                # 10-18: 줄을 나눈 식 (9) 둘째 줄의 Σ 만 한계가 아래로 내려갔다 — 모든 Σ 를 옆 첨자(subSup)로 통일
        for e in npr.findall("{%s}limLoc" % M_NS): npr.remove(e)
        etree.SubElement(npr, "{%s}limLoc" % M_NS).set("{%s}val" % M_NS, "subSup")
    for g in om.iter("{%s}grow" % M_NS):                   # Σ 가 안의 Σ 를 감싸며 커지지 않게(식 (9) 첫 Σ 만 큼)
        g.set("{%s}val" % M_NS, "0")
    return om, ns

def to_omml(tex):
    """"@@" 에서 줄을 바꾼다(단 폭 195.6pt 를 넘는 식용, 10-17): 조각을 따로 변환해 한 oMath 로 잇고 사이에 수동 줄바꿈을 넣는다."""
    parts = [t.strip() for t in tex.split("@@")]
    om, ns = _one(parts[0])
    for extra in parts[1:]:
        br = etree.SubElement(om, "{%s}r" % ns["m"]); etree.SubElement(br, "{%s}br" % W_NS)
        om2, _ = _one(extra)
        for child in list(om2): om.append(child)
    return etree.tostring(om, encoding="unicode"), om, ns

def main():
    os.makedirs(OUT, exist_ok=True)
    for n, tex in EQ.items():
        xml, om, ns = to_omml(tex)
        open(os.path.join(OUT, f"eq{n}.xml"), "w", encoding="utf-8").write(xml)
        open(os.path.join(OUT, f"eq{n}.tex"), "w", encoding="utf-8").write(tex + "\n")
        txt = "".join(om.xpath(".//m:t/text()", namespaces=ns))
        cnt = {k: len(om.xpath(f".//m:{k}", namespaces=ns)) for k in ("d", "f", "rad", "nary", "sSub", "sSup", "sSubSup", "acc", "bar")}
        print(f"({str(n):>3s}) {txt[:90]:90s} | " + " ".join(f"{k}{v}" for k, v in cnt.items() if v))
    print("wrote", OUT)

if __name__ == "__main__":
    main()
