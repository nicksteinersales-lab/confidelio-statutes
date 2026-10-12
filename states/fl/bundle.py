# Florida Statutes bundle, read chapter by chapter from the Florida Legislature's
# official site, Online Sunshine (www.leg.state.fl.us). Florida publishes no bulk
# download, so this walks the 49 titles, then each chapter's "entire chapter" page,
# one request at a time with a pause between requests.
#
# Usage: python3 states/fl/bundle.py <out dir> [max chapters, for testing]
# One JSON line per section: {"c": "FS", "s": "83.49", "h": heading path, "t": text}.
import datetime, gzip, html, io, json, os, re, sys, time, urllib.request

out = sys.argv[1]
LIMIT = int(sys.argv[2]) if len(sys.argv) > 2 else 0
BASE = "http://www.leg.state.fl.us/statutes/"
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
    s = re.sub(r"</(div|p)>", "\n", s)
    s = html.unescape(TAG.sub(" ", s)).replace(" ", " ").replace(" ", " ")
    s = re.sub(r"[ \t]+", " ", s)
    return re.sub(r"\s*\n\s*", "\n", s).strip()

index = get(BASE + "index.cfm?Mode=View%20Statutes&Submenu=1&Tab=statutes")
year = (re.search(r"The (\d{4}) Florida Statutes", index) or re.search(r"(\d{4}) Florida Statutes", index)).group(1)
titles = list(dict.fromkeys(re.findall(r"Title_Request=([IVXL]+)", index)))

chapters = []  # (title heading, chapter path)
for t in titles:
    page = get(BASE + f"index.cfm?App_mode=Display_Index&Title_Request={t}")
    time.sleep(PAUSE)
    tm = re.search(r'name="Title' + t + r'"></a>.*?TITLE ' + t + r'</a>.*?<td[^>]*>(.*?)</td>', page, re.S)
    tname = f"TITLE {t} {clean(tm.group(1))}".strip() if tm else f"TITLE {t}"
    for path in re.findall(r"URL=(\d{4}-\d{4}/[0-9A-Z]+/[0-9A-Z]+)ContentsIndex\.html", page):
        if path not in [c[1] for c in chapters]:
            chapters.append((tname, path))
if LIMIT:
    chapters = chapters[:LIMIT]
print(f"{year} Florida Statutes: {len(titles)} titles, {len(chapters)} chapters", flush=True)

rows = []
for n, (tname, path) in enumerate(chapters, 1):
    page = get(BASE + f"index.cfm?App_mode=Display_Statute&URL={path}.html")
    time.sleep(PAUSE)
    cnum = re.search(r'class="ChapterNumber">(.*?)</', page, re.S)
    cname = re.search(r'class="ChapterName">(.*?)</', page, re.S)
    chapter = " ".join(clean(x.group(1)) for x in (cnum, cname) if x)
    parts = [(m.start(), clean(m.group(1))) for m in re.finditer(r'<div class="Part">.*?<span[^>]*class="PartTitle">(.*?)</span>', page, re.S)]
    for m in re.finditer(r'<div class="Section">', page):
        start = m.start()
        nxt = page.find('<div class="Section">', start + 10)
        chunk = page[start:nxt if nxt > 0 else len(page)]
        num = re.search(r'class="SectionNumber">(.*?)</span>', chunk, re.S)
        if not num:
            continue
        sec = clean(num.group(1)).rstrip(".")
        cat = re.search(r'class="CatchlineText">(.*?)</span>', chunk, re.S)
        catch = clean(cat.group(1)) if cat else ""
        bm = re.search(r'class="SectionBody">(.*?)(?=<div class="History">|$)', chunk, re.S)
        body = clean(bm.group(1)) if bm else ""
        part = [p for pos, p in parts if pos < start]
        heading = " > ".join([tname, chapter] + part[-1:] + [f"{sec} {catch}".strip()])
        text = f"{sec} {catch}\n{body}".strip()
        if body or catch:
            rows.append({"c": "FS", "s": sec, "h": heading[:600], "t": text})
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
json.dump({"jurisdiction": "FL", "source": BASE + " (Online Sunshine, Florida Legislature)",
           "sourceDate": f"{year} Florida Statutes", "sections": len(rows), "parts": part,
           "built": datetime.date.today().isoformat()}, open(os.path.join(out, "manifest.json"), "w"), indent=1)
print(len(rows), "sections in", part, "parts")
