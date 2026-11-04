# Idaho Code (4 Nov 2026), from the Idaho Legislature's site,
# legislature.idaho.gov/statutesrules/idstat: titles, chapters, one page per
# section. Usage: bundle.py <out dir> [max chapters]
import os, re, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "lib"))
from statelib import *
out = sys.argv[1]
LIMIT = int(sys.argv[2]) if len(sys.argv) > 2 else 0
SITE = "https://legislature.idaho.gov/statutesrules/idstat/"
def units():
    out = []
    for t in dict.fromkeys(re.findall(r'href="/statutesrules/idstat/(Title[0-9A-Z]+)"', get(SITE))):
        for c in dict.fromkeys(re.findall(r'href="/statutesrules/idstat/%s/(T[0-9A-Z]+CH[0-9A-Z]+)"' % t, get(SITE + t))):
            out.append(f"{SITE}{t}/{c}")
    return out
chapters = units()
if LIMIT: chapters = chapters[:LIMIT]
def listc(c):
    page = get(c, allow404=True) or ""
    return [[c + "/" + s for s in dict.fromkeys(re.findall(r'href="/statutesrules/idstat/[^"]*/(SECT[0-9A-Z\-]+)"', page))]]
items = [s for x in pool(listc, chapters, 4, 200, "chapters") for s in x]
print(f"Idaho: {len(chapters)} chapters, {len(items)} sections", flush=True)
def one(u):
    page = get(u + "/", allow404=True)
    if not page: return None
    page = re.sub(r"\s+", " ", page)
    sec = u.rsplit("SECT", 1)[1]
    m = re.search(r'>%s\.(?:&nbsp;|\s)*(.*?)(?:<span[^>]*>\s*History:|<div class="(?:footer|site-footer))' % re.escape(sec), page)
    if not m: return None
    cm = re.match(r'\s*<span style="text-transform: uppercase">(.*?)</span>(.*)', m.group(1))
    catch, body = (cm.group(1), cm.group(2)) if cm else ("", m.group(1))
    heads = [oneline(x) for x in re.findall(r'<div style="line-height: 12pt; text-align: center[^"]*"><span[^>]*>(.*?)</span></div>', page)[:4]]
    return row("IC", sec, " > ".join(h.title() for h in heads if h), oneline(catch).rstrip("."), clean(body))
write(pool(one, items, 6, 2000, "sections"), out, "ID", "https://legislature.idaho.gov/statutesrules/idstat/ (Idaho Legislature)")
