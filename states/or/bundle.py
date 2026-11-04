# Oregon Revised Statutes bundle (4 Nov 2026), from Legislative Counsel's
# official chapter files on oregonlegislature.gov (ors001.html ... ors838.html,
# some with a letter, e.g. ors419b.html). The chapter list is built by script on
# the site, so this tries every chapter number and letter; a missing file is a
# 404. Each file carries every section of the chapter.
#
# Usage: python3 states/or/bundle.py <out dir> [max chapter number, for testing]
# One JSON line per section: {"c": "ORS", "s": "90.300", "h": heading path, "t": text}.
import concurrent.futures as cf, datetime, gzip, html, io, json, os, re, sys, time, urllib.error, urllib.request

out = sys.argv[1]
LIMIT = int(sys.argv[2]) if len(sys.argv) > 2 else 0
BASE = "https://www.oregonlegislature.gov/bills_laws/ors/"
PAUSE = 0.2
WORKERS = 6

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Confidelio statute index (https://confidelio.com)"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                return r.read().decode("cp1252", "replace")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if attempt == 3:
                raise
        except Exception:
            if attempt == 3:
                raise
        time.sleep(5 * (attempt + 1))

def tx(p):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", p)).replace("\u00a0", " ")).strip()

SEC = re.compile(r"^(\d{1,3}[A-Z]?\.\d{3,4}[A-Z]?)\s+(.*)$")

def chapter(name):
    page = get(BASE + name)
    time.sleep(PAUSE)
    if not page:
        return []
    paras = re.findall(r"(?is)<p[^>]*>(.*?)</p>", page)
    heads = [tx(p) for p in paras[:12] if tx(p)]
    cname = next((h for h in heads if h.lower().startswith("chapter ")), name)
    rows, cur, sub = [], None, ""
    for p in paras:
        t = tx(p)
        if not t:
            continue
        bold = re.match(r"(?is)\s*<b>(.*?)</b>", p)
        m = SEC.match(t)
        if bold and m and tx(bold.group(1)).startswith(m.group(1)):
            if cur: rows.append(cur)
            btxt = tx(bold.group(1))
            catch = btxt[len(m.group(1)):].strip()
            body = t[len(btxt):].strip()
            cur = {"c": "ORS", "s": m.group(1), "h": " > ".join(x for x in [cname, sub, f"{m.group(1)} {catch}"] if x)[:600], "t": f"{m.group(1)} {catch}" + (f"\n{body}" if body else "")}
        elif cur:
            if t.isupper() and len(t) < 120 and not re.match(r"^\(", t):
                sub = t.title()
                rows.append(cur); cur = None
            else:
                cur["t"] += "\n" + t
        elif t.isupper() and len(t) < 120:
            sub = t.title()
    if cur: rows.append(cur)
    return rows

top = LIMIT or 838
names = [f"ors{n:03d}{x}.html" for n in range(1, top + 1) for x in ["", "a", "b", "c", "d", "e"]]
rows = []
with cf.ThreadPoolExecutor(WORKERS) as ex:
    for n, got in enumerate(ex.map(chapter, names), 1):
        rows += got
        if n % 600 == 0:
            print(f"{n}/{len(names)} files tried, {len(rows)} sections", flush=True)
print(f"Oregon Revised Statutes: {len(rows)} sections", flush=True)

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
json.dump({"jurisdiction": "OR", "source": "https://www.oregonlegislature.gov/bills_laws/Pages/ORS.aspx (Oregon Legislative Counsel)",
           "sourceDate": datetime.date.today().isoformat(), "sections": len(rows), "parts": part,
           "built": datetime.date.today().isoformat()}, open(os.path.join(out, "manifest.json"), "w"), indent=1)
print(len(rows), "sections in", part, "parts")
