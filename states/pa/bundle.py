# Pennsylvania Consolidated Statutes (4 Nov 2026), from the General Assembly's
# official site, palegis.us: each title (and the Constitution) is published as
# one whole-title HTML page, split here into sections. The unconsolidated
# statutes (Purdon's "P.S." acts) are not covered. Usage: bundle.py <out dir> [max titles]
import os, re, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "lib"))
from statelib import *
out = sys.argv[1]
LIMIT = int(sys.argv[2]) if len(sys.argv) > 2 else 0
SITE = "https://www.palegis.us/statutes/consolidated"
def units():
    return list(dict.fromkeys(re.findall(r'view-statute\?txtType=HTM&amp;ttl=(\d+)"', get(SITE))))
chapters = units()
if LIMIT: chapters = chapters[:LIMIT]
print(f"Pennsylvania: {len(chapters)} titles", flush=True)
HEAD = re.compile(r"(?s)<b[^>]*>\s*(?:&#167;|§)\s*([0-9A-Za-z][0-9A-Za-z.\-]*?)\.(?:\s|&nbsp;)+(.*?)</b>")
def one(t):
    page = get(f"{SITE}/view-statute?iFrame=true&txtType=HTM&ttl={t}", allow404=True)
    if not page: return None
    tm = re.search(r"(?s)<title>(.*?)</title>", page)
    title = oneline(tm.group(1)).title() if tm else f"Title {t}"
    code = "CONST" if int(t) == 0 else str(int(t))
    parts = re.split(r'<div class="Comment">([^<]*)</div>', page)
    rows, chap, sub = [], "", ""
    for k, chunk in zip(parts[1::2], parts[2::2]):
        if k.endswith("ax"): break  # appendix: supplementary provisions of amendatory acts
        if k.endswith("h"):
            cm = re.findall(r"(?s)<b[^>]*>\s*((?:CHAPTER|ARTICLE|PART|SUBCHAPTER)\s+[0-9A-Z.\-]+)\s*</b>\s*</p>\s*<p[^>]*>(.*?)</p>", chunk)
            for lab, name in cm:
                name = f"{lab.title()} {oneline(name).title()}"
                if lab.startswith("SUBCHAPTER"): sub = name
                else: chap, sub = name, ""
            continue
        if not k.endswith("s"): continue
        m = HEAD.search(chunk)
        if not m: continue
        km = re.match(r"\d+c([0-9A-Za-z.\-]+)s$", k)
        sec = km.group(1) if km else m.group(1)
        if code == "CONST":
            km = re.match(r"\d\dc(\d+)(\d\d)s$", k)
            if not km: continue
            sec = f"{int(km.group(1))}.{m.group(1)}"
        rows.append(row(code, sec, " > ".join(x for x in [title, chap, sub] if x), oneline(m.group(2)), clean(chunk[m.end():])))
    return rows
write(pool(one, chapters, 6, 10, "titles"), out, "PA", "https://www.palegis.us/statutes/consolidated (Pennsylvania General Assembly, Legislative Reference Bureau)")
