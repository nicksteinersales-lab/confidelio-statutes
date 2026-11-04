# Massachusetts General Laws bundle (4 Nov 2026), from the General Court's
# official site, malegislature.gov. The site's navigation tree (GetJsTree)
# lists parts, titles and chapters; each chapter page lists its sections; each
# section is its own page. Four requests at a time with a pause.
#
# Usage: python3 states/ma/bundle.py <out dir> [max chapters, for testing]
# One JSON line per section: {"c": chapter e.g. "186", "s": "15B", "h": heading path, "t": text}.
import concurrent.futures as cf, datetime, gzip, html, io, json, os, re, sys, time, urllib.request

out = sys.argv[1]
LIMIT = int(sys.argv[2]) if len(sys.argv) > 2 else 0
SITE = "https://malegislature.gov"
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
    s = re.sub(r"(?i)<br\s*/?>", "\n", s)
    s = html.unescape(TAG.sub(" ", s)).replace("\u00a0", " ")
    s = re.sub(r"[ \t]+", " ", s)
    return re.sub(r"\s*\n\s*", "\n", s).strip()

def tree(key, level):
    return get(f"{SITE}/Laws/GeneralLaws/GetJsTree?nodeKey={key}&level={level}")

def nodes(page, level):
    return re.findall(r'data-nodeKey="(\d+)" data-level="%s"[^>]*>\s*<a[^>]*href\s*=\s*"?([^\s">]+)"?[^>]*>(.*?)</a>' % level, page, re.S)

parts = nodes(get(f"{SITE}/Laws/GeneralLaws/GetJsTree?id=%23"), "Part")
chapters = []  # (path heading, chapter url)
for pkey, purl, pname in parts:
    for tkey, turl, tname in nodes(tree(pkey, "Part"), "Title"):
        time.sleep(PAUSE)
        for ckey, curl, cname in nodes(tree(tkey, "Title"), "Chapter"):
            chapters.append((f"{clean(pname)} > {clean(tname)} > {clean(cname)}".replace("\n", " "), curl))
if LIMIT:
    chapters = chapters[:LIMIT]
print(f"Massachusetts General Laws: {len(parts)} parts, {len(chapters)} chapters", flush=True)

items = []
for path, curl in chapters:
    page = get(SITE + curl)
    time.sleep(PAUSE)
    ch = curl.rsplit("/Chapter", 1)[-1]
    for sec in dict.fromkeys(re.findall(re.escape(curl) + r"/Section([0-9A-Za-z\u00bd.]+)", page)):
        items.append((path, ch, sec, f"{SITE}{curl}/Section{sec}"))
print(f"{len(items)} sections listed", flush=True)

def one(item):
    path, ch, sec, url = item
    try:
        page = get(url)
    except Exception as e:
        print(f"{ch} {sec}: skipped ({e})", flush=True)
        return None
    time.sleep(PAUSE)
    m = re.search(r'(?s)id="skipTo"[^>]*>(.*?)</h2>(.*?)<!--', page)
    if not m:
        return None
    head = clean(m.group(1)).replace("\n", " ")
    catch = head.split(":", 1)[1].strip() if ":" in head else ""
    body = clean(m.group(2))
    return {"c": ch, "s": sec, "h": f"{path} > Section {sec} {catch}"[:600], "t": f"{sec} {catch}\n{body}".strip()}

rows = []
with cf.ThreadPoolExecutor(WORKERS) as ex:
    for n, r in enumerate(ex.map(one, items), 1):
        if r:
            rows.append(r)
        if n % 2000 == 0:
            print(f"{n}/{len(items)} sections", flush=True)

best = {}
for r in rows:
    k = (r["c"], r["s"])
    if k not in best or len(r["t"]) > len(best[k]["t"]):
        best[k] = r
rows = sorted(best.values(), key=lambda r: [int(x) if x.isdigit() else x for x in re.split(r"(\d+)", r["c"] + " " + r["s"])])

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
json.dump({"jurisdiction": "MA", "source": "https://malegislature.gov/Laws/GeneralLaws (Massachusetts General Court)",
           "sourceDate": datetime.date.today().isoformat(), "sections": len(rows), "parts": part,
           "built": datetime.date.today().isoformat()}, open(os.path.join(out, "manifest.json"), "w"), indent=1)
print(len(rows), "sections in", part, "parts")
