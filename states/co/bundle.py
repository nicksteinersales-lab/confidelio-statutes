# Colorado Revised Statutes (4 Nov 2026), from the Office of Legislative Legal
# Services' official free download page: one HTML file per title (olls.info),
# split into sections; case annotations are left out. Usage: bundle.py <out dir> [max titles]
import os, re, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "lib"))
from statelib import *
out = sys.argv[1]
LIMIT = int(sys.argv[2]) if len(sys.argv) > 2 else 0
YEAR = "2026"
PAGE = f"https://content.leg.colorado.gov/agencies/office-legislative-legal-services/{YEAR}-crs-titles-download"
def units():
    return list(dict.fromkeys(re.findall(rf"https://olls\.info/crs/crs{YEAR}-title-[0-9.]+\.htm", get(PAGE))))
chapters = units()
if LIMIT: chapters = chapters[:LIMIT]
print(f"Colorado: {len(chapters)} titles", flush=True)
NUM = r"\d+(?:\.\d+)?-\d+(?:\.\d+)?-\d+(?:\.\d+)?"
START = re.compile(rf"(?is)^<p[^>]*text-indent:\.15in[^>]*>\s*<b>\s*<span[^>]*>\s*({NUM})\.\s*</span>\s*</b>(.*)$")
def txt(p):
    return oneline(re.sub(r"(?i)<br\s*/?>", " ", p))
def one(u):
    s = get(u, encoding="cp1252")
    tm = re.search(r"(?is)<title>\s*(Title [0-9.]+ - .*?) - Colorado Revised Statutes", s)
    title = oneline(tm.group(1)) if tm else u
    ps = re.findall(r"(?is)<p[^>]*>.*?</p>", s)
    rows, cur, art, part, skip = [], None, "", "", False
    def done():
        if cur: rows.append(row("CRS", cur[0], " > ".join(x for x in [title, art, part] if x), cur[1], "\n".join(cur[2])))
    for i, p in enumerate(ps):
        t = txt(p)
        if not t: continue
        if "text-align:center" in p and re.match(r"ARTICLE [0-9.]+$", t):
            nxt = txt(ps[i + 1]) if i + 1 < len(ps) else ""
            art, part = f"{t} {nxt}".strip(), ""
            continue
        if "text-align:center" in p and re.match(r"PART [0-9.]+\b", t):
            nxt = txt(ps[i + 1]) if i + 1 < len(ps) else ""
            part = f"{t} {nxt}" if re.match(r"PART [0-9.]+$", t) and nxt.isupper() else t
            continue
        m = START.match(p)
        if m:
            done()
            rest = m.group(2)
            cm = re.search(r"(?is)<b>(.*?)</b>", rest)
            catch = oneline(cm.group(1)) if cm else ""
            body = oneline(rest[cm.end():]) if cm else oneline(rest)
            cur, skip = [m.group(1), catch, [body] if body else []], False
            continue
        if cur is None: continue
        if t == "ANNOTATION": skip = True
        if not skip: cur[2].append(t)
    done()
    return rows
write(pool(one, chapters, 6, 10, "titles"), out, "CO", f"{PAGE} (Colorado Office of Legislative Legal Services, CRS {YEAR})")
