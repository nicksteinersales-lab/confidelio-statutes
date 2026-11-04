# Utah Code (4 Nov 2026), from the Office of Legislative Research and General
# Counsel, le.utah.gov/xcode: the code's version page lists every title's
# current version, and each title is published as one official XML file.
# robots.txt asks for a 10 s crawl delay, so titles are fetched one at a time
# with that pause (about 100 requests). Usage: bundle.py <out dir> [max titles]
import datetime, os, re, sys, xml.etree.ElementTree as ET
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "lib"))
from statelib import *
out = sys.argv[1]
LIMIT = int(sys.argv[2]) if len(sys.argv) > 2 else 0
SITE = "https://le.utah.gov/xcode/"
def units():
    ver = re.search(r'versionDefault="(C_\d+)"', get(SITE + "code.html", pause=10)).group(1)
    return list(dict.fromkeys(re.findall(r'href="(Title[0-9A-Z]+)/[0-9A-Z]+\.html\?v=(C[0-9A-Z]+_\d+)"', get(SITE + ver + ".html", pause=10))))
chapters = units()
if LIMIT: chapters = chapters[:LIMIT]
print(f"Utah: {len(chapters)} titles", flush=True)
TODAY = datetime.date.today()
def mdy(s):
    try:
        m, d, y = (int(x) for x in s.strip().split("/")); return datetime.date(y, m, d)
    except Exception:
        return None
SKIP = {"histories", "catchline", "effdate", "enddate"}
def text(e, out):
    if e.tag in SKIP: return
    if e.tag == "subsection":
        lab = re.findall(r"\([^()]*\)", e.get("number") or "")
        out.append("\n" + (lab[-1] + " " if lab else ""))
    elif e.tag in ("tab",): out.append(" ")
    elif e.tag in ("eol", "center", "right"): out.append("\n")
    if e.text: out.append(e.text)
    for c in e:
        text(c, out)
        if c.tail: out.append(c.tail)
def walk(e, path, rows):
    for c in e:
        if c.tag in ("chapter", "part"):
            cl = c.find("catchline")
            name = ("Chapter " if c.tag == "chapter" else "Part ") + (c.get("number") or "").split("-")[-1]
            walk(c, path + [f"{name} {cl.text or ''}".strip() if cl is not None else name], rows)
        elif c.tag == "section":
            eff, end = c.find("effdate"), c.find("enddate")
            if eff is not None and (mdy(eff.text or "") or TODAY) > TODAY: continue
            if end is not None and (mdy(end.text or "") or TODAY) < TODAY: continue
            cl = c.find("catchline")
            buf = []
            text(c, buf)
            body = re.sub(r"[ \t]+", " ", "".join(buf))
            body = "\n".join(x.strip() for x in body.split("\n") if x.strip())
            body = re.sub(r"(?m)^(\([^()\n]*\))\n", r"\1 ", body)
            rows.append(row("UCA", c.get("number"), " > ".join(path), oneline(cl.text or "") if cl is not None else "", body))
def one(u):
    folder, ver = u
    x = get(f"{SITE}{folder}/{ver}.xml", pause=10, allow404=True)
    if not x: return None
    r = ET.fromstring(x.encode())
    cl = r.find("catchline")
    rows = []
    walk(r, [f"Title {r.get('number')} {cl.text if cl is not None else ''}".strip()], rows)
    return rows
write(pool(one, chapters, 1, 10, "titles"), out, "UT", "https://le.utah.gov/xcode/code.html (Utah Office of Legislative Research and General Counsel)")
