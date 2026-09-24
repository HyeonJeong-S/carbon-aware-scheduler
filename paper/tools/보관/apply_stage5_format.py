"""
apply_stage5_format.py — E9 서식 정정 3건 일괄 적용
작성: 2026-09-21, carbon-aware-scheduler-0c(그림 트랙, E9 조사자). 실행은 be가, 리뷰는 3d가 한다.

담는 규칙 3개 (paper/E9_서식점검.txt 참고):
  R1. 표 캡션 문단("표 N. ...") 전부에 9pt(sz=18) 명시 — 지금은 크기 지정이
      아예 없어 본문 기본값을 상속한다(그림 캡션은 이미 9pt라 안 맞았음).
  R2. 표6 내부에서 7.5pt(sz=15)로 잘못 들어간 run들을 8pt(sz=16)로 통일 —
      나머지 표1~5는 이미 8pt라 그대로 둔다.
  R3. Algorithm 1 블록 문단에 위/아래 가는 실선 테두리 추가(booktabs 느낌) —
      사용자가 논문 디자인 완성도를 지시, be가 채택.

apply_stage3.py(4d)와 같은 안전장치를 따른다: 스냅샷 -> 원자적 쓰기 -> 검증.
다른 점: apply_stage3.py는 특정 커밋 시점에서 추출한 앵커 문자열을 스크립트에
리터럴로 박아넣었지만, 이 스크립트는 **실행 시점의 라이브 document.xml에서
매번 앵커를 다시 찾는다**(be 지시: "네 스크립트가 실행될 시점엔 문서가 또
바뀌어 있을 거다 — paraId 앵커와 상대 검증이면 안전하다"). 그래서 하드코딩된
paraId나 표 개수를 기대하지 않는다 — 표 캡션이 6개든 7개든(신규 alpha표
삽입 여부와 무관하게) 찾은 만큼 전부 처리하고, 실제로 몇 건 처리했는지
결과에 찍어서 3d/be가 눈으로 타당한지 확인하게 한다.

ElementTree는 "찾기"에만 쓴다(문단 위치 파악, 문단 수 검증). 실제 쓰기는
문자열 치환으로 한다(자동작업.md 규칙4: "ElementTree 금지(정규식만)") —
ET로 파싱한 트리를 다시 직렬화해서 저장하면 mc:Ignorable, 속성 순서,
xml:space 같은 것들이 깨질 수 있기 때문이다.

사용법:
  python3 paper/tools/apply_stage5_format.py --dry-run   (기본, 검증만)
  python3 paper/tools/apply_stage5_format.py --apply     (실제로 씀 — be 전용)
"""
import argparse
import datetime
import os
import re
import shutil
import sys
import xml.etree.ElementTree as ET
import zipfile

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOCX = os.path.join(REPO, "paper", "CAST.docx")
VERSIONS_DIR = os.path.join(REPO, "paper", "versions")

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = "{%s}" % W_NS

# R3 테두리 값 — be 지시 "single 4/8pt 검정, 여백 적당히"를 구체 수치로 옮긴 것.
# sz는 1/8pt 단위(OOXML 표준) — 8="1pt"(be가 준 범위의 위쪽 값, 표 테두리
# sz=12=1.5pt보다는 살짝 얇게 해서 코드블록이 표보다 무겁지 않게 했다).
# space는 텍스트-테두리 간격, pt 단위. 리뷰(3d)에서 마음에 안 들면 이 두
# 상수만 바꾸면 된다.
ALGO_BORDER_SZ = "8"      # 1pt
ALGO_BORDER_SPACE = "4"   # 4pt


def read_docx_xml(path):
    with zipfile.ZipFile(path) as z:
        return z.read("word/document.xml").decode("utf-8")


def root_open_tag(xml_str):
    start = xml_str.index("<w:document")
    end = xml_str.index(">", start) + 1
    return xml_str[start:end]


def para_text(p_elem):
    return "".join(t.text or "" for t in p_elem.findall(".//%st" % W))


def find_para_span(xml_str, para_id):
    """paraId로 <w:p ...>부터 짝이 되는 </w:p>까지 원문 문자열 구간을 찾는다.
    w:p는 서로 안 중첩되므로(OOXML 규약) 여는 태그 다음에 오는 첫 </w:p>가
    항상 정확히 그 문단의 끝이다."""
    open_tag_pat = re.compile(r'<w:p [^>]*w14:paraId="%s"[^>]*>' % re.escape(para_id))
    m = open_tag_pat.search(xml_str)
    if not m:
        return None
    start = m.start()
    end = xml_str.index("</w:p>", m.end()) + len("</w:p>")
    return start, end


def set_run_size(run_xml, sz):
    """<w:r>...</w:r> 하나 안의 w:sz/w:szCs를 sz로 맞춘다(없으면 rPr까지 새로 만듦).
    이미 다른 값의 sz/szCs가 있으면 그 값을 sz로 바꾼다."""
    if "<w:rPr>" not in run_xml:
        # rPr 자체가 없음 -> <w:r> 바로 뒤에 새로 삽입
        return run_xml.replace(
            "<w:r>", '<w:r><w:rPr><w:sz w:val="%s"/><w:szCs w:val="%s"/></w:rPr>' % (sz, sz),
            1,
        )
    rpr_m = re.search(r"<w:rPr>(.*?)</w:rPr>", run_xml, re.S)
    rpr_inner = rpr_m.group(1)
    if "<w:sz " in rpr_inner or "<w:sz/>" in rpr_inner:
        new_inner = re.sub(r'<w:sz w:val="\d+"/>', '<w:sz w:val="%s"/>' % sz, rpr_inner)
    else:
        new_inner = rpr_inner + '<w:sz w:val="%s"/>' % sz
    if "<w:szCs " in new_inner or "<w:szCs/>" in new_inner:
        new_inner = re.sub(r'<w:szCs w:val="\d+"/>', '<w:szCs w:val="%s"/>' % sz, new_inner)
    else:
        new_inner = new_inner + '<w:szCs w:val="%s"/>' % sz
    new_rpr = "<w:rPr>%s</w:rPr>" % new_inner
    return run_xml[: rpr_m.start()] + new_rpr + run_xml[rpr_m.end():]


def apply_size_to_paragraph(para_xml, sz):
    """문단 원문 안의 모든 <w:r>...</w:r>에 set_run_size를 적용한다.
    (표 캡션은 보통 run 1개지만, Word가 run을 쪼개놨을 경우까지 방어.)"""
    parts = []
    last = 0
    for m in re.finditer(r"<w:r>.*?</w:r>", para_xml, re.S):
        parts.append(para_xml[last:m.start()])
        parts.append(set_run_size(m.group(0), sz))
        last = m.end()
    parts.append(para_xml[last:])
    return "".join(parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true",
                     help="실제로 파일을 쓴다. 기본은 검증만 하는 dry-run.")
    args = ap.parse_args()
    dry_run = not args.apply

    if not os.path.isfile(DOCX):
        print(f"FATAL: not found: {DOCX}")
        sys.exit(1)

    print(f"대상: {DOCX}  ({'dry-run' if dry_run else 'APPLY'})")
    orig_xml = read_docx_xml(DOCX)
    orig_root_open = root_open_tag(orig_xml)
    orig_root = ET.fromstring(orig_xml)
    orig_para_count = len(list(orig_root.iter(W + "p")))
    print(f"현재 문단 수(표 안 포함, 재귀): {orig_para_count}")

    body = orig_root.find(W + "body")
    all_paras = list(body.iter(W + "p"))

    # ---- R1 대상: "표 N." 로 시작하는 문단 전부 (몇 개인지 하드코딩 안 함) ----
    cap_re = re.compile(r"^표\s*\d+\.")
    r1_targets = []  # (paraId, text)
    for p in all_paras:
        pid = p.get("{http://schemas.microsoft.com/office/word/2010/wordml}paraId")
        if pid is None:
            continue
        txt = para_text(p).strip()
        if cap_re.match(txt):
            r1_targets.append((pid, txt))

    print(f"\nR1 — 표 캡션 문단 탐지: {len(r1_targets)}건")
    for pid, txt in r1_targets:
        print(f"   paraId={pid}  {txt[:50]!r}")
    if not (5 <= len(r1_targets) <= 10):
        print(f"FATAL: 표 캡션 개수({len(r1_targets)})가 상식 범위(5~10)를 벗어남 — "
              f"정규식이 엉뚱한 걸 잡았을 가능성. 검토 필요, 아무 것도 안 씀.")
        sys.exit(2)

    # ---- R2 대상: "표 6." 캡션 뒤에 오는 첫 <w:tbl>...</w:tbl> ----
    r2_caption = None
    for pid, txt in r1_targets:
        if re.match(r"^표\s*6\.", txt):
            r2_caption = pid
            break
    if r2_caption is None:
        print("FATAL: '표 6.' 캡션을 못 찾음 — R2 대상 없음, 아무 것도 안 씀.")
        sys.exit(2)

    # ---- R3 대상: Algorithm 1 코드블록 문단 (Courier New + '슬롯 단위 롤링 재평가') ----
    r3_target = None
    for p in all_paras:
        pid = p.get("{http://schemas.microsoft.com/office/word/2010/wordml}paraId")
        txt = para_text(p)
        if pid and "Algorithm 1" in txt and "슬롯 단위 롤링 재평가" in txt:
            r3_target = pid
            break
    if r3_target is None:
        print("FATAL: Algorithm 1 코드블록 문단을 못 찾음 — R3 대상 없음, 아무 것도 안 씀.")
        sys.exit(2)
    print(f"\nR3 — Algorithm 1 문단: paraId={r3_target}")

    # ================================================================
    # 실제 치환 (전부 원문 문자열 위에서, ElementTree로 다시 안 씀)
    # ================================================================
    new_xml = orig_xml
    r1_applied = 0

    # --- R1 적용 ---
    for pid, txt in r1_targets:
        span = find_para_span(new_xml, pid)
        if span is None:
            print(f"FATAL: R1 처리 중 paraId={pid} 문단을 원문에서 다시 못 찾음 "
                  f"(치환 순서 중 앞의 치환이 이 문단을 건드렸을 가능성).")
            sys.exit(3)
        start, end = span
        old_para = new_xml[start:end]
        new_para = apply_size_to_paragraph(old_para, "18")
        if new_para == old_para:
            print(f"경고: paraId={pid} 는 이미 9pt였던 것으로 보임(변화 없음) — 계속 진행.")
        new_xml = new_xml[:start] + new_para + new_xml[end:]
        r1_applied += 1

    # --- R2 적용: 표6 캡션 뒤 첫 표의 sz=15 -> 16 ---
    cap_span = find_para_span(new_xml, r2_caption)
    if cap_span is None:
        print("FATAL: R2 처리 중 표6 캡션을 다시 못 찾음.")
        sys.exit(3)
    tbl_start = new_xml.index("<w:tbl>", cap_span[1])
    tbl_end = new_xml.index("</w:tbl>", tbl_start) + len("</w:tbl>")
    old_tbl = new_xml[tbl_start:tbl_end]
    r2_count = old_tbl.count('<w:sz w:val="15"/>') + old_tbl.count('<w:szCs w:val="15"/>')
    new_tbl = old_tbl.replace('<w:sz w:val="15"/>', '<w:sz w:val="16"/>')
    new_tbl = new_tbl.replace('<w:szCs w:val="15"/>', '<w:szCs w:val="16"/>')
    new_xml = new_xml[:tbl_start] + new_tbl + new_xml[tbl_end:]
    print(f"\nR2 — 표6 안 7.5pt run {r2_count}개를 8pt로 교체")
    if r2_count == 0:
        print("경고: 표6 안에 7.5pt(sz=15)가 하나도 없었음 — 이미 고쳐져 있었거나 "
              "E9 조사 이후 표6 구조가 바뀌었을 수 있음. 계속 진행하되 3d가 확인할 것.")

    # --- R3 적용: Algorithm 1 문단에 pBdr 삽입 ---
    r3_span = find_para_span(new_xml, r3_target)
    if r3_span is None:
        print("FATAL: R3 처리 중 Algorithm 1 문단을 다시 못 찾음.")
        sys.exit(3)
    start, end = r3_span
    old_para = new_xml[start:end]
    pbdr_xml = (
        "<w:pPr><w:pBdr>"
        '<w:top w:val="single" w:sz="%s" w:space="%s" w:color="000000"/>'
        '<w:bottom w:val="single" w:sz="%s" w:space="%s" w:color="000000"/>'
        "</w:pBdr></w:pPr>"
    ) % (ALGO_BORDER_SZ, ALGO_BORDER_SPACE, ALGO_BORDER_SZ, ALGO_BORDER_SPACE)
    if "<w:pPr>" in old_para[:120]:
        print(f"FATAL: Algorithm 1 문단에 이미 <w:pPr>가 있음 — 이 스크립트는 '없는 경우'만 "
              f"가정하고 만들어졌다. 수동 확인 필요, 아무 것도 안 씀.")
        sys.exit(3)
    open_tag_end = old_para.index(">") + 1  # "<w:p ...>" 여는 태그 끝
    new_para = old_para[:open_tag_end] + pbdr_xml + old_para[open_tag_end:]
    new_xml = new_xml[:start] + new_para + new_xml[end:]
    print(f"R3 — Algorithm 1 문단에 위/아래 테두리 삽입 (sz={ALGO_BORDER_SZ}, space={ALGO_BORDER_SPACE})")

    # ================================================================
    # 결과 검증 (파일 쓰기 전에 전부 통과해야 함)
    # ================================================================
    checks = []

    try:
        new_root = ET.fromstring(new_xml)
        checks.append(("well-formed XML", True, ""))
    except Exception as e:
        checks.append(("well-formed XML", False, str(e)))
        new_root = None

    new_root_open = root_open_tag(new_xml)
    checks.append(("루트 <w:document> 태그 불변", new_root_open == orig_root_open,
                    "" if new_root_open == orig_root_open else "mc:Ignorable 등 확인 필요"))

    if new_root is not None:
        new_para_count = len(list(new_root.iter(W + "p")))
        checks.append((f"문단 수 불변 (R1~R3는 문단을 추가/삭제하지 않음, {orig_para_count}->{new_para_count})",
                        new_para_count == orig_para_count, ""))
    else:
        checks.append(("문단 수 불변 확인", False, "well-formed 실패로 건너뜀"))

    sz18_added = new_xml.count('w:val="18"') - orig_xml.count('w:val="18"')
    checks.append((f"sz=18 참조 증가량 >= {r1_applied} (표캡션 R1건수만큼은 늘어야 함, 실제 +{sz18_added})",
                    sz18_added >= r1_applied, ""))

    sz15_remaining = new_xml.count('<w:sz w:val="15"/>')
    checks.append((f"표6 이후 sz=15 잔존 0건 (실제 {sz15_remaining})", sz15_remaining == 0,
                    "다른 곳에 sz=15가 더 있었을 수 있음 — 표6 범위 밖은 안 건드렸는지 확인"))

    checks.append(("Algorithm 1 문단에 pBdr 존재", "<w:pBdr>" in new_xml and
                    '<w:top w:val="single" w:sz="%s"' % ALGO_BORDER_SZ in new_xml, ""))

    all_ok = all(ok for _, ok, _ in checks)
    print("\n결과 검증:")
    for name, ok, detail in checks:
        mark = "OK  " if ok else "FAIL"
        print(f"  [{mark}] {name}" + (f" — {detail}" if detail and not ok else ""))

    if not all_ok:
        print("\nFATAL: 검증 실패, 아무 파일도 안 씀.")
        sys.exit(4)

    if dry_run:
        print("\n--dry-run 이므로 여기서 멈춘다(기본 모드). 실제로 쓰려면 --apply.")
        sys.exit(0)

    # ---- 스냅샷 ----
    os.makedirs(VERSIONS_DIR, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M")
    snapshot_path = os.path.join(VERSIONS_DIR, f"CAST_{ts}_서식정정전.docx")
    shutil.copy2(DOCX, snapshot_path)
    print(f"\n스냅샷: {snapshot_path}")

    # ---- 원자적 쓰기 ----
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
        import docx  # python-docx
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
    print(f"적용 요약 — R1(표캡션 9pt) {r1_applied}건 / R2(표6 8pt 통일) {r2_count}건 / "
          f"R3(Algorithm 1 테두리) 1건.")
    print("Word로 열어 육안 확인 필수 — 특히 표 캡션 크기와 Algorithm 1 박스 모양.")


if __name__ == "__main__":
    main()
