import json
import re
import sys
from collections import Counter

P = '/Users/jongha/Desktop/GitHub/carbon-aware-scheduler/paper/v2/원고/99_원고.txt'
NUM = re.compile(r'\d+(?:[.,]\d+)?')
CITE = re.compile(r'\[(\d+(?:[–,-]\d+)*)\]')
PROTECT = re.compile(r'^(\[표|\[그림|\[식|#|표 \d+ |그림 \d+ |Table \d+|Fig\. \d+)')

text = open(P, encoding='utf-8').read()
lines = text.split('\n')
before_nums = Counter(NUM.findall(text))
idx = {}
for i, ln in enumerate(lines):
    idx.setdefault(ln, []).append(i)

new_lines = list(lines)
done, bad = 0, []
for path in sys.argv[1:]:
    for e in json.load(open(path, encoding='utf-8')):
        old, new = e['old'].strip(), e['new'].strip()
        hits = idx.get(old, [])
        why = None
        if len(hits) != 1:
            why = f'line matches {len(hits)}'
        elif PROTECT.match(old) or ' | ' in old:
            why = 'protected line'
        elif new and sorted(CITE.findall(old)) != sorted(CITE.findall(new)):
            why = 'citations differ'
        elif new_lines[hits[0]] is None or new_lines[hits[0]] != lines[hits[0]]:
            why = 'line already edited'
        if why:
            bad.append((path.split('/')[-1], why, old[:40]))
            continue
        new_lines[hits[0]] = new if new else None
        done += 1

out = []
for ln in new_lines:
    if ln is None:
        continue
    if ln == '' and out and out[-1] == '':
        continue
    out.append(ln)
result = '\n'.join(out)

for c in set(CITE.findall(text)):
    if c not in CITE.findall(result):
        bad.append(('ALL', 'citation vanished', c))

after_nums = Counter(NUM.findall(result))
lost = sorted(k for k in before_nums if after_nums[k] == 0)
open(P, 'w', encoding='utf-8').write(result)
print('applied', done, 'skipped', len(bad))
for b in bad:
    print('  skip', *b)
print('numbers gone from whole manuscript:', len(lost))
print(' ', ' '.join(lost))
