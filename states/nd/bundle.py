# North Dakota Century Code (4 Nov 2026), from the Legislative Branch site,
# ndlegis.gov: the code index lists every chapter's official PDF and its
# sections; each chapter PDF is read with pdftotext and split into sections.
# Usage: bundle.py <out dir> [max chapters]
import html as H, os, re, subprocess, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "lib"))
from statelib import *
out = sys.argv[1]
LIMIT = int(sys.argv[2]) if len(sys.argv) > 2 else 0
SITE = "https://ndlegis.gov"
INDEX = SITE + "/general-information/north-dakota-century-code/index.html"
def units():
    return list(dict.fromkeys(re.findall(r'href="/cencode/(t[0-9a-z\-]+\.pdf)', get(INDEX))))
chapters = units()
if LIMIT: chapters = chapters[:LIMIT]
# Title and chapter names, and the known sections, from the index.
info, title, chap = {}, "", ""
for m in re.finditer(r'<h2>(Title [^<]*)</h2>|<h3>(Chapter [^<]*)</h3>|href="/cencode/(t[0-9a-z\-]+\.pdf)(?:#nameddest=[^"]*)?">([^<]*)</a>', get(INDEX)):
    if m.group(1): title, chap = oneline(m.group(1)), ""
    elif m.group(2): chap = oneline(m.group(2))
    else:
        d = info.setdefault(m.group(3), [title, chap, set()])
        if re.match(r"\d", m.group(4).strip()): d[2].add(m.group(4).strip())
print(f"North Dakota: {len(chapters)} chapter files", flush=True)
def pdf_text(data):
    with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
        f.write(data); f.flush()
        return subprocess.run(["pdftotext", "-layout", "-enc", "UTF-8", f.name, "-"], capture_output=True, check=True).stdout.decode("utf-8", "replace")
SEC = re.compile(r"^\s*(\d+(?:\.\d+)?-\d+(?:\.\d+)?-\d+(?:\.\d+)*)\.\s+(\S.*)$")
MARK = re.compile(r"^(\d+|[a-z]{1,4}|\([a-z0-9]+\))\.\s")
def one(f):
    data = get(f"{SITE}/cencode/{f}", binary=True, allow404=True)
    if not data or not data.startswith(b"%PDF"): return None
    tname, cname, known = info.get(f, ["", "", set()])
    lines = [l.rstrip() for l in pdf_text(data).replace("\f", "\n").split("\n")]
    lines = [l for l in lines if not re.match(r"^\s*Page No\. \d+\s*$", l)]
    rows, cur = [], None
    def done():
        if not cur: return
        paras = []
        for ln in cur[2]:
            st = ln.strip()
            if not st: continue
            if not paras or (ln.startswith("   ") and (MARK.match(st) or paras[-1][-1:] in ".:;")): paras.append(st)
            else: paras[-1] += " " + st
        rows.append(row("NDCC", cur[0], " > ".join(x for x in [tname, cname] if x), cur[1], "\n".join(paras)))
    i = 0
    while i < len(lines):
        ln = lines[i]; i += 1
        m = SEC.match(ln)
        if m and (m.group(1) in known or (not known and ln.startswith(" ") and m.group(2)[:1].isupper())):
            done()
            cl = [m.group(2).strip()]
            while not cl[-1].endswith(".") and i < len(lines) and len(cl) < 4 and lines[i].strip():
                cl.append(lines[i].strip()); i += 1
            cur = [m.group(1), " ".join(cl), []]
            continue
        if cur: cur[2].append(ln)
    done()
    return rows
write(pool(one, chapters, 6, 200, "chapters"), out, "ND", INDEX + " (North Dakota Legislative Branch)")
