# Wyoming Statutes (4 Nov 2026), from the Legislative Service Office's
# official download page (wyoleg.gov/StateStatutes/StatutesDownload): one PDF
# per title, wyoleg.gov/statutes/compress/TitleNN.pdf, read with pdftotext and
# split into sections. Usage: bundle.py <out dir> [max titles]
import os, re, subprocess, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "lib"))
from statelib import *
out = sys.argv[1]
LIMIT = int(sys.argv[2]) if len(sys.argv) > 2 else 0
SITE = "https://wyoleg.gov/statutes/compress/"
def units():
    # The download page is a script-built app; its list is Title01 to Title42
    # (Title97 and Title99 there are the constitution and an index, not statutes).
    return [f"{n:02d}" for n in range(1, 43)]
chapters = units()
if LIMIT: chapters = chapters[:LIMIT]
print(f"Wyoming: {len(chapters)} titles", flush=True)
def pdf_text(data):
    with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
        f.write(data); f.flush()
        return subprocess.run(["pdftotext", "-layout", "-enc", "UTF-8", f.name, "-"], capture_output=True, check=True).stdout.decode("utf-8", "replace")
SEC = re.compile(r"^\s*(\d+-\d+[A-Z]?-\d+(?:\.\d+)?[a-z]?)\.\s+(\S.*)$")
def one(t):
    data = get(f"{SITE}Title{t}.pdf", binary=True, allow404=True)
    if not data or not data.startswith(b"%PDF"): return None
    lines = [l.rstrip() for l in pdf_text(data).replace("\f", "").split("\n")]
    tnum = str(int(t))
    title, chap, art, rows, cur = f"Title {tnum}", "", "", [], None
    def done():
        if cur:
            paras = []
            for ln in cur[2]:
                if not ln.strip(): continue
                if ln.startswith("   ") or not paras: paras.append(ln.strip())
                else: paras[-1] += " " + ln.strip()
            rows.append(row("WS", cur[0], " > ".join(x for x in [title, chap, art] if x), cur[1], "\n".join(re.sub(r"\s+", " ", x) for x in paras)))
    i = 0
    while i < len(lines):
        ln = lines[i]; i += 1
        st = ln.strip()
        if not st: continue
        if re.match(r"TITLE \d+ - ", st): title = st.title(); continue
        if re.match(r"CHAPTER \d+[A-Z]? - ", st): chap, art = st, ""; continue
        if re.match(r"ARTICLE \d+[A-Z]? - ", st): art = st; continue
        m = SEC.match(ln)
        if m and m.group(1).split("-")[0] == tnum:
            if m.group(2)[:1].isupper() or m.group(2)[:1] == '"':
                done()
                cl = [m.group(2).strip()]
                while not cl[-1].endswith(".") and i < len(lines) and len(cl) < 5 and not lines[i].startswith("     ("):
                    if lines[i].strip(): cl.append(lines[i].strip())
                    i += 1
                cur = [m.group(1), re.sub(r"\s+", " ", " ".join(cl)), []]
                continue
        if cur: cur[2].append(ln)
    done()
    return rows
write(pool(one, chapters, 6, 10, "titles"), out, "WY", "https://wyoleg.gov/StateStatutes/StatutesDownload (Wyoming Legislative Service Office)")
