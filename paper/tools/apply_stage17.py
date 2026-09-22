"""
apply_stage17.py — 표제부 저자 정보 블록 삽입.
작성: 2026-09-22, carbon-aware-scheduler-4d(원고 트랙). 실행은 be가 한다.

A13_표제부규칙.txt의 설계(Keywords 영문 뒤·첫 빈 패딩 문단 앞 삽입,
기존 빈 문단·sectPr 안 건드림)를 그대로 따르되, paraId는 이번에 라이브
문서에서 새로 조회했다 — 그림7 '최종' 커밋(Word 직접 편집으로 보임)
이후 표제부 전체 paraId가 재발급돼 A13 작성 시점 값이 전부 무효화됐다.

저자 4명(이종하*·강희진·강동규·김현정), 소속은 【소속 미정】 플레이스홀더
(사용자가 안 줘서 안 지어냄), 이종하 이메일은 실제(git 커밋 작성자와
일치), 강희진은 사용자 요청대로 명백한 임시 이메일, 나머지 둘은 이메일
없음. 교신저자 지정과 강희진 임시 이메일 둘 다 사용자 확인 필요로
주석에 남겼다. 날짜란(접수/수정/게재확정)은 학회 미확정이라 플레이스홀더.
"""
import sys, os, shutil, zipfile, datetime, argparse, re
import xml.etree.ElementTree as ET

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOCX = os.path.join(REPO, "paper", "CAST.docx")
VERSIONS_DIR = os.path.join(REPO, "paper", "versions")

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

ANCHOR_KEYWORDS_EN = '<w:p w14:paraId="230349EF" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000"><w:r><w:rPr><w:b/><w:bCs/></w:rPr><w:t xml:space="preserve">Keywords: </w:t></w:r><w:r><w:t>Carbon-aware scheduling, Workload shifting, Integer programming, Regional capacity, LSTM</w:t></w:r></w:p>'
NEW_BLOCK_APPEND = '<w:p w14:paraId="AB000001" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000"><w:pPr><w:jc w:val="center"/></w:pPr><w:r><w:rPr><w:sz w:val="22"/><w:szCs w:val="22"/></w:rPr><w:t xml:space="preserve">이종하¹* · 강희진¹ · 강동규¹ · 김현정¹</w:t></w:r></w:p><w:p w14:paraId="AB000002" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000"><w:pPr><w:jc w:val="center"/></w:pPr><w:r><w:rPr><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:t xml:space="preserve">¹ 【소속 미정】</w:t></w:r></w:p><w:p w14:paraId="AB000003" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000"><w:pPr><w:jc w:val="left"/></w:pPr><w:r><w:rPr><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:t xml:space="preserve">* Corresponding Author: 이종하 (E-mail: jongha8273@naver.com) — 교신저자 지정, 사용자 확인 필요</w:t></w:r></w:p><w:p w14:paraId="AB000004" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000"><w:pPr><w:jc w:val="left"/></w:pPr><w:r><w:rPr><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:t xml:space="preserve">강희진 (E-mail: heejin@example.com, 임시 — 확정 필요)</w:t></w:r></w:p><w:p w14:paraId="AB000005" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00000000"><w:pPr><w:jc w:val="center"/></w:pPr><w:r><w:rPr><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:t xml:space="preserve">접수일: 【YYYY-MM-DD】 / 수정일: 【YYYY-MM-DD】 / 게재확정일: 【YYYY-MM-DD】</w:t></w:r></w:p><w:p w14:paraId="AB000006" w14:textId="77777777" w:rsidR="00CA0C2E" w:rsidRDefault="00CA0C2E"/>'

EXPECTED_INSERTED = {'AB000001', 'AB000002', 'AB000003', 'AB000004', 'AB000005', 'AB000006'}
EXPECTED_DELETED = set()
EXPECTED_MODIFIED = set()
EXPECTED_PARA_DELTA = 6

def read_docx_xml(path):
    with zipfile.ZipFile(path) as z:
        return z.read("word/document.xml").decode("utf-8")


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

    print(f"대상: {DOCX}")
    orig_xml = read_docx_xml(DOCX)
    orig_root_open = root_open_tag(orig_xml)

    # ---- 1) 앵커 검증 ----
    problems = []
    c = orig_xml.count(ANCHOR_KEYWORDS_EN)
    if c != 1:
        problems.append(f"ANCHOR_KEYWORDS_EN: count != 1 (got {c})")
    for pid in ("AB000001", "AB000002", "AB000003", "AB000004", "AB000005", "AB000006"):
        if f'w14:paraId="{pid}"' in orig_xml:
            problems.append(f"paraId {pid}: 이미 문서에 존재함(충돌)")
    if problems:
        print("FATAL: 앵커 검증 실패, 아무 것도 안 씀:")
        for p in problems:
            print("  -", p)
        sys.exit(2)
    print("앵커 검증 통과: Keywords(영문) 문단 1건, 새 paraId 6건 충돌 없음")

    # ---- 2) 적용 (Keywords-EN 문단 바로 뒤에 새 블록 삽입) ----
    new_xml = orig_xml.replace(ANCHOR_KEYWORDS_EN, ANCHOR_KEYWORDS_EN + NEW_BLOCK_APPEND, 1)

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
    print("  [OK] 삽입 6건(AB000001~6)만, 삭제/수정 0건")

    # ---- 4) 결과 검증 ----
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
        # sectPr 보유 문단이 정확히 1개(2구역 끝 경계 유지)인지
        sect_count = sum(1 for p in new_root.iter("{%s}p" % W_NS)
                          if p.find(".//{%s}sectPr" % W_NS) is not None)
        checks.append((f"sectPr 보유 문단 수 불변(1개)", sect_count == 1, f"실제 {sect_count}개"))
    else:
        checks.append(("문단 수 델타 확인", False, "well-formed 실패로 건너뜀"))

    checks.append(("저자명 줄 존재", "이종하" in new_xml and "강희진" in new_xml
                    and "강동규" in new_xml and "김현정" in new_xml, ""))
    checks.append(("교신저자 이메일 존재", "jongha8273@naver.com" in new_xml, ""))
    checks.append(("소속 플레이스홀더 존재(지어내지 않음)", "【소속 미정】" in new_xml, ""))
    checks.append(("날짜 플레이스홀더 존재", "【YYYY-MM-DD】" in new_xml, ""))

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
        print("\n--dry-run 이므로 여기서 멈춘다. 실제 파일은 하나도 안 바뀜.")
        sys.exit(0)

    # ---- 5) 스냅샷 ----
    os.makedirs(VERSIONS_DIR, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M")
    snapshot_path = os.path.join(VERSIONS_DIR, f"CAST_{ts}_stage17전.docx")
    shutil.copy2(DOCX, snapshot_path)
    print(f"\n스냅샷: {snapshot_path}")

    # ---- 6) 원자적 쓰기 ----
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
    print("Word로 열어 표제부(1단) 레이아웃 안 깨졌는지, 저자 블록 위치 육안 확인 권장.")
    print("남은 할 일(사용자 확인): 소속, 교신저자 지정 확정, 강희진 임시 이메일,")
    print("접수/수정/게재확정 날짜, 최종 투고 학회.")


if __name__ == "__main__":
    main()
