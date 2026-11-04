# South Carolina Code of Laws (4 Nov 2026), from the General Assembly's site,
# scstatehouse.gov: the master list of titles, each title's chapters, and one
# page per chapter with every section. Usage: bundle.py <out dir> [max chapters]
import os, re, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "lib"))
from statelib import *
out = sys.argv[1]
LIMIT = int(sys.argv[2]) if len(sys.argv) > 2 else 0
SITE = "https://www.scstatehouse.gov"
titles = list(dict.fromkeys(re.findall(r'href="(/code/title\d+\.php)"', get(SITE + "/code/statmast.php"))))
chapters = []
for t in titles:
    page = get(SITE + t)
    tn = re.search(r"<h1[^>]*>(.*?)</h1>|Title (\d+) - ([^<]*)", page)
    for c in dict.fromkeys(re.findall(r'href="(/code/t\d+c\d+[A-Za-z]?\.php)"', page)):
        chapters.append(c)
if LIMIT: chapters = chapters[:LIMIT]
print(f"South Carolina: {len(titles)} titles, {len(chapters)} chapters", flush=True)
SEC = re.compile(r'(?s)<span style="font-weight: bold;">\s*SECTION\s+([0-9A-Z]+-[0-9A-Z]+-[0-9A-Z.]+)\.</span>\s*(.*?)<br\s*/?>(.*?)(?=<span style="font-weight: bold;">\s*SECTION\s|\Z)')
def one(c):
    page = get(SITE + c)
    head = oneline(" ".join(re.findall(r'<div style="text-align: center;">(.*?)</div>', page)[:4]))
    out = []
    for m in SEC.finditer(page):
        body = re.split(r"(?i)<br\s*/?>\s*HISTORY:", m.group(3))[0]
        out.append(row("SC", m.group(1), head, oneline(m.group(2)), clean(body)))
    return out
write(pool(one, chapters, 4, 200, "chapters"), out, "SC", "https://www.scstatehouse.gov/code/statmast.php (South Carolina Legislative Council)")
