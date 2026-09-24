# -*- coding: utf-8 -*-
"""gen_figs.py 가 쓴 SVG(상자그림)를 PNG로 굽는다 — Chrome headless 사용.

왜 필요한가
-----------
fig2_forecast.png 등 SVG 원본 그림들의 변환 스크립트가 레포에 없었다(2026-09-24,
fd가 그림 2 글씨를 줄이며 발견 — fig4_slot_data.json에 생성기가 없었던 것과 같은
종류의 구멍). PNG는 있는데 어떻게 만들었는지 재현할 방법이 없어, 이번에 역산해
스크립트로 남긴다.

Chrome headless로 SVG 파일을 그냥 열면 width="215pt" 의 "pt"를 CSS pt(1pt=4/3px)로
읽어 캔버스 한 귀퉁이에 작게 그려진다 — <img>로 감싸 픽셀 크기를 직접 지정해야
viewBox 그대로 꽉 채워진다. 배율(SCALE)은 기존 PNG(fig1·fig2, 둘 다 215pt 단내)의
실측 해상도 1728px을 역산한 값이다 — 폭을 고정하고 높이는 종횡비로 낸다.

실행: ./.venv/bin/python paper/diagram/render_svg.py [svg파일 ...]
      인자 없으면 fig1_architecture·fig2_forecast 둘 다 굽는다.
"""
import os
import re
import subprocess
import sys

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
HERE = os.path.dirname(os.path.abspath(__file__))
TARGET_WIDTH_PX = 1728  # 215pt 단내 기준 실측 역산값(그 외 폭은 비례로 낸다).


def render(svg_path: str) -> str:
    png_path = os.path.splitext(svg_path)[0] + ".png"
    svg = open(svg_path, encoding="utf-8").read()
    m = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', svg)
    if not m:
        raise ValueError(f"viewBox를 못 찾음: {svg_path}")
    w, h = float(m.group(1)), float(m.group(2))
    scale = TARGET_WIDTH_PX / 215.0   # 215pt 단내 실측 기준 배율
    pw, ph = round(w * scale), round(h * scale)

    html_path = os.path.splitext(png_path)[0] + ".render_tmp.html"
    open(html_path, "w", encoding="utf-8").write(
        "<!DOCTYPE html><html><head><meta charset=\"utf-8\"><style>"
        "html,body{margin:0;padding:0}"
        f"img{{display:block;width:{pw}px;height:{ph}px}}"
        f"</style></head><body><img src=\"file://{svg_path}\"></body></html>")
    try:
        subprocess.run(
            [CHROME, "--headless", "--disable-gpu", "--no-sandbox",
             f"--window-size={pw},{ph}", "--force-device-scale-factor=1",
             "--default-background-color=FFFFFFFF",
             f"--screenshot={png_path}", f"file://{html_path}"],
            check=True, capture_output=True, timeout=60)
    finally:
        os.remove(html_path)
    print(f"wrote {png_path}  ({pw}x{ph})")
    return png_path


def main():
    names = sys.argv[1:] or ["fig1_architecture", "fig2_forecast"]
    for name in names:
        svg_path = name if name.endswith(".svg") else os.path.join(HERE, name + ".svg")
        render(svg_path)


if __name__ == "__main__":
    main()
