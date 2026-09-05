"""대시보드 공통 스타일 — 색상 팔레트, plotly 레이아웃, 작은 UI 조각."""

import plotly.graph_objects as go
from dash import dash_table, dcc, html

from interface.regions import REGIONS

# ── 색 ──────────────────────────────────────────────────────
INK, MUTED, GRID = "#0b0b0b", "#898781", "#e1e0d9"
BASELINE_GRAY = "#898781"
ACCENT = "#2a78d6"          # 탄소 인지 LB (후)
OURS_GREEN = "#1baf7a"      # time-shift (ours)
SHIFT_GREEN = "#2e7d32"
WARN = "#e08600"
OK = "#2e7d32"
BAD = "#c62828"

# 리전 8색 (표준 코드 순서에 1:1 고정 — 모든 화면에서 같은 리전은 같은 색)
REGION_COLORS = dict(zip(REGIONS, [
    "#1565c0", "#6baed6", "#c62828", "#f4a6a6",
    "#2e7d32", "#81c784", "#ef6c00", "#f9c74f",
]))
BLUE_SEQ = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]

PLOT_LAYOUT = dict(
    font=dict(family="system-ui, -apple-system, 'Segoe UI', sans-serif", color=INK, size=13),
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(l=10, r=10, t=36, b=10),
    hovermode="closest",
)
NO_MODEBAR = {"displayModeBar": False}


def base_fig(**layout):
    """공통 레이아웃이 적용된 빈 Figure."""
    fig = go.Figure()
    fig.update_layout(**PLOT_LAYOUT, **layout)
    fig.update_xaxes(gridcolor=GRID, zeroline=False)
    fig.update_yaxes(gridcolor=GRID, zeroline=False)
    return fig


def empty_fig(message, height=240):
    """데이터가 없을 때 보여줄 안내 Figure."""
    fig = base_fig(height=height)
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    fig.add_annotation(text=message, showarrow=False, font=dict(color=MUTED, size=13))
    return fig


def graph(id_, figure=None, **kw):
    """모드바 없는 dcc.Graph."""
    return dcc.Graph(id=id_, figure=figure if figure is not None else empty_fig(""),
                     config=NO_MODEBAR, **kw)


# ── 작은 UI 조각 ────────────────────────────────────────────
def kpi(label, value, delta=None, tone=None):
    """지표 카드. tone: 'good' | 'bad' | None (delta 색)."""
    color = {"good": OK, "bad": BAD}.get(tone, MUTED)
    return html.Div([
        html.Div(label, className="kpi-label"),
        html.Div(value, className="kpi-value"),
        html.Div(delta, className="kpi-delta", style={"color": color}) if delta else None,
    ], className="kpi")


def kpi_row(*cards):
    return html.Div(list(cards), className="kpi-row")


def section(title, *children, caption=None):
    return html.Div([
        html.H3(title, className="section-title"),
        *children,
        html.Div(caption, className="caption") if caption else None,
    ], className="section")


def caption(text):
    return html.Div(text, className="caption")


def notice(text, kind="info"):
    """kind: info | ok | warn | error"""
    return html.Div(text, className=f"notice notice-{kind}")


def details(summary, *children, open_=False):
    """접었다 펴는 블록."""
    return html.Details([html.Summary(summary),
                         html.Div(list(children), className="details-body")],
                        open=open_, className="details")


def md(text):
    return dcc.Markdown(text, className="md")


def hr():
    return html.Hr(className="hr")


def table(df, page_size=20, height=None, **kw):
    """DataFrame → 가벼운 dash_table."""
    cols = [{"name": str(c), "id": str(c)} for c in df.columns]
    data = df.astype(object).where(df.notna(), None).to_dict("records")
    style_table = {"overflowX": "auto"}
    if height:
        style_table.update({"height": height, "overflowY": "auto"})
    return dash_table.DataTable(
        columns=cols, data=data, page_size=page_size,
        style_table=style_table,
        style_cell={"fontSize": "0.8rem", "padding": "4px 8px", "textAlign": "left",
                    "fontFamily": "inherit", "whiteSpace": "nowrap"},
        style_header={"fontWeight": 700, "backgroundColor": "#f4f4f2",
                      "borderBottom": f"1px solid {GRID}"},
        style_data={"borderBottom": "1px solid #f0f0ee"},
        **kw,
    )


def bar_style(column, max_val, color="#8bc34a", n_bins=20):
    """dash_table 셀 안에 진행바 — 값 구간별 linear-gradient 배경."""
    styles = []
    for i in range(n_bins):
        lo = max_val * i / n_bins
        hi = max_val * (i + 1) / n_bins
        pct = (i + 1) / n_bins * 100
        if i == n_bins - 1:
            cond = f"{{{column}}} >= {lo}"
        else:
            cond = f"{{{column}}} >= {lo} && {{{column}}} < {hi}"
        styles.append({
            "if": {"filter_query": cond, "column_id": column},
            "background": (f"linear-gradient(90deg, {color} 0%, {color} {pct}%, "
                           f"white {pct}%, white 100%)"),
        })
    return styles
