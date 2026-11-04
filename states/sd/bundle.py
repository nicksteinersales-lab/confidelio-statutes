# South Dakota Codified Laws (4 Nov 2026), from the Legislature's own JSON API
# (sdlegislature.gov/api/Statutes/Statute/<id>): each title lists its chapters,
# each chapter its sections, and each section carries its official text.
# Titles are tried by number (1 to 62, with an "A" variant).
# Usage: bundle.py <out dir> [max chapters]
import json, os, re, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "lib"))
from statelib import *
out = sys.argv[1]
LIMIT = int(sys.argv[2]) if len(sys.argv) > 2 else 0
API = "https://sdlegislature.gov/api/Statutes/Statute/"
def j(id_):
    t = get(API + id_, allow404=True, pause=0.15)
    try:
        return json.loads(t) if t else None
    except Exception:
        return None
chapters = []
for n in range(1, 63):
    for t in (str(n), f"{n}A"):
        d = j(t)
        if not d or d.get("Type") != "Title": continue
        tname = f"Title {t} {d.get('CatchLine') or ''}".strip()
        for ch in dict.fromkeys(re.findall(r"Statute=(%s-\d+[A-Z]?)\"" % re.escape(t), d.get("Html") or "")):
            chapters.append((tname, ch))
if LIMIT: chapters = chapters[:LIMIT]
print(f"South Dakota: {len(chapters)} chapters", flush=True)
items = []
def listch(tc):
    tname, ch = tc
    d = j(ch)
    if not d: return []
    cname = f"{tname} > Chapter {ch} {d.get('CatchLine') or ''}".strip()
    return [(cname, s) for s in dict.fromkeys(re.findall(r"Statute=(%s-[0-9A-Z.]+)\"" % re.escape(ch), d.get("Html") or ""))]
for x in pool(lambda tc: [listch(tc)], chapters, 4, 200, "chapters"):
    items += x
print(f"{len(items)} sections listed", flush=True)
def one(item):
    cname, sid = item
    d = j(sid)
    if not d or d.get("Type") != "Section": return None
    text = clean(d.get("Html") or "")
    text = re.sub(r"^\s*%s\s*" % re.escape(sid), "", text)
    catch = (d.get("CatchLine") or "").strip()
    if catch: text = re.sub(r"^[.\s]*" + re.escape(catch.rstrip(". ")) + r"\.?\s*", "", text)
    body = re.split(r"\n\s*Source:", text)[0].strip()
    return row("SDCL", sid, cname, catch, body)
write(pool(one, items, 4, 2000, "sections"), out, "SD", "https://sdlegislature.gov/Statutes (South Dakota Legislative Research Council)")
