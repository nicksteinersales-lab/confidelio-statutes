# Nevada Revised Statutes (4 Nov 2026), from the Legislature's site,
# leg.state.nv.us/NRS: one page per chapter with every section.
# Usage: bundle.py <out dir> [max chapters]
import os, re, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "lib"))
from statelib import *
out = sys.argv[1]
LIMIT = int(sys.argv[2]) if len(sys.argv) > 2 else 0
SITE = "https://www.leg.state.nv.us/NRS/"
chapters = sorted(set(re.findall(r'href="(NRS-[0-9A-Z]+\.html)"', get(SITE, encoding="cp1252"))) - {"NRS-000.html"})
if LIMIT: chapters = chapters[:LIMIT]
print(f"Nevada: {len(chapters)} chapters", flush=True)
def one(c):
    page = get(SITE + c, encoding="cp1252")
    head = oneline((re.search(r'(?s)<p class="Chapter">(.*?)</p>', page) or re.search(r"(?s)<title>(.*?)</title>", page)).group(1))
    paras = re.findall(r'(?s)<p class="(SectBody|SourceNote|DocHeading|COHead\d)"[^>]*>(.*?)</p>', page)
    out, cur = [], None
    for cls, p in paras:
        m = re.search(r'(?s)<span\s+class="Section">([0-9A-Z.]+)</span>.*?<span\s+class="Leadline">(.*?)</span>', p)
        if cls == "SectBody" and m:
            if cur: out.append(cur)
            rest = p[m.end():]
            cur = row("NRS", m.group(1), head, oneline(m.group(2)), oneline(rest))
        elif cls == "SectBody" and cur:
            t = oneline(p)
            if t: cur["t"] += "\n" + t
        elif cur and cls != "SourceNote":
            out.append(cur); cur = None
    if cur: out.append(cur)
    return out
write(pool(one, chapters, 4, 200, "chapters"), out, "NV", "https://www.leg.state.nv.us/NRS/ (Nevada Legislative Counsel Bureau)")
