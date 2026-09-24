# -*- coding: utf-8 -*-
"""CAST_압축본.docx 를 10쪽 이내로 줄인다 (사용자 지시 2026-09-23).

사용자: "쪽은 늘어나도 되는데 전체적인 불필요한 내용은 줄여도 돼 /
내가 과거에 썼던 이야기를 지워도 돼 / 너무 진짜 10페이지 이내로 줄여"
→ 가독성 개선(Caspian 문단 복원·기호표·전단그림 위치)은 넣되, 그만큼
   이상을 군더더기에서 빼서 최종 10쪽 이내로 맞춘다.

삭제 기준(전부 "본문 다른 곳이 이미 말한 것"):
 - 논문 주장과 직접 연결되지 않는 배경 디테일(EU 규제 조문, IEA 시나리오 수치)
 - 같은 사실을 두 번 이상 말하는 문단
 - 뒤 문단이 곧바로 받아주는 예고성 문장
정보가 그 문단에만 있는 것은 절대 건드리지 않는다.
"""
import re
import shutil
import zipfile
import datetime
import xml.etree.ElementTree as ET

D = "/Users/jongha/Desktop/GitHub/carbon-aware-scheduler/paper/CAST_압축본.docx"
PARA = re.compile(r'<w:p\b[^>]*?/>|<w:p\b[^>]*?(?<!/)>.*?</w:p>', re.DOTALL)
TBL = re.compile(r'<w:tbl>.*?</w:tbl>', re.DOTALL)

# 문단 첫머리로 식별한다(원문 그대로여야 하며, 하나만 매칭돼야 한다)
DELETE = [
    # --- §1 서론 ---
    ("EU는 개정 에너지효율지침 제12조와",       "규제 조문 디테일 — 주장과 무관"),
    ("통상적인 대응은 설비 효율 개선과",         "IEA 시나리오 수치 — 다음 문단이 결론을 이미 말함"),
    ("저탄소 전원 조달 역시 완전한 해법은",      "같은 이유로 중복"),
    ("이 값은 지역에 따라, 그리고 같은 지역 안에서도", "바로 다음 문단이 우리 실측으로 더 구체적으로 말함"),
    ("즉 동일한 작업이라도 어느 리전에서 언제 실행하느냐에 따라 배출량이 달라진다. 선행 연구는",
                                             "같은 격차를 세 번째로 반복"),
    ("시스템 구현 연구는 대체로 두 축 중 하나에", "문헌 통계 — 뒤에서 실제 시스템을 직접 짚음"),
    ("본 논문은 리전별 용량이 유한하고 여유율 제약이", "앞 문단 끝문장과 같은 말, 다음 문단이 바로 받음"),
    # --- §6.4 ---
    ("공간 이동만 적용한 단계에서는 8개 리전 전부가", "로드밸런서가 상한을 지키는 이유 — §5.3에 이미 있음"),
    ("선행 연구는 시간 이동의 절감이 어떤 조건에",  "인용만 남은 연결 문장, 앞뒤가 이미 이어짐"),
    # --- §7 결론 ---
    ("이 63.03%는 두 경계값 사이에 있다",      "§6.3 표1·그림5가 같은 경계 설명을 이미 함"),
]


def paragraphs(xml):
    tbl = [(m.start(), m.end()) for m in TBL.finditer(xml)]
    out = []
    for m in PARA.finditer(xml):
        if any(s <= m.start() < e for s, e in tbl):
            continue
        out.append((m.start(), m.end(), m.group(0),
                    re.sub(r"<[^>]+>", "", m.group(0)).strip()))
    return out


def main():
    shutil.copy2(D, D.replace("CAST_압축본.docx",
                 f"versions/2026-09-23/CAST_압축본_{datetime.datetime.now():%Y%m%d-%H%M}_10쪽감축전.docx"))
    z = zipfile.ZipFile(D)
    xml = z.read("word/document.xml").decode("utf-8")
    d0 = xml.count("<w:drawing>")
    before = sum(len(t) for *_, t in paragraphs(xml) if t)

    removed = 0
    for head, why in DELETE:
        hits = [f for *_, f, t in [(0, 0, p[2], p[3]) for p in paragraphs(xml)] if t.startswith(head)]
        assert len(hits) == 1, f"{head[:28]!r} -> {len(hits)}개 매칭"
        frag = hits[0]
        # sectPr 을 품은 문단은 삭제하면 단 구성이 깨진다
        assert "<w:sectPr" not in frag, f"{head[:28]!r}: sectPr 포함 — 건너뜀"
        assert "<w:drawing" not in frag, f"{head[:28]!r}: 그림 포함 — 건너뜀"
        xml = xml.replace(frag, "", 1)
        removed += len(re.sub(r"<[^>]+>", "", frag).strip())
        print(f"  삭제 {len(re.sub(r'<[^>]+>','',frag).strip()):>4}자  {head[:30]}…  ({why})")

    ET.fromstring(xml)
    assert xml.count("<w:drawing>") == d0, "그림 손실"
    after = sum(len(t) for *_, t in paragraphs(xml) if t)
    print(f"\n프로즈 {before:,} → {after:,}자 ({removed:,}자 삭제, {removed/before*100:.1f}%)")

    tmp = D + ".n"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as o:
        for it in z.infolist():
            o.writestr(it, xml.encode("utf-8") if it.filename == "word/document.xml"
                       else z.read(it.filename))
    z.close()
    shutil.move(tmp, D)


if __name__ == "__main__":
    main()
