# -*- coding: utf-8 -*-
"""CAST_JOK_투고본.docx 의 그림 10장을 지금 판으로 교체하고 삽입 폭을 JOK 규격에 맞춘다.

replace_figs.py 와 다른 점
--------------------------
 · 대상이 CAST_JOK_투고본.docx 다 (CAST_A4본.docx 는 A4 판본으로 그대로 둔다).
 · 폭을 **지정한다**. 옛 도구는 폭을 유지하고 높이만 다시 냈는데, 지금 docx 의
   삽입 폭이 167~215pt 로 제각각이라(옛 조판의 흔적) 그대로 두면 JOK 단 폭과
   안 맞는다. 단내 그림은 69mm(195.6pt), 전단 그림은 142.4mm(403.7pt)로 박는다.
 · 전단 두 장(그림1·2)은 쪽 규격을 JOK 로 바꾼 **뒤에** 넣어야 Word 가 단을
   가로지르게 잡는다 — 지금은 WIDE_READY 가 False 라 단내 폭으로만 둔다.

2026-09-24 교훈(옛 도구 주석에서 그대로 가져옴): 바꾼 것만 골라 적지 말고
열 장을 전부 적는다. 같은 바이트면 교체해도 무해하다.
"""
import io
import re
import shutil
import zipfile
import xml.etree.ElementTree as ET

from PIL import Image

REPO = "/Users/jongha/Desktop/GitHub/carbon-aware-scheduler/"
DOC = REPO + "paper/CAST_JOK_투고본.docx"
DIA = REPO + "paper/diagram/"

COL_PT = 69.0 * 72 / 25.4          # 195.59 — JOK 단 폭
FULL_PT = 402.0                     # 전단 폭. 실측 본문 폭 404.3pt 에 2.3pt 여유
EMU = 12700                         # 1pt
WIDE_READY = True                  # 쪽 규격을 JOK 로 바꾼 뒤 True 로

#  docx 안 이름 → (새 파일, 전단인가)
REPLACE = {
    "word/media/image1.png":  ("fig1_architecture.png",   True),   # 그림 1  파이프라인
    "word/media/image2.png":  ("fig2_forecast.png",       False),  # 그림 2  LSTM 구조(2026-10-10 단내로 전환)
    "word/media/image3.png":  ("fig3_forecast_curve.png", False),  # 그림 3  예측 곡선
    "word/media/image4.png":  ("fig3_loadbalancer.png",   False),  # 그림 4  무릎점 산점도
    "word/media/image5.png":  ("fig4_routing.png",        False),  # 그림 5  리전 간 흐름
    "word/media/image6.png":  ("fig4_pareto.png",         False),  # 그림 6  파레토 곡선
    "word/media/image7.png":  ("fig4_scheduler.png",      False),  # 그림 7  하루 점유
    "word/media/image8.png":  ("fig5_comparison.png",     False),  # 그림 8  배출량 비교
    "word/media/image9.png":  ("fig6_concurrency.png",    False),  # 그림 9  동시 실행 수
    "word/media/image10.png": ("fig7_benchmark.png",      False),  # 그림 10 선행 정책
}


def main():
    z = zipfile.ZipFile(DOC)
    parts = {i.filename: z.read(i.filename) for i in z.infolist()}
    infos = z.infolist()
    rel = parts["word/_rels/document.xml.rels"].decode()
    xml = parts["word/document.xml"].decode()
    z.close()

    for name, (fn, wide) in REPLACE.items():
        src = DIA + fn
        new_bytes = open(src, "rb").read()
        im_old = Image.open(io.BytesIO(parts[name]))
        im_new = Image.open(src)
        ratio = im_new.height / im_new.width
        want_w = FULL_PT if (wide and WIDE_READY) else COL_PT
        cx = int(round(want_w * EMU))
        cy = int(round(cx * ratio))

        m = re.search(rf'Id="(rId\d+)"[^>]*Target="{name.replace("word/", "")}"', rel)
        assert m, f"{name}: rId 를 못 찾음"
        rid = m.group(1)
        n = 0
        for mm in list(re.finditer(r'<w:drawing>.*?</w:drawing>', xml, re.DOTALL))[::-1]:
            frag = mm.group(0)
            if f'r:embed="{rid}"' not in frag:
                continue
            fixed = re.sub(r'cx="\d+" cy="\d+"', f'cx="{cx}" cy="{cy}"', frag)
            xml = xml[:mm.start()] + fixed + xml[mm.end():]
            n += 1
        assert n == 1, f"{name}: drawing {n}곳 (1이어야 함)"
        parts[name] = new_bytes
        print(f"  {name:22s} ← {fn:24s} {im_old.size} → {im_new.size} · "
              f"{cx/EMU:6.1f}×{cy/EMU:6.1f}pt{'  [전단 대기]' if wide and not WIDE_READY else ''}")

    ET.fromstring(xml)
    parts["word/document.xml"] = xml.encode()
    tmp = DOC + ".new"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as o:
        for it in infos:
            o.writestr(it, parts[it.filename])
    shutil.move(tmp, DOC)
    import docx
    docx.Document(DOC)
    print("교체 완료")


if __name__ == "__main__":
    main()
