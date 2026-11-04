# Alaska Statutes (4 Nov 2026), from the Legislature's BASIS site,
# akleg.gov/basis/statutes.asp: the title list, then each whole title from the
# site's own print view (one request per title), split into sections.
# Usage: bundle.py <out dir> [max titles]
import os, re, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "lib"))
from statelib import *
out = sys.argv[1]
LIMIT = int(sys.argv[2]) if len(sys.argv) > 2 else 0
SITE = "https://www.akleg.gov/basis/statutes.asp"
def units():
    return [f"{int(n):02d}" for n in dict.fromkeys(re.findall(r'loadTOC\(\s*(\d+)\);', get(SITE, encoding="cp1252")))]
chapters = units()
if LIMIT: chapters = chapters[:LIMIT]
print(f"Alaska: {len(chapters)} titles", flush=True)
TOK = re.compile(r'(?is)<h5>(.*?)</h5>|<h6>(.*?)</h6>|<h7>(.*?)</h7>|<a name="(\d+\.\d+\.\d+)">\s*</a>')
def one(t):
    s = get(f"{SITE}?media=print&secStart={t}&secEnd={t}", encoding="cp1252")
    s = re.sub(r"(?i)(<p>\s*)+", "<p>", s)
    tm = re.search(r"(?is)Title \d+\.\s*[^<]*", s)
    title = oneline(tm.group(0)).rstrip(".") if tm else f"Title {int(t)}"
    chap, art, rows, toks = "", "", [], list(TOK.finditer(s))
    for k, m in enumerate(toks):
        if m.group(1): title = oneline(m.group(1)).rstrip(".") or title
        elif m.group(2): chap = oneline(m.group(2)).rstrip(".")
        elif m.group(3): art = oneline(m.group(3)).rstrip(".")
        else:
            end = toks[k + 1].start() if k + 1 < len(toks) else len(s)
            seg = s[m.end():end]
            hm = re.match(r"(?is)\s*Secs?\.\s*[0-9.]+(?:\s*(?:\x97|&mdash;|—|-)\s*[0-9.]+)?\.?\s*(.*?)<BR>\s*</b>", seg)
            catch = oneline(hm.group(1)) if hm else ""
            body = seg[hm.end():] if hm else seg
            body = re.sub(r"(?is)<b>\s*$", "", body.strip())
            body = re.sub(r"(?i)&nbsp;", " ", body)
            rows.append(row("AS", m.group(4), " > ".join(x for x in [title, chap, art] if x), catch, clean(body)))
            if art and k + 1 < len(toks) and toks[k + 1].group(2): art = ""
    return rows
write(pool(one, chapters, 6, 10, "titles"), out, "AK", SITE + " (Alaska State Legislature)")
