"""
apply_stage12.py — E1 압축 2차: 6장(검증) 나머지 배치.
작성: 2026-09-21, carbon-aware-scheduler-4d(원고 트랙). 실행은 be가 한다.

DELETE_JUSTIFICATION = {
    "068A6731(문단561, §6.1)": "\"평가 규율(예측값/실측값 구분, 3단계 비교)\" 선언이 §6.3 문단597(표2 직전 도입부)에 사실상 그대로 반복된다. 597은 표2의 문맥상 필수 도입부라 남기고, §6.1쪽(561)을 지운다 — 실험설정 절에서 미리 알 필요는 없고 표2 직전에 한 번만 알면 충분하다.",
}
SENTENCE_TRIM_JUSTIFICATION = {
    "2182DCED(문단553, §6.1)": "말미의 리전 목록 문장이 §2 문단102(\"CAST는 8개 리전을 대상으로 한다. 미국 3개(캘리포니아, 텍사스, 뉴욕)...\")와 완전히 동일하다. 553의 나머지(탄소집약도 API 출처·해상도·방법론 URL)는 §2에 없는 553 고유 내용이라 문단 전체 삭제 대신 중복 문장 하나만 제거했다 — 정보 손실 없음(리전 목록은 102에 그대로 있음).",
}
"""
import sys, os, shutil, zipfile, datetime, argparse, re
import xml.etree.ElementTree as ET

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOCX = os.path.join(REPO, "paper", "CAST.docx")
VERSIONS_DIR = os.path.join(REPO, "paper", "versions")

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

DELETE_BLOCK = '<w:p w14:paraId="5CA6D01A" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00CA0C2E" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/></w:pPr></w:p><w:p w14:paraId="068A6731" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/></w:pPr><w:r><w:t>평가</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>규율은</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>다음과</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>같다</w:t></w:r><w:r><w:t xml:space="preserve">. </w:t></w:r><w:r><w:t>배치</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>결정에는</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>예측값만</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>사용하고</w:t></w:r><w:r><w:t xml:space="preserve">, </w:t></w:r><w:r><w:t>배출량</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>산정에는</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>실측값만</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>사용한다</w:t></w:r><w:r><w:t xml:space="preserve">. </w:t></w:r><w:r><w:t>세</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>단계를</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>동일한</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>회계로</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>비교한다</w:t></w:r><w:r><w:t xml:space="preserve">. </w:t></w:r><w:r><w:t>첫째</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>단계는</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>홈</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>리전</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>즉시</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>실행</w:t></w:r><w:r><w:t xml:space="preserve">, </w:t></w:r><w:r><w:t>둘째</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>단계는</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>탄소</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>인지</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>공간</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>이동</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>후</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>즉시</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>실행</w:t></w:r><w:r><w:t xml:space="preserve">, </w:t></w:r><w:r><w:t>셋째</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>단계는</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>여기에</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>시간</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>이동을</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>더한</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:t>것이다</w:t></w:r><w:r><w:t>.</w:t></w:r></w:p>'
P553_OLD = '<w:p w14:paraId="2182DCED" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/></w:pPr><w:r><w:t xml:space="preserve">평가는 8개 리전의 2025년 실측 탄소집약도 1년치 위에서 수행한다. 탄소집약도는 Electricity Maps API를 통해 1시간 해상도로 수집하였다 — 발전과 설비를 모두 포함하는 전과정 배출계수 체계를 쓰는 공식 방법론이다(https://www.electricitymaps.com/data/methodology). 대상 리전은 미국 3개(캘리포니아, 텍사스, 뉴욕), 유럽 2개(프랑스, 독일), 아시아 3개(한국, 일본, 인도)다.</w:t></w:r></w:p>'
P553_NEW = '<w:p w14:paraId="2182DCED" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000" w:rsidP="00724B75"><w:pPr><w:jc w:val="left"/></w:pPr><w:r><w:t xml:space="preserve">평가는 8개 리전의 2025년 실측 탄소집약도 1년치 위에서 수행한다. 탄소집약도는 Electricity Maps API를 통해 1시간 해상도로 수집하였다 — 발전과 설비를 모두 포함하는 전과정 배출계수 체계를 쓰는 공식 방법론이다(https://www.electricitymaps.com/data/methodology).</w:t></w:r></w:p>'

DELETIONS = [DELETE_BLOCK]
NUM_FIXES = [(P553_OLD, P553_NEW)]  # 이름은 NUM_FIXES지만 실제론 narrow text 치환(공용 로직 재사용)

EXPECTED_DELETED = {'5CA6D01A', '068A6731'}
EXPECTED_INSERTED = set()
EXPECTED_MODIFIED = {'2182DCED'}
EXPECTED_PARA_DELTA = -2
CHARS_SAVED_PROSE = 212
CUMULATIVE_CH6_TARGET = 4100
CUMULATIVE_CH6_SO_FAR_BEFORE_THIS_STAGE = 821  # stage11

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

    checks.append(("§6.1 문단561(평가 규율 중복 선언) 사라짐",
                    "068A6731" not in new_map if new_root is not None else False, ""))
    t597 = para_plain_text("408FBD51", new_xml)
    checks.append(("§6.3 문단597(표2 직전 도입부) 그대로 보존",
                    "세 단계를 동일한 회계로 비교하였다" in t597, "못 찾음/바뀜"))
    t553 = para_plain_text("2182DCED", new_xml)
    checks.append(("§6.1 문단553 고유 내용(측정 방법론) 보존",
                    "electricitymaps.com/data/methodology" in t553, "못 찾음"))
    checks.append(("§6.1 문단553에서 중복 리전목록 문장 제거됨",
                    "대상 리전은 미국 3개" not in t553, "아직 남아있음"))
    t102 = para_plain_text("5A29E817", new_xml)
    checks.append(("§2 문단102(리전 목록 원본) 안 건드렸는지 확인",
                    "미국 3개(캘리포니아, 텍사스, 뉴욕)" in t102, "못 찾음/바뀜"))

    all_ok = all(ok for _, ok, _ in checks)
    print()
    print("결과 검증:")
    for name, ok, detail in checks:
        mark = "OK  " if ok else "FAIL"
        print(f"  [{mark}] {name}" + (f" — {detail}" if detail and not ok else ""))

    if not all_ok:
        print("\nFATAL: 검증 실패, 아무 파일도 안 씀.")
        sys.exit(4)

    cumulative = CUMULATIVE_CH6_SO_FAR_BEFORE_THIS_STAGE + CHARS_SAVED_PROSE
    print(f"\n글자수 절감(이번 stage): {CHARS_SAVED_PROSE}자")
    print(f"6장 누계: {cumulative} / 목표 {CUMULATIVE_CH6_TARGET}자 "
          f"({100*cumulative/CUMULATIVE_CH6_TARGET:.0f}%)")

    if args.dry_run:
        print("\n--dry-run 이므로 여기서 멈춘다. 실제 파일은 하나도 안 바뀜.")
        sys.exit(0)

    os.makedirs(VERSIONS_DIR, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M")
    snapshot_path = os.path.join(VERSIONS_DIR, f"CAST_{ts}_stage12전.docx")
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
