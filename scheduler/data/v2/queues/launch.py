"""한 줄 = 한 실행. N개 동시. 사용: ./.venv/bin/python scheduler/data/v2/queues/launch.py <list.txt> [N]"""
import shlex, subprocess, sys, re, os, time
from concurrent.futures import ThreadPoolExecutor
ROOT = "/Users/jongha/Desktop/GitHub/carbon-aware-scheduler"
lst, par = sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 6
lines = [l.strip() for l in open(lst) if l.strip() and not l.startswith("#")]
def run(args):
    raw = re.search(r"--name (\S+)", args).group(1)
    name = raw.replace("/", "_")
    if os.path.exists(os.path.join(ROOT, "scheduler/data/v2", raw, "stats.json")):
        print(f"[skip] {name} (이미 있음)", flush=True); return
    log = os.path.join(ROOT, "scheduler/data/v2/logs", name + ".log")
    t0 = time.time()
    with open(log, "w") as f:
        rc = subprocess.call([os.path.join(ROOT, ".venv/bin/python"), "-m", "scheduler.run_v2"] + shlex.split(args),
                             cwd=ROOT, stdout=f, stderr=subprocess.STDOUT)
    last = open(log).read().strip().splitlines()[-1][:170] if os.path.getsize(log) else ""
    print(f"[{rc}] {name} {time.time()-t0:.0f}s | {last}", flush=True)
with ThreadPoolExecutor(max_workers=par) as ex:
    list(ex.map(run, lines))
print("ALL DONE")
