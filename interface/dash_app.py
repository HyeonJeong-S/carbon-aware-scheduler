"""CAST 통합 대시보드 진입점 (Dash).

실행 (저장소 루트에서, `pip install -e .` 이후):
    cast-dashboard                          → http://localhost:8050
    python -m interface.dash_app --port 8060 --debug

화면 구성과 각 페이지는 interface/dashboard/ 패키지에 있다.
"""

import argparse

from interface.dashboard.app import create_app

app = create_app()
server = app.server  # gunicorn/waitress 용


def main():
    ap = argparse.ArgumentParser(description="CAST 통합 대시보드")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8050)
    ap.add_argument("--debug", action="store_true", help="핫리로드 + 디버그 툴바")
    args = ap.parse_args()
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
