# Montana Code Annotated (4 Nov 2026), from the Legislature's site,
# leg.mt.gov/bills/mca: titles, chapters, parts, one page per section.
# Usage: bundle.py <out dir> [max parts]
import os, re, sys, urllib.parse
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "lib"))
from statelib import *
out = sys.argv[1]
LIMIT = int(sys.argv[2]) if len(sys.argv) > 2 else 0
SITE = "https://leg.mt.gov/bills/mca/"
def units():
    out = []
    for t in dict.fromkeys(re.findall(r'href="\./(title_\d+)/chapters_index\.html"', get(SITE + "index.html"))):
        for c in dict.fromkeys(re.findall(r'href="\./(chapter_\d+)/parts_index\.html"', get(f"{SITE}{t}/chapters_index.html"))):
            for p in dict.fromkeys(re.findall(r'href="\./(part_\d+)/sections_index\.html"', get(f"{SITE}{t}/{c}/parts_index.html"))):
                out.append(f"{SITE}{t}/{c}/{p}/")
    return out
chapters = units()
if LIMIT: chapters = chapters[:LIMIT]
items = []
def listp(p):
    page = get(p + "sections_index.html")
    return [[p + s for s in dict.fromkeys(re.findall(r'href="\./(section_\d+/[0-9\-]+\.html)"', page))]]
for x in pool(listp, chapters, 4, 500, "parts"):
    items += x
print(f"Montana: {len(chapters)} parts, {len(items)} sections", flush=True)
def one(u):
    page = get(u, allow404=True)
    if not page: return None
    hdr = re.search(r'(?s)<div class="section-header">(.*?)</div>', page)
    sec = re.search(r'(?s)<span class="citation">\s*([0-9A-Z\-.]+)\s*</span>', page) or re.search(r'(?s)<li class="active"><span title="([0-9A-Z\-.]+)\s', page)
    title = re.search(r'(?s)<h1 class="section-section-title">(.*?)</h1>', page)
    body = re.search(r'(?s)<div class="section-doc"[^>]*>(.*?)<div class="(?:history-doc|section-history)', page) or re.search(r'(?s)<div class="section-doc"[^>]*>(.*?)</div>\s*</div>', page)
    if not sec or not body: return None
    heads = [oneline(x) for x in re.findall(r'(?s)<h[234][^>]*>(.*?)</h[234]>', hdr.group(1))] if hdr else []
    h = re.sub(r"\s+", " ", body.group(1))
    h = re.sub(r'^.*?<span class="citation">[^<]*</span>[^<]*</span>', "", h, count=1)
    text = clean(h)
    return row("MCA", sec.group(1), " > ".join(heads), oneline(title.group(1)) if title else "", text)
write(pool(one, items, 6, 2000, "sections"), out, "MT", "https://leg.mt.gov/bills/mca/ (Montana Legislative Services Division)")
