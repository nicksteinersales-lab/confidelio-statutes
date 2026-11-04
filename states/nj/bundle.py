# New Jersey Statutes bundle (4 Nov 2026), from the Legislature's official
# plain-text file of the general and permanent statutes (pub.njleg.gov, updated
# every weekday). One download; each section starts on its own line with its
# number, e.g. "46:8-21.1.  Return of security deposit".
#
# Usage: python3 states/nj/bundle.py <out dir>
# One JSON line per section: {"c": "NJSA", "s": "46:8-21.1", "h": heading path, "t": text}.
import datetime, gzip, io, json, os, re, sys, time, urllib.request, zipfile

out = sys.argv[1]
URL = "https://pub.njleg.gov/statutes/STATUTES-TEXT.zip"
req = urllib.request.Request(URL, headers={"User-Agent": "Confidelio statute index (https://confidelio.com)"})
for attempt in range(4):
    try:
        data = urllib.request.urlopen(req, timeout=600).read()
        break
    except Exception:
        if attempt == 3:
            raise
        time.sleep(15)
text = zipfile.ZipFile(io.BytesIO(data)).read("STATUTES.TXT").decode("cp1252", "replace").replace("\r", "")
m = re.search(r"UPDATED THROUGH\s+(.*?)\)", text[:500])
edition = f"{datetime.date.today().isoformat()} (through {m.group(1).strip()})" if m else datetime.date.today().isoformat()
print("New Jersey Statutes,", edition, flush=True)

SEC = re.compile(r"^(\d+[A-Z]{0,2}:\d+[A-Z]{0,2}-\d+[a-z]?\d*(?:\.\d+[a-z]?\d*)*)\.?\s+(\S.*)$")
TITLE = re.compile(r"^TITLE\s+(\d+[A-Z]{0,2})\s+(.*)$")
rows, cur, title = [], None, ""
for ln in text.split("\n"):
    t = TITLE.match(ln)
    if t:
        if cur: rows.append(cur); cur = None
        title = f"Title {t.group(1)} {re.sub(r'\\s+', ' ', t.group(2)).strip().title()}"
        continue
    m = SEC.match(ln)
    if m:
        if cur: rows.append(cur)
        sec, catch = m.group(1), re.sub(r"\s+", " ", m.group(2)).strip()
        cur = {"c": "NJSA", "s": sec, "h": f"{title} > {sec} {catch}"[:600], "t": f"{sec} {catch}"}
    elif cur and ln.strip():
        cur["t"] += "\n" + re.sub(r"[ \t]+", " ", ln).strip()
if cur: rows.append(cur)

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
json.dump({"jurisdiction": "NJ", "source": "https://pub.njleg.gov/statutes/STATUTES-TEXT.zip (New Jersey Legislature, Office of Legislative Services)",
           "sourceDate": edition, "sections": len(rows), "parts": part,
           "built": datetime.date.today().isoformat()}, open(os.path.join(out, "manifest.json"), "w"), indent=1)
print(len(rows), "sections in", part, "parts")
