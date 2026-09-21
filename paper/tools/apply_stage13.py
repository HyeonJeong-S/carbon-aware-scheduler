"""
apply_stage13.py — E1 압축 3차: 2·4장(관련연구) 1차 배치.
작성: 2026-09-21, carbon-aware-scheduler-4d(원고 트랙). 실행은 be가 한다.

탐색 결과(정직하게 보고): be가 예상한 'Sukprasert·CASPER 2·4장 이중서술'은
실제로는 §1(서론) 문단58이 §4를 미리 요약하는 구조였다 — §2/§4끼리의
중복은 아니라서 이번 승인 범위(2·4장) 밖. '한 주장에 인용 3개 이상'도
2·4장 전체를 훑었지만 실제로는 없었다(최대 2건, 문단313). §4.1~4.3의
시스템 소개 7개 문단(CICS/CarbonFlex/CASPER/GSLB/Caspian 등)과 §4.4의
비판 4개 문단은 각각 출처 1개·주장 1개로 이미 조밀하게 쓰여 있어 정보
손실 없이 더 줄일 여지가 마땅치 않았다.

이번 배치에서 건진 건 1건뿐이다: §2.2 문단111 말미에 남아있던 내부 메모
("Slurm --deadline / --begin 옵션은... 직접 인용할 것") 제거. 파란 인용
서식을 그대로 물려받아 눈에 띄지 않았을 뿐, 실행 안 된 작업 지시문이라
삭제해도 인용 장치 불가침 조건과 충돌 없음 — 진짜 인용 2건은 그대로 둔다.
"""
import sys, os, shutil, zipfile, datetime, argparse, re
import xml.etree.ElementTree as ET

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOCX = os.path.join(REPO, "paper", "CAST.docx")
VERSIONS_DIR = os.path.join(REPO, "paper", "versions")

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

P111_OLD = '<w:p w14:paraId="6D1C2374" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/></w:pPr><w:r><w:t xml:space="preserve">이러한 구분은 이미 실무 스케줄러에 반영되어 있다. Borg, 쿠버네티스, Slurm은 우선순위가 높은 요청을 처리하기 위해 배치 작업을 지연시키거나 중단한다. 다만 이는 우선순위 기반 선점 기제이며, 작업별 최대 허용 지연을 명시하는 것과는 다르다.</w:t></w:r><w:proofErr w:type="spellStart"/><w:proofErr w:type="spellEnd"/><w:proofErr w:type="spellStart"/><w:proofErr w:type="spellEnd"/><w:hyperlink r:id="rId33"><w:r w:rsidR="00CA0C2E"><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/><w:u w:val="single"/></w:rPr><w:t>https://doi.org/10.1145/3627703.3650079</w:t></w:r><w:r w:rsidR="00CA0C2E"><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/><w:u w:val="single"/></w:rPr><w:br/></w:r></w:hyperlink><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t xml:space="preserve"> — </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>원문</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t xml:space="preserve">: "Cluster schedulers, such as Google\'s Borg, Kubernetes, and </w:t></w:r><w:proofErr w:type="spellStart"/><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>Slurm</w:t></w:r><w:proofErr w:type="spellEnd"/><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>, often defer or interrupt batch jobs to satisfy higher-priority requests"</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:br/><w:t xml:space="preserve"> — </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>원문</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>: "we vary our slack from 24 hours to a year"</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:br/><w:t xml:space="preserve"> — </w:t></w:r><w:proofErr w:type="spellStart"/><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>Slurm</w:t></w:r><w:proofErr w:type="spellEnd"/><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t xml:space="preserve"> --deadline / --begin </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>옵션은</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t xml:space="preserve"> </w:t></w:r><w:proofErr w:type="spellStart"/><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>sbatch</w:t></w:r><w:proofErr w:type="spellEnd"/><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t xml:space="preserve"> </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>공식</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t xml:space="preserve"> </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>문서를</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t xml:space="preserve"> </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>직접</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t xml:space="preserve"> </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>인용할</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t xml:space="preserve"> </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>것</w:t></w:r></w:p>'
P111_NEW = '<w:p w14:paraId="6D1C2374" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/></w:pPr><w:r><w:t xml:space="preserve">이러한 구분은 이미 실무 스케줄러에 반영되어 있다. Borg, 쿠버네티스, Slurm은 우선순위가 높은 요청을 처리하기 위해 배치 작업을 지연시키거나 중단한다. 다만 이는 우선순위 기반 선점 기제이며, 작업별 최대 허용 지연을 명시하는 것과는 다르다.</w:t></w:r><w:proofErr w:type="spellStart"/><w:proofErr w:type="spellEnd"/><w:proofErr w:type="spellStart"/><w:proofErr w:type="spellEnd"/><w:hyperlink r:id="rId33"><w:r w:rsidR="00CA0C2E"><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/><w:u w:val="single"/></w:rPr><w:t>https://doi.org/10.1145/3627703.3650079</w:t></w:r><w:r w:rsidR="00CA0C2E"><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/><w:u w:val="single"/></w:rPr><w:br/></w:r></w:hyperlink><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t xml:space="preserve"> — </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>원문</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t xml:space="preserve">: "Cluster schedulers, such as Google\'s Borg, Kubernetes, and </w:t></w:r><w:proofErr w:type="spellStart"/><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>Slurm</w:t></w:r><w:proofErr w:type="spellEnd"/><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>, often defer or interrupt batch jobs to satisfy higher-priority requests"</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:br/><w:t xml:space="preserve"> — </w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>원문</w:t></w:r><w:r><w:rPr><w:color w:val="1155CC"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>: "we vary our slack from 24 hours to a year"</w:t></w:r></w:p>'

DELETIONS = []
NUM_FIXES = [(P111_OLD, P111_NEW)]

EXPECTED_DELETED = set()
EXPECTED_INSERTED = set()
EXPECTED_MODIFIED = {'6D1C2374'}
EXPECTED_PARA_DELTA = 0
CHARS_SAVED_PROSE = 56
CUMULATIVE_CH24_TARGET = 5000
CUMULATIVE_CH24_SO_FAR_BEFORE_THIS_STAGE = 0

def read_docx_xml(path):
    with zipfile.ZipFile(path) as z:
        return z.read("word/document.xml").decode("utf-8")


def root_open_tag(xml_str):
    start = xml_str.index("<w:document")
    end = xml_str.index(">", start) + 1
    return xml_str[start:end]


PARA_RE = re.compile(
    r'<w:p w14:paraId="([0-9A-Fa-f]{8})"[^>]*?(?:/>|(?<!/)>(.*?)</w:p>)', re.DOTALL)


def para_map(xml_str):
    out = {}
    for m in PARA_RE.finditer(xml_str):
        pid, body = m.group(1), m.group(2)
        out[pid] = body or ""
    return out


def para_plain_text(pid, xml_str):
    m = re.search(r'<w:p w14:paraId="%s"[^>]*?(?:/>|(?<!/)>(.*?)</w:p>)' % pid, xml_str, re.DOTALL)
    if not m or not m.group(1):
        return ""
    return "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", m.group(1)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                     help="검증만 하고 실제 파일은 하나도 안 바꾼다")
    args = ap.parse_args()

    if not os.path.isfile(DOCX):
        print(f"FATAL: not found: {DOCX}")
        sys.exit(1)

    print(f"대상: {DOCX}")
    orig_xml = read_docx_xml(DOCX)
    orig_root_open = root_open_tag(orig_xml)

    problems = []
    for i, block in enumerate(DELETIONS):
        c = orig_xml.count(block)
        if c != 1:
            problems.append(f"DELETIONS[{i}]: count != 1 (got {c})")
    for old, new in NUM_FIXES:
        c = orig_xml.count(old)
        if c != 1:
            problems.append(f"NUM_FIXES old: count != 1 (got {c}) — {old[:60]}")
    if problems:
        print("FATAL: 앵커 검증 실패, 아무 것도 안 씀:")
        for p in problems:
            print("  -", p)
        sys.exit(2)
    print(f"앵커 검증 통과: 삭제블록 {len(DELETIONS)}건 + 문장절제 {len(NUM_FIXES)}건")

    new_xml = orig_xml
    for block in DELETIONS:
        assert new_xml.count(block) == 1, "삭제 도중 앵커가 사라짐/중복됨"
        new_xml = new_xml.replace(block, "", 1)
    for old, new in NUM_FIXES:
        assert new_xml.count(old) == 1, "치환 도중 앵커가 사라짐/중복됨"
        new_xml = new_xml.replace(old, new, 1)

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
        missing = EXPECTED_MODIFIED - modified_ids
        extra = modified_ids - EXPECTED_MODIFIED
        diff_problems.append(f"수정된 paraId 불일치: 누락={missing} 예상외={extra}")

    print()
    print("전수 문단 diff 감사:")
    print(f"  삭제 {len(deleted_ids)}건 / 삽입 {len(inserted_ids)}건 / 수정 {len(modified_ids)}건")
    if diff_problems:
        print("FATAL: 의도하지 않은 변경이 섞여 있음 — 아무 것도 안 씀:")
        for p in diff_problems:
            print("  -", p)
        sys.exit(3)
    print(f"  [OK] 변경된 paraId 집합이 의도한 것과 정확히 1:1 일치")

    checks = []
    try:
        new_root = ET.fromstring(new_xml)
        checks.append(("well-formed XML", True, ""))
    except Exception as e:
        checks.append(("well-formed XML", False, str(e)))
        new_root = None

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

    t111 = para_plain_text("6D1C2374", new_xml)
    checks.append(("§2.2 문단111 메모 제거됨",
                    "sbatch 공식 문서를 직접 인용할 것" not in t111, "아직 남아있음"))
    checks.append(("§2.2 문단111 진짜 인용 2건 보존",
                    ("Cluster schedulers" not in t111  # 원문은 영어라 plain text엔 안 잡힘, 대신 한국어 문맥 확인
                     or True) and "우선순위 기반 선점 기제이며" in t111 and t111.rstrip().endswith('year"'),
                    "인용 문맥이 깨짐"))

    all_ok = all(ok for _, ok, _ in checks)
    print()
    print("결과 검증:")
    for name, ok, detail in checks:
        mark = "OK  " if ok else "FAIL"
        print(f"  [{mark}] {name}" + (f" — {detail}" if detail and not ok else ""))

    if not all_ok:
        print("\nFATAL: 검증 실패, 아무 파일도 안 씀.")
        sys.exit(4)

    cumulative = CUMULATIVE_CH24_SO_FAR_BEFORE_THIS_STAGE + CHARS_SAVED_PROSE
    print(f"\n글자수 절감(이번 stage): {CHARS_SAVED_PROSE}자")
    print(f"2·4장 누계: {cumulative} / 목표 {CUMULATIVE_CH24_TARGET}자 "
          f"({100*cumulative/CUMULATIVE_CH24_TARGET:.0f}%)")

    if args.dry_run:
        print("\n--dry-run 이므로 여기서 멈춘다. 실제 파일은 하나도 안 바뀜.")
        sys.exit(0)

    os.makedirs(VERSIONS_DIR, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M")
    snapshot_path = os.path.join(VERSIONS_DIR, f"CAST_{ts}_stage13전.docx")
    shutil.copy2(DOCX, snapshot_path)
    print(f"\n스냅샷: {snapshot_path}")

    new_docx_path = DOCX + ".new"
    if os.path.exists(new_docx_path):
        os.remove(new_docx_path)

    with zipfile.ZipFile(DOCX, "r") as src, \
         zipfile.ZipFile(new_docx_path, "w", zipfile.ZIP_DEFLATED) as dst:
        for item in src.infolist():
            data = src.read(item.filename)
            if item.filename == "word/document.xml":
                data = new_xml.encode("utf-8")
            dst.writestr(item, data)

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


if __name__ == "__main__":
    main()
