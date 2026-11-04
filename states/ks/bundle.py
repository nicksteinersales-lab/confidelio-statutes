# Kansas Statutes Annotated (4 Nov 2026), from the Revisor of Statutes,
# ksrevisor.gov: the chapter list, each chapter's sections, one page per
# section. Usage: bundle.py <out dir> [max chapters]
import os, re, sys, urllib.parse
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "lib"))
from statelib import *
out = sys.argv[1]
LIMIT = int(sys.argv[2]) if len(sys.argv) > 2 else 0
SITE = "https://ksrevisor.gov"
def units():
    return list(dict.fromkeys(re.findall(r'href="(/statutes/ksa_ch\d+[a-z]?\.html)"', get(SITE + "/ksa.html"))))
chapters = units()
if LIMIT: chapters = chapters[:LIMIT]
items = []
for c in chapters:
    page = get(SITE + c)
    cn = re.search(r"(?s)<title>(.*?)</title>", page)
    for u in dict.fromkeys(re.findall(r'href="(/statutes/chapters/ch\d+[a-z]?/[0-9a-z_]+\.html)"', page)):
        items.append((oneline(cn.group(1)) if cn else c, u))
print(f"Kansas: {len(chapters)} chapters, {len(items)} sections", flush=True)
def one(it):
    head, u = it
    page = get(SITE + u, allow404=True)
    if not page: return None
    m = re.search(r'(?s)<span class="stat_number">\s*([0-9a-z\-]+)\.?\s*</span>\s*<span class="stat_caption">(.*?)</span>(.*?)(?:<p class="ksa_stat_hist"|</div>)', page)
    if not m: return None
    return row("KSA", m.group(1), head, oneline(m.group(2)), clean(m.group(3)))
write(pool(one, items, 6, 2000, "sections"), out, "KS", "https://ksrevisor.gov/ksa.html (Kansas Office of Revisor of Statutes)")
