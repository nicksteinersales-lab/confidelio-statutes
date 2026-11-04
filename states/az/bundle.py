# Arizona Revised Statutes bundle (4 Nov 2026), from the Arizona Legislature's
# official site, azleg.gov. Each title's page lists its chapters, articles and
# sections; each section is its own page. Four requests at a time with a pause.
#
# Usage: python3 states/az/bundle.py <out dir> [max titles, for testing]
# One JSON line per section: {"c": "ARS", "s": "33-1321", "h": heading path, "t": text}.
import concurrent.futures as cf, datetime, gzip, html, io, json, os, re, sys, time, urllib.request

out = sys.argv[1]
LIMIT = int(sys.argv[2]) if len(sys.argv) > 2 else 0
SITE = "https://www.azleg.gov"
PAUSE = 0.25
WORKERS = 4

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
    s = re.sub(r"(?i)</(p|div|li|h\d)>", "\n", s)
    s = html.unescape(TAG.sub(" ", s)).replace("\u00a0", " ")
    s = re.sub(r"[ \t]+", " ", s)
    return re.sub(r"\s*\n\s*", "\n", s).strip()

index = get(SITE + "/arstitle/")
titles = list(dict.fromkeys(re.findall(r"arsDetail/?\?title=([0-9A-Z.]+)", index)))
if LIMIT:
    titles = titles[:LIMIT]
items = []  # (heading path, section, url)
for t in titles:
    page = get(f"{SITE}/arsDetail/?title={t}")
    time.sleep(PAUSE)
    tm = re.search(r'<h1 class="topTitle">(.*?)</h1>', page, re.S)
    tname = clean(tm.group(1)) if tm else f"Title {t}"
    chapter, article = "", ""
    for m in re.finditer(r'(<div class="accordion"[^>]*>|<h5[^>]*>(.*?)</h5>)|<a class="one-sixth first"[^>]*>(Article [^<]*)</a><span[^>]*>([^<]*)</span>|href="/viewdocument/\?docName=(https://www\.azleg\.gov/ars/[^"]+\.htm)">([^<]+)</a></li><li class="colright">([^<]*)</li>', page, re.S):
        if m.group(2):
            chapter = " ".join(clean(m.group(2)).split("\n")[:1])
        elif m.group(3):
            article = f"{clean(m.group(3))} {clean(m.group(4))}".strip()
        elif m.group(5):
            items.append((" > ".join(x for x in [tname, chapter, article] if x), clean(m.group(6)), m.group(5), clean(m.group(7))))
print(f"Arizona Revised Statutes: {len(titles)} titles, {len(items)} sections", flush=True)

def one(item):
    path, sec, url, catch = item
    try:
        page = get(url)
    except Exception as e:
        print(f"{sec}: skipped ({e})", flush=True)
        return None
    time.sleep(PAUSE)
    body = re.search(r"(?is)<body[^>]*>(.*)</body>", page)
    text = clean(body.group(1) if body else page)
    lines = text.split("\n")
    if lines and lines[0].startswith(sec):
        lines = lines[1:]
    return {"c": "ARS", "s": sec, "h": f"{path} > {sec} {catch}"[:600], "t": f"{sec} {catch}\n" + "\n".join(lines).strip()}

rows = []
with cf.ThreadPoolExecutor(WORKERS) as ex:
    for n, r in enumerate(ex.map(one, items), 1):
        if r:
            rows.append(r)
        if n % 1000 == 0:
            print(f"{n}/{len(items)} sections", flush=True)

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
json.dump({"jurisdiction": "AZ", "source": "https://www.azleg.gov/arstitle/ (Arizona Legislative Council)",
           "sourceDate": datetime.date.today().isoformat(), "sections": len(rows), "parts": part,
           "built": datetime.date.today().isoformat()}, open(os.path.join(out, "manifest.json"), "w"), indent=1)
print(len(rows), "sections in", part, "parts")
