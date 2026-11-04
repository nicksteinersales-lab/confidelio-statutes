# Revised Statutes of Missouri bundle (4 Nov 2026), from the Revisor of
# Statutes' official site, revisor.mo.gov. The home page lists every chapter,
# each chapter lists its sections, and each section is its own page. Four
# requests at a time with a pause.
#
# Usage: python3 states/mo/bundle.py <out dir> [max chapters, for testing]
# One JSON line per section: {"c": "RSMO", "s": "535.300", "h": heading path, "t": text}.
import concurrent.futures as cf, datetime, gzip, html, io, json, os, re, sys, time, urllib.request

out = sys.argv[1]
LIMIT = int(sys.argv[2]) if len(sys.argv) > 2 else 0
SITE = "https://revisor.mo.gov/main/"
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

home = get(SITE + "Home.aspx")
chapters = list(dict.fromkeys(re.findall(r"OneChapter\.aspx\?chapter=([0-9A-Z]+)", home)))
if LIMIT:
    chapters = chapters[:LIMIT]
items = []
for ch in chapters:
    page = get(f"{SITE}OneChapter.aspx?chapter={ch}")
    time.sleep(PAUSE)
    tm = re.search(r"<title>(.*?)</title>", page, re.S)
    cname = f"Chapter {ch}"
    hm = re.search(r'(?s)<span class="bold">\s*Chapter\s+%s\b(.*?)</span>' % re.escape(ch), page)
    if hm:
        cname = f"Chapter {ch} {clean(hm.group(1))}".strip()
    for sec in dict.fromkeys(re.findall(r"PageSelect\.aspx\?section=(%s\.[0-9A-Z.]+)&" % re.escape(ch), page)):
        items.append((cname, sec))
print(f"Revised Statutes of Missouri: {len(chapters)} chapters, {len(items)} sections", flush=True)

def one(item):
    cname, sec = item
    try:
        page = get(f"{SITE}OneSection.aspx?section={sec}")
    except Exception as e:
        print(f"{sec}: skipped ({e})", flush=True)
        return None
    time.sleep(PAUSE)
    m = re.search(r'(?s)<div class="norm"[^>]*>(.*?)</div>', page)
    if not m:
        return None
    raw = m.group(1)
    bm = re.search(r'(?s)<span class="bold">(.*?</span>.*?)</span>', raw)
    catch = ""
    if bm:
        catch = re.sub(r"^\s*%s\.\s*" % re.escape(sec), "", clean(bm.group(1))).strip().rstrip("—").strip()
        raw = raw.replace(bm.group(0), "", 1)
    body = clean(raw)
    return {"c": "RSMO", "s": sec, "h": f"{cname} > {sec} {catch}"[:600], "t": f"{sec} {catch}\n{body}".strip()}

rows = []
with cf.ThreadPoolExecutor(WORKERS) as ex:
    for n, r in enumerate(ex.map(one, items), 1):
        if r:
            rows.append(r)
        if n % 2000 == 0:
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
json.dump({"jurisdiction": "MO", "source": "https://revisor.mo.gov (Missouri Revisor of Statutes)",
           "sourceDate": datetime.date.today().isoformat(), "sections": len(rows), "parts": part,
           "built": datetime.date.today().isoformat()}, open(os.path.join(out, "manifest.json"), "w"), indent=1)
print(len(rows), "sections in", part, "parts")
