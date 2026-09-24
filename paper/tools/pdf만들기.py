"""CAST 작업 문서 → PDF.

  정리.txt / 목차.txt / 공식.txt  : 고정폭 그대로 (표 정렬 보존)
  공식.tex                        : $...$ 를 MathJax 로 조판, % 주석은 설명문으로

한글 고정폭이 시스템에 없어 Nanum Gothic Coding 을 웹폰트로 쓴다.
없으면 Menlo 로 떨어지고 한글만 비례폭이 되어 표가 어긋난다.
"""
import html
import os
import re
import subprocess
import sys

ROOT = '/Users/jongha/Desktop/GitHub/carbon-aware-scheduler/paper'
OUT = os.path.join(ROOT, 'pdf')
CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'

HEAD = """<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>{title}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Nanum+Gothic+Coding:wght@400;700&family=IBM+Plex+Sans+KR:wght@400;500;600&display=swap">
{mathjax}
<style>
@page {{ size: A4; margin: 15mm 14mm 16mm 14mm; }}
* {{ box-sizing: border-box; }}
body {{ margin:0; color:#111; background:#fff;
  font-family:'Nanum Gothic Coding',Menlo,monospace; font-size:8.6pt; line-height:1.52; }}
.cover {{ padding:64mm 0 0; text-align:left; page-break-after:always; }}
.cover h1 {{ font-family:'IBM Plex Sans KR',sans-serif; font-size:26pt; font-weight:600;
  margin:0 0 6mm; letter-spacing:-.01em; }}
.cover .sub {{ font-family:'IBM Plex Sans KR',sans-serif; font-size:10pt; color:#666; line-height:1.8; }}
.cover .rule {{ border:0; border-top:2px solid #111; margin:0 0 8mm; }}
pre {{ margin:0; white-space:pre-wrap; word-break:break-word; font:inherit; }}
.h1 {{ font-family:'IBM Plex Sans KR',sans-serif; font-size:13pt; font-weight:600;
  margin:9mm 0 2mm; padding-bottom:1.5mm; border-bottom:1.5px solid #111;
  page-break-after:avoid; page-break-inside:avoid; }}
.h2 {{ font-family:'IBM Plex Sans KR',sans-serif; font-size:10.5pt; font-weight:600;
  margin:6mm 0 1.5mm; color:#222; page-break-after:avoid; }}
.sep {{ border:0; border-top:1px solid #ccc; margin:2mm 0; }}
.em {{ background:#fff3cf; font-weight:700; }}
.dim {{ color:#888; }}
/* 수식 시트 */
.fx {{ display:grid; grid-template-columns:1fr 14mm; align-items:center; gap:0 3mm;
  margin:4.5mm 0; padding:1mm 0 1mm 4mm; border-left:2px solid #111;
  page-break-inside:avoid; font-size:11pt; }}
.fx .num {{ font-family:'IBM Plex Sans KR',sans-serif; font-size:9pt; color:#555;
  text-align:right; }}
.note {{ font-family:'IBM Plex Sans KR',sans-serif; font-size:8.8pt; color:#555;
  line-height:1.65; margin:2mm 0 1mm; }}
.note.first {{ margin-top:5mm; }}
mjx-container {{ font-size:112% !important; }}
</style></head><body>
<div class="cover"><hr class="rule"><h1>{title}</h1><div class="sub">{sub}</div></div>
"""

MJ = """<script>MathJax={tex:{inlineMath:[['$','$']]},chtml:{scale:1.0},
 options:{renderActions:{addMenu:[0]}}};</script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/mathjax/3.2.2/es5/tex-mml-chtml.js"></script>"""


def render_txt(lines):
    """고정폭 본문. [n] 절 제목과 ==== / ---- 구분선을 스타일로 승격."""
    out, buf = [], []

    def flush():
        if buf:
            out.append('<pre>' + '\n'.join(buf) + '</pre>')
            buf.clear()

    i = 0
    while i < len(lines):
        ln = lines[i]
        s = ln.strip()
        # ==== 로 감싼 제목
        if set(s) == {'='} and len(s) > 20 and i + 1 < len(lines):
            nxt = lines[i + 1].strip()
            if nxt and set(nxt) != {'='}:
                flush()
                out.append(f'<div class="h1">{html.escape(nxt)}</div>')
                i += 2
                if i < len(lines) and set(lines[i].strip()) == {'='}:
                    i += 1
                continue
        # [n] 제목 + 밑줄
        if re.match(r'^\[[\d\-]+\]', s):
            flush()
            out.append(f'<div class="h1">{html.escape(s)}</div>')
            i += 1
            if i < len(lines) and set(lines[i].strip()) in ({'-'}, {'='}):
                i += 1
            continue
        if set(s) in ({'-'}, {'='}) and len(s) > 20:
            flush()
            out.append('<hr class="sep">')
            i += 1
            continue
        # ** 강조 ** 줄
        e = html.escape(ln)
        e = re.sub(r'\*\*(.+?)\*\*', r'<span class="em">\1</span>', e)
        buf.append(e)
        i += 1
    flush()
    return '\n'.join(out)


def render_tex(lines):
    """$...$ 는 수식으로, % 주석은 설명문으로.

    주석 첫 줄의 (1) 또는 R1 을 식 번호로 뽑아 수식 오른쪽에 붙인다.
    학술지 조판과 같은 모양이 된다.
    """
    out, note, num = [], [], ''


    def flush():
        if note:
            txt = '<br>'.join(html.escape(x) for x in note)
            out.append(f'<div class="note{" first" if len(note) > 2 else ""}">{txt}</div>')
            note.clear()

    for ln in lines:
        s = ln.rstrip()
        if s.startswith('$') and s.endswith('$') and len(s) > 2:
            n = num
            flush()
            num = ''
            out.append(f'<div class="fx"><div>{s}</div><div class="num">{n}</div></div>')
        elif s.startswith('%'):
            body = s.lstrip('% ').rstrip()
            if not body or set(body) <= set('═─=-'):
                flush()
                continue
            m = re.match(r'^(\((\d+)\)|R(\d))\s', body + ' ')
            if m and not num:
                num = m.group(1)
            note.append(body)
        elif not s:
            flush()
    flush()
    return '\n'.join(out)


JOBS = [
    ('정리.txt', '정리',     'CAST 논문 진행 정리', '무엇이 정해졌고 왜 그런지 · 근거 · 수치 · 남은 작업'),
    ('목차.txt', '목차',     'CAST 논문 목차',     '각 절에 무엇을 쓸 것인가 · 집필용'),
    ('공식.txt', '공식명세', 'CAST 공식 명세',     '기호 · 규약 · 증명 · 코드와 다르면 이 문서가 기준'),
    ('공식.tex', '수식',     'CAST 수식',          '식 (1)~(15) · Word 수식 개체로 넣을 소스'),
]

os.makedirs(OUT, exist_ok=True)
for fn, stem, title, sub in JOBS:
    src = os.path.join(ROOT, fn)
    if not os.path.exists(src):
        print(f'  없음: {fn}')
        continue
    lines = open(src, encoding='utf-8').read().split('\n')
    is_tex = fn.endswith('.tex')
    body = render_tex(lines) if is_tex else render_txt(lines)
    doc = HEAD.format(title=title, sub=sub, mathjax=MJ if is_tex else '') + body + '</body></html>'
    tmp = f'/tmp/_cast_{fn}.html'
    open(tmp, 'w', encoding='utf-8').write(doc)
    pdf = os.path.join(OUT, stem + '.pdf')
    subprocess.run([CHROME, '--headless', '--disable-gpu', '--no-pdf-header-footer',
                    '--virtual-time-budget=20000', f'--print-to-pdf={pdf}', f'file://{tmp}'],
                   capture_output=True)
    ok = os.path.exists(pdf)
    print(f'  {"OK " if ok else "실패"} {os.path.basename(pdf):14} {os.path.getsize(pdf)/1024:7.0f} KB' if ok
          else f'  실패 {fn}')
