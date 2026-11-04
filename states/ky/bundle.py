# Kentucky Revised Statutes (4 Nov 2026), from the Legislative Research
# Commission, apps.legislature.ky.gov: the chapter list, each chapter's (and
# UCC article / subtitle) section list, and one official PDF per section, read
# with pdftotext (repealed and renumbered stubs are taken from the listing
# without fetching their PDFs). Usage: bundle.py <out dir> [max chapters]
import os, re, subprocess, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "lib"))
from statelib import *
out = sys.argv[1]
LIMIT = int(sys.argv[2]) if len(sys.argv) > 2 else 0
SITE = "https://apps.legislature.ky.gov/law/statutes/"
NAMES = {i: oneline(n) for i, n in re.findall(r'href="chapter\.aspx\?id=(\d+)">([^<]*)<', get(SITE))}
PARENT, top = {}, ""
for i, n in NAMES.items():
    if n.upper().startswith("CHAPTER "): top = n
    PARENT[i] = top
def units():
    return [i for i, n in NAMES.items() if re.match(r"(CHAPTER|Chapter|Article|Subtitle|Subchapter) ", n)]
chapters = units()
if LIMIT: chapters = chapters[:LIMIT]
def listing(c):
    page, head, got = get(f"{SITE}chapter.aspx?id={c}"), "", []
    for hd, sid, cat in re.findall(r'(?s)(?:<div class="heading_text">(.*?)</div>)|href="statute\.aspx\?id=(\d+)">(.*?)</a>', page):
        if hd: head = oneline(hd); continue
        num = re.match(r"\s*(\.[0-9A-Za-z\-]+)", cat)
        chap = re.match(r"CHAPTER\s+(\S+)", PARENT.get(c, ""), re.I)
        sec = chap.group(1) + num.group(1) if chap and num else ""
        path = [PARENT.get(c, ""), NAMES.get(c, "")] if PARENT.get(c) != NAMES.get(c) else [NAMES.get(c, "")]
        got.append((" > ".join(x for x in path + [head] if x), sid, oneline(re.sub(r"^\s*\.[0-9A-Za-z\-]+", "", cat)), sec))
    return got
items, seen = [], set()
for it in pool(listing, chapters, 6, 200, "chapters"):
    if it[1] not in seen:
        seen.add(it[1]); items.append(it)
print(f"Kentucky: {len(chapters)} chapters, {len(items)} sections", flush=True)
SEC = re.compile(r"^\s*(\d+[A-Z]?\.\d+[0-9A-Za-z\-]*)\s+(.*)$")
STUB = re.compile(r"^(Repealed|Renumbered|Expired|Recodified|Transferred|Void|Omitted)\b")
def one(it):
    head, sid, catch, lsec = it
    if lsec and STUB.match(catch):  # repealed/renumbered stub: the listing says it all, skip the PDF
        return row("KRS", lsec, head, catch, "")
    data = get(f"{SITE}statute.aspx?id={sid}", binary=True, allow404=True)
    if not data or not data.startswith(b"%PDF"): return None
    with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
        f.write(data); f.flush()
        r = subprocess.run(["pdftotext", "-layout", "-enc", "UTF-8", f.name, "-"], capture_output=True)
    lines = [l.rstrip() for l in r.stdout.decode("utf-8", "replace").replace("\f", "\n").split("\n")]
    lines = [l for l in lines if l.strip() and not re.match(r"^\s*Page \d+ of \d+\s*$", l)]
    if not lines: return None
    m = SEC.match(lines[0])
    if not m: return None
    sec, got, n = m.group(1), m.group(2).strip(), 1
    want = len(re.sub(r"\s+", "", catch))
    while n < len(lines) and len(re.sub(r"\s+", "", got)) < want and not re.match(r"^\s*\(\d+\)", lines[n]):
        got += " " + lines[n].strip(); n += 1
    body = "\n".join(re.sub(r"^\s{2,}", "", l) for l in lines[n:])
    return row("KRS", sec, head, catch or got, re.sub(r"[ \t]{2,}", " ", body))
write(pool(one, items, 6, 2000, "sections"), out, "KY", "https://apps.legislature.ky.gov/law/statutes/ (Kentucky Legislative Research Commission)")
