# Texas statutes bundle, from the Texas Legislative Council's own downloads:
# one zip of chapter HTML files per code, listed in
# https://statutes.capitol.texas.gov/assets/StatuteCodeDownloads.json and served
# from https://tcss.legis.texas.gov/resources/Zips/<CODE>.htm.zip.
#
# Usage: python3 states/tx/bundle.py <out dir>
# One JSON line per section: {"c": code, "s": section, "h": heading path, "t": text}.
# The Constitution (code CN) uses "<article>.<section>", e.g. "1.3a".
import datetime, gzip, html, io, json, os, re, sys, urllib.request, zipfile

out = sys.argv[1]
LIST = "https://statutes.capitol.texas.gov/assets/StatuteCodeDownloads.json"
FILES = "https://tcss.legis.texas.gov/resources"
SKIP = {"SD"}  # Special District Local Laws: thousands of local districts, not used by individuals

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Confidelio statute index (https://confidelio.com)"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                return r.read()
        except Exception:
            if attempt == 2:
                raise

codes = json.loads(get(LIST).decode("utf-8-sig"))["StatuteCode"]
SEC = re.compile(r'<a[^>]*href="[^"]*/Docs/([A-Z0-9]+)/htm/[^"#]*#([^"]+)"[^>]*>(.*?)</a>(.*?)(?=<a[^>]*href="[^"]*/Docs/[A-Z0-9]+/htm/[^"#]*#|<p class="center"|</pre>|$)', re.S)
HEAD = re.compile(r'<p class="center"[^>]*>(.*?)</p>', re.S)
TAG = re.compile(r"<[^>]+>")

def clean(s):
    s = s.replace("</p>", "\n").replace("<br />", "\n")
    s = html.unescape(TAG.sub(" ", s)).replace(" ", " ")
    s = re.sub(r"[ \t]+", " ", s)
    return re.sub(r"\s*\n\s*", "\n", s).strip()

LEVELS = ["TITLE", "SUBTITLE", "CHAPTER", "SUBCHAPTER", "ARTICLE", "PART"]

def hierarchy(heads, pos, codename):
    """The title, chapter and subchapter a section sits under: the latest heading of each
    level before it, dropping lower levels whenever a higher one starts."""
    cur = {}
    for p, h in heads:
        if p >= pos:
            break
        word = h.split(" ", 1)[0].upper()
        if word not in LEVELS or h.upper() == codename.upper():
            continue
        lvl = LEVELS.index(word)
        cur = {k: v for k, v in cur.items() if k < lvl}
        cur[lvl] = h
    return [cur[k] for k in sorted(cur)]

rows, latest = [], None
for c in codes:
    code = c["code"]
    if code in SKIP or not c.get("Html"):
        continue
    z = zipfile.ZipFile(io.BytesIO(get(FILES + c["Html"])))
    n0 = len(rows)
    for info in z.infolist():
        if not info.filename.lower().endswith(".htm"):
            continue
        d = datetime.date(*info.date_time[:3])
        latest = d if latest is None or d > latest else latest
        doc = z.read(info).decode("utf-8-sig", "replace")
        # Headings (title, chapter, subchapter) in order of position, to label each section.
        heads = [(m.start(), clean(m.group(1))) for m in HEAD.finditer(doc)]
        for m in SEC.finditer(doc):
            sec = m.group(2).strip()
            title = clean(m.group(3))
            body = clean(m.group(3) + " " + m.group(4))
            heading = " > ".join(hierarchy(heads, m.start(), c["CodeName"]) + [title])
            if not body:
                continue
            rows.append({"c": code, "s": sec, "h": heading[:600], "t": body})
    print(f"{code} {c['CodeName']}: {len(rows) - n0} sections", flush=True)

# One row per code and section: a section repeated across files (rare) keeps its longest text.
best = {}
for r in rows:
    k = (r["c"], r["s"])
    if k not in best or len(r["t"]) > len(best[k]["t"]):
        best[k] = r
rows = sorted(best.values(), key=lambda r: (r["c"], [int(x) if x.isdigit() else x for x in re.split(r"(\d+)", r["s"])]))

os.makedirs(out, exist_ok=True)
for f in os.listdir(out):
    if f.startswith("part-"):
        os.remove(os.path.join(out, f))
part, raw, buf = 0, 0, io.BytesIO()
g = gzip.GzipFile(fileobj=buf, mode="wb", compresslevel=9, mtime=0)
def flush(last=False):
    global part, raw, buf, g
    g.close()
    with open(os.path.join(out, f"part-{part:02d}.jsonl.gz"), "wb") as fh:
        fh.write(buf.getvalue())
    part, raw = part + 1, 0
    if not last:
        buf = io.BytesIO()
        g = gzip.GzipFile(fileobj=buf, mode="wb", compresslevel=9, mtime=0)
for r in rows:
    line = (json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n").encode()
    g.write(line)
    raw += len(line)
    if raw > 30_000_000:
        flush()
flush(last=True)
json.dump({"jurisdiction": "TX", "source": FILES + "/Zips/ (Texas Legislative Council)",
           "sourceDate": latest.isoformat() if latest else "", "sections": len(rows), "parts": part,
           "built": datetime.date.today().isoformat()}, open(os.path.join(out, "manifest.json"), "w"), indent=1)
print(len(rows), "sections in", part, "parts")
