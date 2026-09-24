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
import os
import sys
import warnings

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = ["gen_figs_data", "gen_pareto", "gen_routing",
           "gen_comparison", "gen_benchmark", "gen_concurrency"]


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
    if bad:
        print("서체에 없는 글자가 그림에 쓰였다:")
        for b in bad:
            print("  ·", b)
        sys.exit(1)
    print(f"그림 {len(SCRIPTS)}개 — 서체에 없는 글자 없음")


if __name__ == "__main__":
    main()
