# -*- coding: utf-8 -*-
"""그림에 쓴 글자 가운데 서체에 없는 것을 찾는다.

그림 서체(Apple SD Gothic Neo)에는 U+2212(−)·⌊·⌈ 가 **없다**. 본문 서체에는
있어서 docx 에서는 멀쩡히 보이므로, 그림 스크립트에 그대로 옮겨 적으면
지면에서만 두부(□)로 찍힌다. 2026-09-24 에 그림 6(−3,108.8 kg)과
그림 7(현지는 −7 h)이 이 문제로 두 번 걸렸다.

matplotlib 은 이럴 때 "Glyph … missing from font" 경고를 낸다. 그림을 모두
다시 그리면서 그 경고를 잡는다.

실행: ./.venv/bin/python paper/diagram/check_glyphs.py
"""
import importlib.util
import io
import os
import re
import sys
import warnings

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = ["gen_figs_data", "gen_pareto", "gen_routing",
           "gen_comparison", "gen_benchmark", "gen_concurrency"]

# ── 원시 SVG 검사 ─────────────────────────────────────────────────
# 2026-09-24(73 지적): 위의 matplotlib 경고 방식은 gen_figs.py 를 전혀 못 잡는다.
# 그 파일은 SVG 문자열을 손으로 쓰므로 matplotlib 을 거치지 않고, 따라서 경고도
# 안 난다 — 그림 1~4 가 검사에서 통째로 빠져 있었다.
#
# 다만 matplotlib 과 SVG 는 대체 규칙이 다르다. matplotlib 은 서체 하나를 잡고
# 없는 글자를 두부로 찍지만, SVG 는 font-family 에 적은 차례대로 **글자마다**
# 넘어간다. 그래서 Apple SD Gothic Neo 하나만 놓고 재면 Ĉ·availᵣ·Rₙ 처럼
# 지면에서 멀쩡히 찍히는 글자까지 전부 걸린다(첫 판이 실제로 그랬다).
# 선언된 차례 전체와 최후의 sans-serif 까지 보고, **어디에도 없을 때만** 알린다.
SVG_FALLBACK = ["Helvetica", "Arial", "Times New Roman"]   # generic sans-serif 자리
SKIP = set(" \t\n\u00a0")


def svg_texts(path):
    """<text> … </text> 안의 글자만. 태그와 속성은 뺀다."""
    raw = io.open(path, encoding="utf-8").read()
    out = []
    for m in re.finditer(r"<text\b[^>]*>(.*?)</text>", raw, re.DOTALL):
        inner = re.sub(r"<[^>]+>", "", m.group(1))
        inner = (inner.replace("&amp;", "&").replace("&lt;", "<")
                      .replace("&gt;", ">").replace("&quot;", '"'))
        if inner.strip():
            out.append(inner)
    return out


def svg_families(path):
    """그 SVG 가 선언한 font-family 차례."""
    raw = io.open(path, encoding="utf-8").read()
    m = re.search(r'font-family="([^"]+)"', raw)
    if not m:
        return []
    return [f.strip().strip("'\"") for f in m.group(1).split(",")]


def _coverage(family, _cache={}):
    """그 이름의 서체가 담은 코드포인트. 없으면 빈 집합."""
    if family in _cache:
        return _cache[family]
    from fontTools.ttLib import TTCollection, TTFont
    import matplotlib.font_manager as fm
    cps = set()
    path = None
    for f in fm.fontManager.ttflist:
        if f.name.lower() == family.lower():
            path = f.fname
            break
    if path and os.path.exists(path):
        try:
            fonts = (TTCollection(path).fonts if path.lower().endswith(".ttc")
                     else [TTFont(path, fontNumber=0)])
            for f in fonts:
                for table in f["cmap"].tables:
                    cps |= set(table.cmap)
        except Exception:
            cps = set()
    _cache[family] = cps
    return cps


def _any_installed_font_with(ch, _scanned=[None]):
    """시스템에 설치된 어느 서체든 이 글자를 담고 있으면 그 이름.

    렌더러(Chrome)는 선언한 차례가 다 떨어지면 시스템 서체 전체로 넘어간다.
    그래서 "선언 차례에 없다"만으로는 두부가 난다고 말할 수 없다 — 실제로
    Rₙ·Ĉ 가 그렇게 멀쩡히 찍힌다. 정말 아무 서체에도 없을 때만 실패로 둔다.
    """
    import matplotlib.font_manager as fm
    if _scanned[0] is None:
        _scanned[0] = sorted({f.fname for f in fm.fontManager.ttflist})
    from fontTools.ttLib import TTCollection, TTFont
    for path in _scanned[0]:
        try:
            fonts = (TTCollection(path).fonts if path.lower().endswith(".ttc")
                     else [TTFont(path, fontNumber=0, lazy=True)])
            for f in fonts:
                for table in f["cmap"].tables:
                    if ord(ch) in table.cmap:
                        return os.path.basename(path)
        except Exception:
            continue
    return None


def check_svgs():
    """(치명, 파일, 글자, 코드포인트, 문구, 대체서체) 목록.

    치명=True  선언 차례에도, 설치된 어느 서체에도 없다 → 지면에서 두부
    치명=False 선언 차례엔 없지만 다른 서체가 대신 찍는다 → 서체가 섞여 보임
    """
    out = []
    for fn in sorted(os.listdir(HERE)):
        if not fn.endswith(".svg"):
            continue
        path = os.path.join(HERE, fn)
        chain = svg_families(path) + SVG_FALLBACK
        covered = set()
        for fam in chain:
            covered |= _coverage(fam)
        if not covered:
            print(f"  ! {fn}: 선언 서체를 하나도 못 찾음 {chain} — 건너뜀")
            continue
        seen = set()
        for line in svg_texts(path):
            for ch in line:
                if ch in SKIP or ord(ch) in covered or (fn, ch) in seen:
                    continue
                seen.add((fn, ch))
                alt = _any_installed_font_with(ch)
                out.append((alt is None, fn, ch, ord(ch), line.strip(), alt))
    return out


def main():
    sys.path.insert(0, os.path.dirname(HERE))
    sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
    bad = []
    for name in SCRIPTS:
        spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, name + ".py"))
        mod = importlib.util.module_from_spec(spec)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            try:
                spec.loader.exec_module(mod)
                # __name__ 이 "__main__" 이 아니라 스크립트의 main() 이 안 돈다.
                # 경고는 savefig 시점에 나오므로 직접 불러야 잡힌다.
                if hasattr(mod, "main"):
                    mod.main()
            except SystemExit:
                pass
            except Exception as e:                     # 그림 생성 실패는 따로 표시
                bad.append(f"{name}: 실행 실패 — {e}")
                continue
        miss = {str(w.message) for w in caught if "missing from font" in str(w.message)}
        for m in sorted(miss):
            bad.append(f"{name}: {m}")
    svg = check_svgs()
    n_svg = len([f for f in os.listdir(HERE) if f.endswith(".svg")])
    fatal = [r for r in svg if r[0]]
    mixed = [r for r in svg if not r[0]]

    if mixed:
        print("선언한 서체엔 없어 다른 서체가 대신 찍는 글자 (두부는 아니지만 서체가 섞인다):")
        for _, fn, ch, cp, line, alt in mixed:
            print(f"  · {fn}: {ch!r} (U+{cp:04X}) ← {alt} — {line[:52]!r}")

    if bad or fatal:
        print("서체에 없는 글자가 그림에 쓰였다:")
        for b in bad:
            print("  ·", b)
        for _, fn, ch, cp, line, _a in fatal:
            print(f"  · {fn}: {ch!r} (U+{cp:04X}) — 어느 서체에도 없음 — {line[:52]!r}")
        sys.exit(1)
    print(f"matplotlib 그림 {len(SCRIPTS)}개 · SVG {n_svg}개 — 두부로 찍힐 글자 없음")


if __name__ == "__main__":
    main()
