# Nebraska Revised Statutes (4 Nov 2026), from the Legislature's site,
# nebraskalegislature.gov/laws: each chapter's section list, one page per
# section. Usage: bundle.py <out dir> [max chapters]
import os, re, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "lib"))
from statelib import *
out = sys.argv[1]
LIMIT = int(sys.argv[2]) if len(sys.argv) > 2 else 0
SITE = "https://nebraskalegislature.gov"
def units():
    return [str(n) for n in range(1, 91)]
chapters = units()
if LIMIT: chapters = chapters[:LIMIT]
def listc(c):
    page = get(f"{SITE}/laws/browse-chapters.php?chapter={c}", allow404=True) or ""
    return [[s for s in dict.fromkeys(re.findall(r'href="/laws/statutes\.php\?statute=([0-9A-Za-z.,\-]+)"', page))]]
items = [s for x in pool(listc, chapters, 4, 100, "chapters") for s in x]
print(f"Nebraska: {len(chapters)} chapters, {len(items)} sections", flush=True)
def one(s):
    page = get(f"{SITE}/laws/statutes.php?statute={s}", allow404=True)
    if not page: return None
    m = re.search(r'(?s)<div class="statute">\s*<h2>\s*([0-9A-Za-z.,\-]+?)\.?\s*</h2>\s*<h3>(.*?)</h3>(.*?)(?:<div class="statute_source">|<div>\s*<h2>)', page)
    if not m: return None
    return row("NEB", m.group(1), "Chapter " + m.group(1).split("-")[0], oneline(m.group(2)), clean(re.sub(r"\s+", " ", m.group(3))))
write(pool(one, items, 6, 2000, "sections"), out, "NE", "https://nebraskalegislature.gov/laws/laws.php (Nebraska Legislature)")
