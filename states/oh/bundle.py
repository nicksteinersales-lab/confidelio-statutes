# Ohio Revised Code bundle (4 Nov 2026), read chapter by chapter from the Ohio
# Legislative Service Commission's official site, codes.ohio.gov. Each chapter
# page carries the full text of every section in it, so this walks the titles,
# then each chapter, one request at a time with a pause between requests.
#
# Usage: python3 states/oh/bundle.py <out dir> [max chapters, for testing]
# One JSON line per section: {"c": "ORC", "s": "5321.16", "h": heading path, "t": text}.
import datetime, gzip, html, io, json, os, re, sys, time, urllib.request

out = sys.argv[1]
LIMIT = int(sys.argv[2]) if len(sys.argv) > 2 else 0
BASE = "https://codes.ohio.gov/ohio-revised-code"
PAUSE = 0.4

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Confidelio statute index (https://confidelio.com)"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read().decode("utf-8", "replace")
        except Exception:
            if attempt == 3:
                raise
            time.sleep(5 * (attempt + 1))

TAG = re.compile(r"<[^>]+>")
def clean(s):
    s = re.sub(r"</(div|p|li|h\d)>", "\n", s)
    s = re.sub(r"<br\s*/?>", "\n", s)
    s = html.unescape(TAG.sub(" ", s)).replace(" ", " ")
    s = re.sub(r"[ \t]+", " ", s)
    return re.sub(r"\s*\n\s*", "\n", s).strip()

def title_of(page):
    m = re.search(r"<title>(.*?)\|", page, re.S)
    return clean(m.group(1)).replace(" - Ohio Revised Code", "").strip() if m else ""

root = get(BASE)
LINK = r'<a href="{}({}-[0-9A-Z]+)">\s*(\w+ [0-9A-Z]+)\s*<span class=.codes-separator.>\|</span>\s*([^<]*)'
titles = {}
for slug, num, name in re.findall(LINK.format("ohio-revised-code/", "title"), root):
    titles.setdefault(slug, f"{num} {clean(name)}".strip())
chapters = []  # (title heading, chapter slug, chapter heading)
for t, tname in titles.items():
    page = get(f"{BASE}/{t}")
    time.sleep(PAUSE)
    seen = set()
    for ch, num, name in re.findall(LINK.format("", "chapter"), page):
        if ch in seen:
            continue
        seen.add(ch)
        chapters.append((tname, ch, f"{num} {clean(name)}".strip()))
if LIMIT:
    chapters = chapters[:LIMIT]
print(f"Ohio Revised Code: {len(titles)} titles, {len(chapters)} chapters", flush=True)

rows = []
for n, (tname, ch, cname) in enumerate(chapters, 1):
    page = get(f"{BASE}/{ch}")
    time.sleep(PAUSE)
    for m in re.finditer(r'<a href="section-([0-9A-Z.]+)">Section [^<]*?<span class=.codes-separator.>\|</span>\s*(.*?)</a>', page, re.S):
        sec = m.group(1).rstrip(".")
        catch = clean(m.group(2))
        bm = re.search(r'<section class="laws-body">(.*?)</section>', page[m.end():m.end() + 400000], re.S)
        body = clean(bm.group(1)) if bm else ""
        heading = " > ".join([tname, cname, f"{sec} {catch}".strip()])
        if body or catch:
            rows.append({"c": "ORC", "s": sec, "h": heading[:600], "t": f"{sec} {catch}\n{body}".strip()})
    if n % 50 == 0:
        print(f"{n}/{len(chapters)} chapters, {len(rows)} sections", flush=True)

best = {}
for r in rows:
    k = r["s"]
    if k not in best or len(r["t"]) > len(best[k]["t"]):
        best[k] = r
rows = sorted(best.values(), key=lambda r: [int(x) if x.isdigit() else x for x in re.split(r"(\d+)", r["s"])])

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
json.dump({"jurisdiction": "OH", "source": BASE + " (Ohio Legislative Service Commission)",
           "sourceDate": datetime.date.today().isoformat(), "sections": len(rows), "parts": part,
           "built": datetime.date.today().isoformat()}, open(os.path.join(out, "manifest.json"), "w"), indent=1)
print(len(rows), "sections in", part, "parts")
