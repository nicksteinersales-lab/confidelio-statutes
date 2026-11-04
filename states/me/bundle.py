# Maine Revised Statutes (4 Nov 2026), from the Revisor of Statutes,
# legislature.maine.gov/statutes: titles, chapters, one page per section.
# Usage: bundle.py <out dir> [max chapters]
import os, re, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "lib"))
from statelib import *
out = sys.argv[1]
LIMIT = int(sys.argv[2]) if len(sys.argv) > 2 else 0
SITE = "https://legislature.maine.gov/statutes/"
def units():
    out = []
    for t in dict.fromkeys(re.findall(r'href="([0-9A-Z\-]+)/title[0-9A-Z\-]+ch0sec0\.html"', get(SITE + "homepage.html"))):
        page = get(f"{SITE}{t}/title{t}ch0sec0.html", allow404=True) or ""
        for c in dict.fromkeys(re.findall(r'href="\./(title[0-9A-Z\-]+ch[0-9A-Z\-]+sec0\.html)"', page)):
            if not c.endswith("ch0sec0.html"): out.append(f"{SITE}{t}/{c}")
    return out
chapters = units()
if LIMIT: chapters = chapters[:LIMIT]
def listc(c):
    page = get(c, allow404=True) or ""
    base = c.rsplit("/", 1)[0] + "/"
    return [[base + s for s in dict.fromkeys(re.findall(r'href="\./(title[0-9A-Z\-]+sec[0-9A-Z\-]+\.html)"', page)) if not s.endswith("sec0.html")]]
items = [s for x in pool(listc, chapters, 4, 200, "chapters") for s in x]
print(f"Maine: {len(chapters)} chapters, {len(items)} sections", flush=True)
def one(u):
    page = get(u, allow404=True)
    if not page: return None
    m = re.search(r'(?s)<h3 class="heading_section">\s*§\s*([0-9A-Z\-]+)\.\s*(.*?)</h3>(.*?)(?:<div class="qhistory|<footer|<div class="footer)', page)
    if not m: return None
    t = re.search(r"/statutes/([0-9A-Z\-]+)/", u).group(1)
    heads = [oneline(x) for x in re.findall(r'(?s)<div class="MRS(?:Title|Part|Chapter|Subchapter) toc">(.*?)</div>', page)]
    body = re.sub(r'(?s)<span class="bhistory">.*?</span>', "", re.sub(r"\s+", " ", m.group(3)))
    return row(t, m.group(1), " > ".join(heads), oneline(m.group(2)), clean(body))
write(pool(one, items, 6, 2000, "sections"), out, "ME", "https://legislature.maine.gov/statutes/ (Maine Revisor of Statutes)")
