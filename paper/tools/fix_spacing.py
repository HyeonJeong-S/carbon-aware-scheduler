# -*- coding: utf-8 -*-
"""한글–영문/숫자 자동 간격 끄기 + 제목 색 검정 (세 문서 공통).

Word 는 한글과 라틴문자·숫자가 붙으면 사이에 빈칸을 자동으로 벌린다
(autoSpaceDE / autoSpaceDN). 그래서 "CAST를" 이 "CAST 를", "146,000건" 이
"146,000 건" 처럼 보인다. 국문 논문에서는 이 벌어짐이 오히려 어색하고
양쪽 맞춤과 겹치면 줄이 들쭉날쭉해진다. 문서 기본값에서 끈다.

끄면 줄당 글자가 늘어 쪽수가 약간 줄어드는 부수 효과도 있다.
"""
import re
import shutil
import zipfile
import xml.etree.ElementTree as ET

DOCS = ["CAST_압축본.docx", "CAST_인용포함.docx", "CAST_추가자료.docx"]
BASE = "/Users/jongha/Desktop/GitHub/carbon-aware-scheduler/paper/"


def patch_settings(xml):
    """settings.xml 에 문서 전역 스위치를 넣는다."""
    for tag in ("autoSpaceDE", "autoSpaceDN"):
        xml = re.sub(rf'<w:{tag}[^/>]*/>', "", xml)
    add = '<w:doNotExpandShiftReturn/>'
    if "doNotExpandShiftReturn" not in xml:
        xml = xml.replace("</w:settings>", add + "</w:settings>")
    return xml


def patch_styles(xml):
    """docDefaults 의 문단 기본값에서 자동 간격을 끄고, 제목 색을 검정으로."""
    off = '<w:autoSpaceDE w:val="0"/><w:autoSpaceDN w:val="0"/>'
    m = re.search(r'(<w:pPrDefault>\s*<w:pPr>)', xml)
    if m and 'w:autoSpaceDE w:val="0"' not in xml:
        xml = xml[:m.end()] + off + xml[m.end():]
    elif not m and 'w:autoSpaceDE w:val="0"' not in xml:
        xml = xml.replace("<w:docDefaults>",
                          f"<w:docDefaults><w:pPrDefault><w:pPr>{off}</w:pPr></w:pPrDefault>", 1)
    # 제목 스타일의 파란 글자색 -> 검정
    def black(m2):
        s = m2.group(0)
        if re.search(r'w:styleId="Heading', s):
            s = re.sub(r'<w:color[^/>]*/>', '<w:color w:val="000000"/>', s)
        return s
    xml = re.sub(r'<w:style\b.*?</w:style>', black, xml, flags=re.DOTALL)
    return xml


def para_off(xml):
    """본문 문단에도 개별로 끈다 — docDefaults 를 무시하는 스타일이 있을 수 있다."""
    off = '<w:autoSpaceDE w:val="0"/><w:autoSpaceDN w:val="0"/>'
    n = 0
    out, pos = [], 0
    for m in re.finditer(r'<w:p\b[^>]*?(?<!/)>', xml):
        end = m.end()
        nxt = xml[end:end + 400]
        if nxt.lstrip().startswith("<w:pPr"):
            i = end + nxt.index("<w:pPr") + len(re.match(r'<w:pPr\b[^>]*?>', nxt[nxt.index("<w:pPr"):]).group(0))
            ins = i
        else:
            ins = end
            off2 = f"<w:pPr>{off}</w:pPr>"
            out.append(xml[pos:ins]); out.append(off2); pos = ins; n += 1
            continue
        if "autoSpaceDE" in xml[ins:ins + 200]:
            continue
        out.append(xml[pos:ins]); out.append(off); pos = ins; n += 1
    out.append(xml[pos:])
    return "".join(out), n


def main():
    for name in DOCS:
        p = BASE + name
        shutil.copy2(p, BASE + f"versions/2026-09-24/{name[:-5]}_간격수정전.docx")
        z = zipfile.ZipFile(p)
        parts = {i.filename: z.read(i.filename) for i in z.infolist()}
        infos = z.infolist()

        doc = parts["word/document.xml"].decode()
        d0 = doc.count("<w:p ") + doc.count("<w:p>")
        doc, n = para_off(doc)
        ET.fromstring(doc)
        assert doc.count("<w:p ") + doc.count("<w:p>") == d0, "문단 수 변함"
        parts["word/document.xml"] = doc.encode()

        if "word/styles.xml" in parts:
            parts["word/styles.xml"] = patch_styles(parts["word/styles.xml"].decode()).encode()
        if "word/settings.xml" in parts:
            parts["word/settings.xml"] = patch_settings(parts["word/settings.xml"].decode()).encode()

        z.close()
        tmp = p + ".new"
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as o:
            for it in infos:
                o.writestr(it, parts[it.filename])
        shutil.move(tmp, p)
        import docx
        docx.Document(p)
        print(f"  {name}: 문단 {n:,}개에 자동간격 해제")


if __name__ == "__main__":
    main()
