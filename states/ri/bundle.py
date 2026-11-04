# Rhode Island General Laws (4 Nov 2026), from the General Assembly's site,
# webserver.rilegislature.gov/Statutes: titles, chapters, one page per section.
# Usage: bundle.py <out dir> [max chapters]
import os, re, sys, urllib.parse
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "lib"))
from statelib import *
out = sys.argv[1]
LIMIT = int(sys.argv[2]) if len(sys.argv) > 2 else 0
SITE = "https://webserver.rilegislature.gov/Statutes/"
def units():
    out = []
    for t in dict.fromkeys(re.findall(r'(?i)href="(TITLE[0-9A-Z.]+/INDEX\.HTM)"', get(SITE))):
        base = SITE + t.rsplit("/", 1)[0] + "/"
        for c in dict.fromkeys(re.findall(r'(?i)href="([0-9A-Z.\-]+/INDEX\.htm)"', get(SITE + t))):
            out.append(base + c)
    return out
chapters = units()
if LIMIT: chapters = chapters[:LIMIT]
items = []
for c in chapters:
    page = get(c)
    head = oneline((re.search(r"(?is)<h2[^>]*>(.*?)</h2>", page) or re.search(r"(?is)<title>(.*?)</title>", page)).group(1))
    base = c.rsplit("/", 1)[0] + "/"
    for s in dict.fromkeys(re.findall(r'(?i)href="([0-9A-Z.\-]+\.htm)"', page)):
        if s.upper() != "INDEX.HTM": items.append((head, base + s))
print(f"Rhode Island: {len(chapters)} chapters, {len(items)} sections", flush=True)
def one(it):
    head, u = it
    page = get(u, allow404=True)
    if not page: return None
    m = re.search(r'(?s)<p[^>]*><b>\s*§(?:&nbsp;|\s)*([0-9A-Z.\-]+?)\.(?:&nbsp;|\s)*(.*?)</b></p>(.*?)(?:<p[^>]*>\s*History of Section|</div>)', page)
    if not m: return None
    return row("RIGL", m.group(1), head, oneline(m.group(2)), clean(re.sub(r"\s+", " ", m.group(3))))
write(pool(one, items, 6, 2000, "sections"), out, "RI", "https://webserver.rilegislature.gov/Statutes/ (Rhode Island General Assembly)")
