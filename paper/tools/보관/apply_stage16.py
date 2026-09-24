"""
apply_stage16.py — 그림7(다섯 방식 비교) §6.3 표2 직후 삽입.
작성: 2026-09-22, carbon-aware-scheduler-4d(원고 트랙). 실행은 be가 한다.

삽입 위치: 표2 ④행 마지막 셀 바로 뒤 빈 문단(paraId 7B6AD9DC, self-
closing) 다음. 그 빈 문단은 표-그림7 사이 구분자로 그대로 두고, 뒤에
[드로잉+캡션+참조문+새 빈문단]을 추가한다. 캡션·참조문은 0c 초안
그대로(길이·서식만 확인). 크기 215×330pt = 2,730,500×4,191,000 EMU
(fig7_comparison.png 실제 픽셀 895×1375와 세로/가로 비율 일치 확인함).
"""
import sys, os, shutil, zipfile, datetime, argparse, re, hashlib
import xml.etree.ElementTree as ET

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOCX = os.path.join(REPO, "paper", "CAST.docx")
VERSIONS_DIR = os.path.join(REPO, "paper", "versions")

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

ANCHOR_OLD = '<w:p w14:paraId="7B6AD9DC" w14:textId="77777777" w:rsidR="004A6DA0" w:rsidRDefault="004A6DA0"/>'
NEW_BLOCK = '<w:p w14:paraId="7B6AD9DC" w14:textId="77777777" w:rsidR="004A6DA0" w:rsidRDefault="004A6DA0"/><w:p w14:paraId="FF000002" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="both"/></w:pPr><w:r><w:rPr><w:noProof/></w:rPr><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0" wp14:anchorId="0000A005" wp14:editId="0000A006"><wp:extent cx="2730500" cy="4191000"/><wp:effectExtent l="0" t="0" r="0" b="0"/><wp:docPr id="964" name="Picture 964"/><wp:cNvGraphicFramePr><a:graphicFrameLocks xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" noChangeAspect="1"/></wp:cNvGraphicFramePr><a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:nvPicPr><pic:cNvPr id="964" name="fig7_comparison.png"/><pic:cNvPicPr/></pic:nvPicPr><pic:blipFill><a:blip r:embed="rId59"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill><pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="2730500" cy="4191000"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p><w:p w14:paraId="FF000003" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/><w:rPr><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr></w:pPr><w:r><w:rPr><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:t xml:space="preserve">그림 7. 다섯 방식의 총 배출량 비교 — 온라인 용량 인지(④, 10,805.0 kg, −63.03%)는 아무것도 안 했을 때(①, 29,225.6 kg)와 실현 불가능한 반사실 상한(③, 9,958.2 kg) 사이에 위치한다.</w:t></w:r></w:p><w:p w14:paraId="FF000004" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="both"/></w:pPr><w:r><w:t xml:space="preserve">그림 7은 표 2의 다섯 방식을 한 축 위에 나란히 놓아, ④가 두 경계(①의 손해, ③의 이상치) 사이 어디에 실제로 도달하는지를 보여준다.</w:t></w:r></w:p><w:p w14:paraId="FF000005" w14:textId="77777777" w:rsidR="004A6DA0" w:rsidRDefault="004A6DA0"/>'
MEDIA_ADD = {'docx_path': 'word/media/image10.png', 'source': '/Users/jongha/Desktop/GitHub/carbon-aware-scheduler/paper/diagram/fig7_comparison.png', 'md5': '32679580733ce3a33cf56e3c04e56f0c', 'size': 144378}
RELS_ADD = '<Relationship Id="rId59" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/image10.png"/>'

EXPECTED_INSERTED = {'FF000002', 'FF000003', 'FF000004', 'FF000005'}
EXPECTED_DELETED = set()
EXPECTED_MODIFIED = set()
EXPECTED_PARA_DELTA = 4

def read_docx_xml(path):
    with zipfile.ZipFile(path) as z:
        return z.read("word/document.xml").decode("utf-8")


def read_docx_rels(path):
    with zipfile.ZipFile(path) as z:
        return z.read("word/_rels/document.xml.rels").decode("utf-8")


def root_open_tag(xml_str):
    start = xml_str.index("<w:document")
    end = xml_str.index(">", start) + 1
    return xml_str[start:end]


PARA_RE = re.compile(
    r'<w:p w14:paraId="([0-9A-Za-z]{8})"[^>]*?(?:/>|(?<!/)>(.*?)</w:p>)', re.DOTALL)


def para_map(xml_str):
    out = {}
    for m in PARA_RE.finditer(xml_str):
        pid, body = m.group(1), m.group(2)
        out[pid] = body or ""
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                     help="검증만 하고 실제 파일은 하나도 안 바꾼다")
    args = ap.parse_args()

    if not os.path.isfile(DOCX):
        print(f"FATAL: not found: {DOCX}")
        sys.exit(1)
    if not os.path.isfile(MEDIA_ADD["source"]):
        print(f"FATAL: 새 이미지 파일 없음: {MEDIA_ADD['source']}")
        sys.exit(1)

    print(f"대상: {DOCX}")
    orig_xml = read_docx_xml(DOCX)
    orig_rels = read_docx_rels(DOCX)
    orig_root_open = root_open_tag(orig_xml)

    # ---- 1) 앵커 검증 ----
    problems = []
    c = orig_xml.count(ANCHOR_OLD)
    if c != 1:
        problems.append(f"ANCHOR_OLD(7B6AD9DC): count != 1 (got {c})")
    with zipfile.ZipFile(DOCX) as z:
        names = z.namelist()
        if MEDIA_ADD["docx_path"] in names:
            problems.append(f"{MEDIA_ADD['docx_path']}: 이미 존재함(중복 삽입 위험)")
        if "rId59" in orig_rels:
            problems.append("rId59: 이미 rels에 존재함(중복 발급 위험)")
        actual_md5 = hashlib.md5(open(MEDIA_ADD["source"], "rb").read()).hexdigest()
        if actual_md5 != MEDIA_ADD["md5"]:
            problems.append(f"새 이미지 md5 불일치: {actual_md5} != {MEDIA_ADD['md5']}")
    for pid in ("FF000002", "FF000003", "FF000004", "FF000005"):
        if f'w14:paraId="{pid}"' in orig_xml:
            problems.append(f"paraId {pid}: 이미 문서에 존재함(충돌)")
    if problems:
        print("FATAL: 앵커 검증 실패, 아무 것도 안 씀:")
        for p in problems:
            print("  -", p)
        sys.exit(2)
    print("앵커 검증 통과: 삽입 지점 1건, media/rels/paraId 충돌 없음")

    # ---- 2) 적용 ----
    new_xml = orig_xml.replace(ANCHOR_OLD, NEW_BLOCK, 1)
    assert new_xml.count(NEW_BLOCK) == 1

    # rels: </Relationships> 바로 앞에 새 Relationship 삽입
    assert orig_rels.count("</Relationships>") == 1
    new_rels = orig_rels.replace("</Relationships>", RELS_ADD + "</Relationships>", 1)

    # ---- 3) 전수 문단 diff 감사 ----
    old_map = para_map(orig_xml)
    new_map = para_map(new_xml)
    deleted_ids = set(old_map) - set(new_map)
    inserted_ids = set(new_map) - set(old_map)
    modified_ids = {pid for pid in (set(old_map) & set(new_map)) if old_map[pid] != new_map[pid]}

    diff_problems = []
    if deleted_ids != EXPECTED_DELETED:
        diff_problems.append(f"삭제된 paraId 불일치: 실제={deleted_ids} 기대={EXPECTED_DELETED}")
    if inserted_ids != EXPECTED_INSERTED:
        diff_problems.append(f"삽입된 paraId 불일치: 실제={inserted_ids} 기대={EXPECTED_INSERTED}")
    if modified_ids != EXPECTED_MODIFIED:
        diff_problems.append(f"수정된 paraId 불일치: 실제={modified_ids} 기대={EXPECTED_MODIFIED}")

    print()
    print("전수 문단 diff 감사:")
    print(f"  삭제 {len(deleted_ids)}건 / 삽입 {len(inserted_ids)}건 / 수정 {len(modified_ids)}건")
    if diff_problems:
        print("FATAL: 의도하지 않은 변경이 섞여 있음 — 아무 것도 안 씀:")
        for p in diff_problems:
            print("  -", p)
        sys.exit(3)
    print(f"  [OK] 삽입 4건(FF000002~5)만, 삭제/수정 0건")

    # ---- 4) 결과 검증 ----
    checks = []
    try:
        new_root = ET.fromstring(new_xml)
        checks.append(("well-formed XML(document.xml)", True, ""))
    except Exception as e:
        checks.append(("well-formed XML(document.xml)", False, str(e)))
        new_root = None

    try:
        ET.fromstring(new_rels)
        checks.append(("well-formed XML(rels)", True, ""))
    except Exception as e:
        checks.append(("well-formed XML(rels)", False, str(e)))

    new_root_open = root_open_tag(new_xml)
    checks.append(("루트 <w:document> 태그 불변", new_root_open == orig_root_open, ""))

    if new_root is not None:
        old_root = ET.fromstring(orig_xml)
        old_count = len(list(old_root.iter("{%s}p" % W_NS)))
        new_count = len(list(new_root.iter("{%s}p" % W_NS)))
        delta = new_count - old_count
        checks.append((f"문단 수 델타 == {EXPECTED_PARA_DELTA} (실제 {old_count}->{new_count}, delta {delta})",
                        delta == EXPECTED_PARA_DELTA, ""))
    else:
        checks.append(("문단 수 델타 확인", False, "well-formed 실패로 건너뜀"))

    checks.append(("캡션 텍스트 존재", "다섯 방식의 총 배출량 비교" in new_xml, ""))
    checks.append(("참조문 텍스트 존재", "두 경계(①의 손해, ③의 이상치)" in new_xml, ""))
    checks.append(("rId59 참조 존재", 'r:embed="rId59"' in new_xml, ""))
    checks.append(("rels에 rId59 추가됨", "rId59" in new_rels, ""))
    checks.append(("표2 문단(0A1B2C41) 안 건드렸는지", old_map.get("0A1B2C41") == new_map.get("0A1B2C41"), ""))
    checks.append(("표2 해설 서사(4D34B9DF) 안 건드렸는지", old_map.get("4D34B9DF") == new_map.get("4D34B9DF"), ""))

    all_ok = all(ok for _, ok, _ in checks)
    print()
    print("결과 검증:")
    for name, ok, detail in checks:
        mark = "OK  " if ok else "FAIL"
        print(f"  [{mark}] {name}" + (f" — {detail}" if detail and not ok else ""))

    if not all_ok:
        print("\nFATAL: 검증 실패, 아무 파일도 안 씀.")
        sys.exit(4)

    if args.dry_run:
        print("\n--dry-run 이므로 여기서 멈춘다. 실제 파일은 하나도 안 바뀜(media/rels 포함).")
        sys.exit(0)

    # ---- 5) 스냅샷 ----
    os.makedirs(VERSIONS_DIR, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M")
    snapshot_path = os.path.join(VERSIONS_DIR, f"CAST_{ts}_stage16전.docx")
    shutil.copy2(DOCX, snapshot_path)
    print(f"\n스냅샷: {snapshot_path}")

    # ---- 6) 원자적 쓰기 (document.xml 교체 + rels 교체 + media 신규 추가) ----
    new_docx_path = DOCX + ".new"
    if os.path.exists(new_docx_path):
        os.remove(new_docx_path)

    with open(MEDIA_ADD["source"], "rb") as f:
        media_bytes = f.read()

    with zipfile.ZipFile(DOCX, "r") as src, \
         zipfile.ZipFile(new_docx_path, "w", zipfile.ZIP_DEFLATED) as dst:
        for item in src.infolist():
            if item.filename == "word/document.xml":
                data = new_xml.encode("utf-8")
            elif item.filename == "word/_rels/document.xml.rels":
                data = new_rels.encode("utf-8")
            else:
                data = src.read(item.filename)
            dst.writestr(item, data)
        # 새 media 파일 추가(기존에 없던 항목)
        dst.writestr(MEDIA_ADD["docx_path"], media_bytes)

    with zipfile.ZipFile(new_docx_path) as z:
        names = z.namelist()
        assert MEDIA_ADD["docx_path"] in names, "새 media 파일이 zip에 없음"
        got_md5 = hashlib.md5(z.read(MEDIA_ADD["docx_path"])).hexdigest()
        assert got_md5 == MEDIA_ADD["md5"], "쓰기 후 media md5 불일치"
    print(f"media 추가 확인: {MEDIA_ADD['docx_path']} md5 일치")

    try:
        import docx
        docx.Document(new_docx_path)
        print("python-docx 로드: OK")
    except ImportError:
        print("python-docx 미설치 — 이 검증은 건너뜀")
    except Exception as e:
        print(f"FATAL: python-docx 로드 실패: {e}")
        os.remove(new_docx_path)
        sys.exit(5)

    os.replace(new_docx_path, DOCX)
    print(f"\n완료: {DOCX} 갱신됨. 스냅샷은 {snapshot_path} 에 보존.")
    print("Word로 열어 그림7 위치·캡션·크기(215×330pt, 단내) 육안 확인 권장.")


if __name__ == "__main__":
    main()
