# Vermont Statutes (4 Nov 2026), from the Legislature's site,
# legislature.vermont.gov: titles 1 to 33 (the list is built by script, so the
# numbers are tried), each title's chapters, and the "fullchapter" page with
# every section. Usage: bundle.py <out dir> [max chapters]
import os, re, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "lib"))
from statelib import *
out = sys.argv[1]
LIMIT = int(sys.argv[2]) if len(sys.argv) > 2 else 0
SITE = "https://legislature.vermont.gov"
chapters = []
for n in range(1, 34):
    t = f"{n:02d}"
    page = get(f"{SITE}/statutes/title/{t}", allow404=True)
    if not page: continue
    for c in dict.fromkeys(re.findall(r'href="/statutes/chapter/%s/([0-9A-Za-z]+)"' % t, page)):
        chapters.append((t, c))
if LIMIT: chapters = chapters[:LIMIT]
print(f"Vermont: {len(chapters)} chapters", flush=True)
def one(tc):
    t, c = tc
    page = get(f"{SITE}/statutes/fullchapter/{t}/{c}")
    hm = re.search(r'(?s)<h2[^>]*class="statute-title"[^>]*>(.*?)</h2>', page) or re.search(r"(?s)<title>(.*?)</title>", page)
    head = oneline(hm.group(1)) if hm else f"Title {t} Chapter {c}"
    out = []
    for m in re.finditer(r'(?s)<b>\s*§+\s*([0-9A-Za-z.\-]+)\.\s*(.*?)</b>\s*</p>(.*?)(?=<b>\s*§|\Z)', page):
        body = re.split(r'(?s)</div>\s*</li>', m.group(3))[0]
        out.append(row(str(int(t)) if t.isdigit() else t, m.group(1), head, oneline(m.group(2)), clean(body)))
    return out
write(pool(one, chapters, 4, 200, "chapters"), out, "VT", "https://legislature.vermont.gov/statutes/ (Vermont Office of Legislative Counsel)")
