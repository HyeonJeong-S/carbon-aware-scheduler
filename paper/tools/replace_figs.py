# -*- coding: utf-8 -*-
"""docx 안의 그림 파일을 새 판으로 교체하고 삽입 크기를 종횡비에 맞춘다.

그림을 바꿀 때 바이트만 갈아끼우면 이전 그림의 가로:세로 비율이 그대로 남아
새 그림이 늘어나거나 눌린다. <wp:extent cx cy> 와 <a:ext cx cy> 를 함께 고쳐
폭은 유지하고 높이만 새 비율로 다시 계산한다.
"""
import re
import shutil
import zipfile
import xml.etree.ElementTree as ET

from PIL import Image

REPO = "/Users/jongha/Desktop/GitHub/carbon-aware-scheduler/"
DOC = REPO + "paper/CAST_압축본.docx"
DIA = REPO + "paper/diagram/"

# docx 안 이름 -> 새 파일
# 2026-09-24 2차: 개념도(상자·화살표)를 실측 자료 그림으로 전면 교체
REPLACE = {
    "word/media/image1.png": DIA + "fig1_architecture.png",    # 그림 1 파이프라인
    "word/media/image2.png": DIA + "fig2_forecast.png",        # 그림 2 LSTM (CASPER 작화)
    "word/media/image4.png": DIA + "fig3_loadbalancer.png",    # 그림 4 무릎점 (★ 제거)
    "word/media/image6.png": DIA + "fig4_pareto.png",          # 그림 6 파레토 (★ 제거)
    # 그림 7: 캡션("캘리포니아의 한 날이다")이 실측 그림을 가리키는데 개념도가
    # 들어가 있었다. Algorithm 1 이 바로 옆에 있어 개념도는 중복이기도 하다.
    "word/media/image7.png": DIA + "fig4_scheduler.png",       # 그림 7 하루 점유 (실측)
    "word/media/image5.png": DIA + "fig4_routing.png",         # 그림 5 라우팅 흐름 (라벨 정렬)
    "word/media/image10.png": DIA + "fig7_benchmark.png",      # 그림 10 선행 정책 (음영 라벨)
}


def main():
    shutil.copy2(DOC, REPO + "paper/versions/2026-09-24/CAST_압축본_그림교체전.docx")
    z = zipfile.ZipFile(DOC)
    parts = {i.filename: z.read(i.filename) for i in z.infolist()}
    infos = z.infolist()
    rel = parts["word/_rels/document.xml.rels"].decode()
    xml = parts["word/document.xml"].decode()

    for name, src in REPLACE.items():
        old_ratio = None
        with Image.open(REPO + "paper/versions/2026-09-24/_tmp") if False else open(src, "rb") as f:
            new_bytes = f.read()
        im_old = Image.open(__import__("io").BytesIO(parts[name]))
        im_new = Image.open(src)
        old_ratio = im_old.height / im_old.width
        new_ratio = im_new.height / im_new.width

        # 이 media 를 참조하는 rId 를 찾고, 그 rId 를 쓰는 drawing 의 extent 를 고친다
        rid = re.search(rf'Id="(rId\d+)"[^>]*Target="{name.replace("word/", "")}"', rel).group(1)
        n = 0
        for m in list(re.finditer(r'<w:drawing>.*?</w:drawing>', xml, re.DOTALL))[::-1]:
            frag = m.group(0)
            if f'r:embed="{rid}"' not in frag:
                continue
            def fix(mm):
                cx = int(mm.group(1))
                return f'{mm.group(0)[:mm.start(1)-mm.start(0)]}{cx}" cy="{int(round(cx*new_ratio))}"'
            fixed = re.sub(r'cx="(\d+)" cy="\d+"',
                           lambda mm: f'cx="{mm.group(1)}" cy="{int(round(int(mm.group(1))*new_ratio))}"',
                           frag)
            xml = xml[:m.start()] + fixed + xml[m.end():]
            n += 1
        parts[name] = new_bytes
        print(f"  {name}: {im_old.size} → {im_new.size}  "
              f"비율 {old_ratio:.3f}→{new_ratio:.3f}, drawing {n}곳 갱신")

    ET.fromstring(xml)
    parts["word/document.xml"] = xml.encode()
    z.close()
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
