# Code of Maryland (4 Nov 2026), from the General Assembly's site,
# mgaleg.maryland.gov: each statutory article is published as one official
# whole-article PDF (link from the site's GetArticleLink API), read with
# pdftotext and split into sections. Maryland sections have no catchlines.
# Where a section has a future or expiring version ("// EFFECTIVE ..."), the
# version in effect is kept. Usage: bundle.py <out dir> [max articles]
import json, os, re, subprocess, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "lib"))
from statelib import *
out = sys.argv[1]
LIMIT = int(sys.argv[2]) if len(sys.argv) > 2 else 0
SITE = "https://mgaleg.maryland.gov/mgawebsite"
def units():
    return list(dict.fromkeys(re.findall(r'<option value="(g[a-z]{2})">', get(SITE + "/Laws/Statutes"))))
chapters = units()
if LIMIT: chapters = chapters[:LIMIT]
print(f"Maryland: {len(chapters)} articles", flush=True)
SEC = re.compile(r"^§(\d[0-9A-Z.]*[–-][0-9A-Z.–-]*?)\.(?:\s{2,}(\S.*))?$")  # "§8–203." (cross-references are "§ 8–203")
def one(a):
    link = json.loads(get(f"{SITE}/api/Laws/GetArticleLink?articleCode={a}&enactments=false"))
    if not link: return None
    data = get(link, binary=True, allow404=True)
    if not data or not data.startswith(b"%PDF"): return None
    with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
        f.write(data); f.flush()
        txt = subprocess.run(["pdftotext", "-layout", "-enc", "UTF-8", f.name, "-"], capture_output=True).stdout.decode("utf-8", "replace")
    lines = [l.rstrip() for l in txt.replace("\f", "\n").split("\n")]
    lines = [l for l in lines if not re.match(r"^\s*-\s*\d+\s*-\s*$", l)]
    art = next((re.sub(r"^\s*Article\s*-\s*", "", l).strip() for l in lines if l.strip()), a)
    secs, cur = [], None
    for l in lines:
        m = SEC.match(l)
        if m:
            cur = [m.group(1).replace("–", "-"), (m.group(2) or "").strip(), []]
            secs.append(cur)
        elif cur:
            cur[2].append(l.strip())
    rows = []
    for sec, flag, body in secs:
        if flag.startswith("//"):
            continue
        body = re.sub(r"\n{2,}", "\n", "\n".join(body)).strip()
        # join wrapped lines inside a paragraph (pdftotext breaks at the page width)
        body = re.sub(r"\n(?!\(|“)", " ", body)
        p = sec.split("-")
        h = " > ".join([art] + [f"Title {p[0]}"] + ([f"Subtitle {p[1][:-2] or '0'}"] if len(p) > 1 and len(p[1]) > 2 else []))
        rows.append(row(a[1:].upper(), sec, h, "", body))
    return rows
write(pool(one, chapters, 6, 5, "articles"), out, "MD", "https://mgaleg.maryland.gov/mgawebsite/Laws/Statutes (Maryland General Assembly, Department of Legislative Services)")
