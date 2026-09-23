# -*- coding: utf-8 -*-
"""CAST_투고본.docx -> CAST_압축본.docx (짧은 판) 생성.

목적: 사용자가 "17쪽은 읽기 힘들다, 참고 논문들은 다 짧은데 우리만 주저리주저리
많은 것 같다"고 해서, Caspian(8쪽)급으로 줄인 판을 따로 만들어 비교해보려는 것.
원본 CAST.docx / CAST_투고본.docx 는 전혀 건드리지 않는다.

근거(실측): 국문초록 494자 ↔ 영문초록 177단어로 환산비를 재면 우리 본문
31,183자 ≈ 영어 11,173단어. CASPER 5,749 / Caspian 7,020 / CICS 11,878 /
CarbonFlex 13,404 단어이므로, 우리는 CICS·CarbonFlex급 "긴 논문" 체급이고
CASPER·Caspian보다 1.6~1.9배 많다. 즉 서식이 아니라 내용량 문제다.

잘라내는 기준: "이 논문의 기여가 아닌 것"부터. LSTM 예측(§5.3, §6.2)은
본 논문의 기여가 아니라 가져다 쓴 부품이고(사용자 동의), 배경·문제정의·
관련연구 상세는 Caspian처럼 압축 가능하며, 민감도 분석(§6.5)·논의(§6.6)는
부록성이다. 핵심 기여(§5.4 공간이동, §5.5~5.6 용량 인지 알고리즘,
§6.3 주요결과, §6.4 용량 분석)는 전부 남긴다.
"""
import re
import shutil
import zipfile
import xml.etree.ElementTree as ET

REPO = "/Users/jongha/Desktop/GitHub/carbon-aware-scheduler"
SRC = f"{REPO}/paper/CAST_투고본.docx"
DST = f"{REPO}/paper/CAST_압축본.docx"

PARA = re.compile(r'<w:p\b[^>]*?/>|<w:p\b[^>]*?(?<!/)>.*?</w:p>', re.DOTALL)
TBL = re.compile(r'<w:tbl>.*?</w:tbl>', re.DOTALL)

# (시작 제목, 끝나는 다음 제목) — 시작 포함, 끝 제외
CUTS = [
    ("2. 배경 지식", "3. 풀고자 하는 문제"),
    ("3. 풀고자 하는 문제", "4. 관련 연구와 그 한계"),
    ("4.1 시간 축 접근", "4.4 기존 연구의 한계"),
    ("5.3 탄소집약도 예측", "5.4 공간 이동"),
    ("6.2 예측 정확도", "6.3 주요 결과"),
    ("6.5 용량 스윕", "6.6 논의"),
    ("6.6 논의", "7. 결론"),
]


def blocks(xml):
    """문단과 표를 문서 순서대로, (종류, 시작, 끝, 평문)."""
    out = []
    for m in TBL.finditer(xml):
        out.append(("tbl", m.start(), m.end(), re.sub(r"<[^>]+>", "", m.group(0))))
    for m in PARA.finditer(xml):
        if any(s <= m.start() < e for _, s, e, _ in out if _ == "tbl"):
            continue
        out.append(("p", m.start(), m.end(), re.sub(r"<[^>]+>", "", m.group(0)).strip()))
    return sorted(out, key=lambda b: b[1])


def main():
    shutil.copy2(SRC, DST)
    z = zipfile.ZipFile(DST)
    xml = z.read("word/document.xml").decode("utf-8")
    before_chars = len(re.sub(r"<[^>]+>", "", xml))

    bs = blocks(xml)
    heads = {}
    for kind, s, e, t in bs:
        if kind != "p":
            continue
        for start, _ in CUTS:
            if t.startswith(start) and start not in heads:
                heads[start] = s
        for _, end in CUTS:
            if t.startswith(end) and end not in heads:
                heads[end] = s

    spans = []
    for start, end in CUTS:
        assert start in heads, f"시작 제목 못 찾음: {start}"
        assert end in heads, f"끝 제목 못 찾음: {end}"
        assert heads[start] < heads[end], f"순서 이상: {start} -> {end}"
        spans.append((heads[start], heads[end]))

    # 겹침 제거 후 뒤에서부터 잘라내기(인덱스 보존)
    spans.sort()
    merged = []
    for s, e in spans:
        if merged and s <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], e))
        else:
            merged.append((s, e))
    out = xml
    for s, e in reversed(merged):
        out = out[:s] + out[e:]

    ET.fromstring(out)
    after_chars = len(re.sub(r"<[^>]+>", "", out))
    print(f"잘라낸 구간 {len(merged)}개")

    tmp = DST + ".new"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as o:
        for it in z.infolist():
            d = out.encode("utf-8") if it.filename == "word/document.xml" else z.read(it.filename)
            o.writestr(it, d)
    z.close()
    shutil.move(tmp, DST)

    plain = [t for _, _, _, t in blocks(out) if t]
    prose = sum(len(t) for t in plain)
    print(f"프로즈 {prose:,}자 (원본 31,183자 대비 {(1-prose/31183)*100:.0f}% 감축)")
    print(f"남은 절: {[t for t in plain if re.match(r'^\\d+\\.\\d*\\s?\\S', t) and len(t) < 30]}")


if __name__ == "__main__":
    main()
