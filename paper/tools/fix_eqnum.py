# -*- coding: utf-8 -*-
"""식 (12) 결번 메우기 — 13~16 을 12~15 로 당긴다.

두 번 실패하고 세 번째에 된 작업이라 그 내력을 남긴다.
 1차: 큰 번호부터(16→15, 15→14, …) 처리 → 방금 만든 번호를 다음 회차가 다시
      집어 연쇄로 무너져 모든 식이 (12)가 됐다. **번호를 낮출 때는 작은 것부터.**
 2차: python-docx 로 문단 글을 통째로 다시 썼더니 수식 문단의 OMML 구조가
      깨졌다. 수식은 <w:r> 이 아니라 <m:oMath> 에 들어 있어 run 을 갈아끼우면
      식 자체가 사라진다.
 3차(이 판): 원시 XML 에서 **번호표 문자열이 들어 있는 <w:t> 하나만** 바꾼다.
      구조를 건드리지 않으므로 수식도 서식도 그대로 남는다.
"""
import re
import shutil
import zipfile
import xml.etree.ElementTree as ET

DOCS = ["/Users/jongha/Desktop/GitHub/carbon-aware-scheduler/paper/CAST_압축본.docx",
        "/Users/jongha/Desktop/GitHub/carbon-aware-scheduler/paper/CAST_인용포함.docx"]
SHIFT = [(13, 12), (14, 13), (15, 14), (16, 15)]      # 낮추는 작업 → 작은 번호부터
PARA = re.compile(r'<w:p\b[^>]*?/>|<w:p\b[^>]*?(?<!/)>.*?</w:p>', re.DOTALL)


def main():
    for doc in DOCS:
        shutil.copy2(doc, doc.replace("paper/CAST", "paper/versions/2026-09-24/식번호3차전_CAST"))
        z = zipfile.ZipFile(doc)
        xml = z.read("word/document.xml").decode("utf-8")
        n0 = len(PARA.findall(xml))
        d0 = xml.count("<w:drawing>")
        m0 = xml.count("<m:oMath")
        tag = ref = 0

        for old, new in SHIFT:
            # 1) 식 끝 번호표 — 문단 마지막 <w:t> 안의 "(N)" 만
            out, pos = [], 0
            for m in PARA.finditer(xml):
                frag = m.group(0)
                if not re.search(rf"\({old}\)\s*<", frag) and not frag.rstrip().endswith(
                        f"({old})</w:t></w:r></w:p>"):
                    # 평문 기준으로 문단이 (N) 으로 끝나는지 본다
                    if not re.sub(r"<[^>]+>", "", frag).rstrip().endswith(f"({old})"):
                        continue
                fixed = re.sub(rf"\({old}\)(?=\s*</w:t>)", f"({new})", frag, count=1)
                if fixed != frag:
                    out.append(xml[pos:m.start()]); out.append(fixed)
                    pos = m.end(); tag += 1
            out.append(xml[pos:]); xml = "".join(out)

            # 2) 본문 참조 "식 (N)" — 한 <w:t> 안에 통째로 들어 있는 경우만 안전하게
            xml, k = re.subn(rf"식\s*\({old}\)", f"식 ({new})", xml)
            ref += k

        ET.fromstring(xml)
        assert len(PARA.findall(xml)) == n0, "문단 수 변함"
        assert xml.count("<w:drawing>") == d0, "그림 손실"
        assert xml.count("<m:oMath") == m0, "수식 손실"

        tmp = doc + ".n"
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as o:
            for it in z.infolist():
                o.writestr(it, xml.encode() if it.filename == "word/document.xml"
                           else z.read(it.filename))
        z.close()
        shutil.move(tmp, doc)
        import docx
        docx.Document(doc)

        ps = [re.sub(r"<[^>]+>", "", p).strip() for p in PARA.findall(xml)]
        ns = sorted({int(x.group(1)) for p in ps
                     for x in re.finditer(r"\((\d{1,2})\)\s*$", p)})
        gap = [k for k in range(1, max(ns) + 1) if k not in ns]
        rf = sorted({int(x.group(1)) for p in ps
                     for x in re.finditer(r"식\s*\((\d{1,2})\)", p)})
        print(f"{doc.split('/')[-1]}: 번호표 {tag} · 참조 {ref}")
        print(f"   식 {ns}  결번 {gap or '없음'}")
        print(f"   참조 {rf}  없는 식 참조 {[r for r in rf if r not in ns] or '없음'}"
              f"  수식 {m0}개 보존")


if __name__ == "__main__":
    main()
