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
 6: r"n_{r}(t)\le\mathrm{cap}_{r}+z_{r}(t),\quad z_{r}(t)\ge 0\qquad\forall r\in R,\ \forall t",
 7: r"c_{j}(r,i)=d_{j}\left[\alpha\,\tilde{C}_{j}(r,i)+(1-\alpha)\,\tilde{\ell}(o_{j},r)\right]",
 8: r"\tilde{C}_{j}(r,i)=\frac{\hat{C}_{r}^{(t)}(t+i,\,d_{j})}{\max_{r',t'}\hat{C}_{r'}^{(t)}(t')},\qquad\tilde{\ell}(o,r)=\frac{\ell(o,r)}{244}",
 9: r"\min\ \sum_{j\in Q}\sum_{r,i}c_{j}(r,i)\,x_{jri}+M_{A}\sum_{r,\tau}z^{A}_{r\tau} @@ \qquad+M_{B}\sum_{r,\tau\ge t+1}z^{B}_{r\tau}+\varepsilon\sum_{j\in Q}\sum_{r,i}i\,x_{jri}",
 10: r"\sum_{r,i}x_{jri}=1\qquad\forall j\in Q",
 11: r"\sum_{(j,i)\ni\tau}x_{jri}+n_{r}(\tau)\le\mathrm{cap}_{r}+z^{A}_{r\tau}",        # ∀ r, τ∈[t,t+H] 는 해설 문장에(단 폭)
 12: r"\sum_{(j,i)\ni\tau,\ j\in Q^{\mathrm{def}}}x_{jri}+n_{r}(\tau)\le\mathrm{cap}_{r}-\rho_{r}+z^{B}_{r\tau}",   # ∀ r, τ∈[t+1,t+H] 는 해설 문장에
 13: r"\alpha^{*}=\underset{\alpha\in A}{\mathrm{arg\,min}}\sqrt{\tilde{\lambda}_{\alpha}^{2}+\tilde{e}_{\alpha}^{2}}",
 14: r"E_{j}\approx P\,d_{j}\,\frac{1}{|T_{j}|}\sum_{\tau\in T_{j}}C_{r(j)}(\tau)",
}

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

def _one(tex):
    mml = l2m.convert(tex)
    doc = etree.fromstring(mml.encode("utf-8"))
    res = etree.XSLT(etree.parse(XSL))(doc)
    root = res.getroot()
    ns = {"m": "http://schemas.openxmlformats.org/officeDocument/2006/math"}
    return (root if root.tag.endswith("}oMath") else root.find(".//m:oMath", ns)), ns

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
        print(f"({n:2d}) {txt[:90]:90s} | " + " ".join(f"{k}{v}" for k, v in cnt.items() if v))
    print("wrote", OUT)

if __name__ == "__main__":
    main()
