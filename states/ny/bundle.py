# New York laws bundle (4 Nov 2026), from the New York State Senate's Open
# Legislation API (legislation.nysenate.gov), which serves the official text of
# every consolidated and unconsolidated law from the Legislative Bill Drafting
# Commission. One request per law (full text), with a pause between requests.
# The key comes from the NY_OPENLEG_KEY environment variable (a repo secret).
#
# Usage: python3 states/ny/bundle.py <out dir> [max laws, for testing]
# One JSON line per section: {"c": law id e.g. "RPP", "s": "7-108", "h": heading path, "t": text}.
import datetime, gzip, html, io, json, os, re, sys, time, urllib.parse, urllib.request

out = sys.argv[1]
LIMIT = int(sys.argv[2]) if len(sys.argv) > 2 else 0
KEY = os.environ.get("NY_OPENLEG_KEY", "").strip()
if not KEY:
    sys.exit("NY_OPENLEG_KEY is not set")
API = "https://legislation.nysenate.gov/api/3"
PAUSE = 0.5

def get(path, **params):
    params["key"] = KEY
    url = f"{API}{path}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "Confidelio statute index (https://confidelio.com)"})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except Exception:
            if attempt == 4:
                raise
            time.sleep(10 * (attempt + 1))

laws = []
offset = 1
while True:
    page = get("/laws", limit=1000, offset=offset)
    items = page.get("result", {}).get("items", [])
    laws += items
    total = page.get("total") or page.get("result", {}).get("size") or 0
    if not items or len(laws) >= int(page.get("total", len(laws))):
        break
    offset += len(items)
if LIMIT:
    laws = laws[:LIMIT]
print(f"New York: {len(laws)} laws", flush=True)

def walk(doc, path, law_id, rows):
    t = (doc.get("docType") or "").upper()
    title = (doc.get("title") or "").strip()
    level = f"{t.title()} {doc.get('docLevelId', '')} {title}".strip() if t and t != "SECTION" else ""
    if t == "SECTION":
        sec = str(doc.get("docLevelId") or doc.get("locationId") or "").strip()
        text = (doc.get("text") or "").replace("\\n", "\n").strip()
        if sec and (text or title) and not doc.get("repealed"):
            h = " > ".join([p for p in path if p] + [f"{sec} {title}".strip()])
            rows.append({"c": law_id, "s": sec, "h": h[:600], "t": f"{sec} {title}\n{text}".strip()})
    for child in (doc.get("documents") or {}).get("items") or []:
        walk(child, path + ([level] if level else []), law_id, rows)

rows = []
for n, law in enumerate(laws, 1):
    law_id = law.get("lawId")
    try:
        r = get(f"/laws/{law_id}", full="true").get("result", {})
    except Exception as e:
        print(f"{law_id}: skipped ({e})", flush=True)
        continue
    time.sleep(PAUSE)
    name = (law.get("name") or r.get("info", {}).get("name") or law_id).strip()
    walk(r.get("documents") or {}, [name], law_id, rows)
    if n % 20 == 0:
        print(f"{n}/{len(laws)} laws, {len(rows)} sections", flush=True)

best = {}
for r in rows:
    k = (r["c"], r["s"])
    if k not in best or len(r["t"]) > len(best[k]["t"]):
        best[k] = r
rows = sorted(best.values(), key=lambda r: [r["c"]] + [int(x) if x.isdigit() else x for x in re.split(r"(\d+)", r["s"])])

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
json.dump({"jurisdiction": "NY", "source": "https://legislation.nysenate.gov (New York State Senate Open Legislation API)",
           "sourceDate": datetime.date.today().isoformat(), "sections": len(rows), "parts": part,
           "built": datetime.date.today().isoformat()}, open(os.path.join(out, "manifest.json"), "w"), indent=1)
print(len(rows), "sections in", part, "parts")
