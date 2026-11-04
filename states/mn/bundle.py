# Minnesota Statutes bundle (4 Nov 2026), from the Office of the Revisor of
# Statutes, revisor.mn.gov. The statutes page lists the parts, each part lists
# its chapters, and each chapter's "full" page carries every section. One
# request at a time with a pause.
#
# Usage: python3 states/mn/bundle.py <out dir> [max chapters, for testing]
# One JSON line per section: {"c": "MS", "s": "504B.178", "h": heading path, "t": text}.
import datetime, gzip, html, io, json, os, re, sys, time, urllib.request

out = sys.argv[1]
LIMIT = int(sys.argv[2]) if len(sys.argv) > 2 else 0
SITE = "https://www.revisor.mn.gov"
PAUSE = 0.3

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Confidelio statute index (https://confidelio.com)"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                return r.read().decode("utf-8", "replace")
        except Exception:
            if attempt == 3:
                raise
            time.sleep(5 * (attempt + 1))

TAG = re.compile(r"<[^>]+>")
def clean(s):
    s = re.sub(r"(?i)</(p|div|li|h\d|tr)>", "\n", s)
    s = re.sub(r"(?i)<br\s*/?>", "\n", s)
    s = re.sub(r'(?is)<a[^>]*class="permalink"[^>]*>.*?</a>', " ", s)
    s = html.unescape(TAG.sub(" ", s)).replace("\u00a0", " ")
    s = re.sub(r"[ \t]+", " ", s)
    return re.sub(r"\s*\n\s*", "\n", s).strip()

root = get(SITE + "/statutes/")
parts = list(dict.fromkeys(re.findall(r'href="(https://www\.revisor\.mn\.gov/statutes/part/[^"]+)"', root)))
chapters = []
for p in parts:
    page = get(p)
    time.sleep(PAUSE)
    for ch in re.findall(r'href="(?:https://www\.revisor\.mn\.gov)?/statutes/cite/([0-9A-Z]+)"', page):
        if ch not in chapters:
            chapters.append(ch)
if LIMIT:
    chapters = chapters[:LIMIT]
print(f"Minnesota Statutes: {len(parts)} parts, {len(chapters)} chapters", flush=True)

rows = []
for n, ch in enumerate(chapters, 1):
    page = get(f"{SITE}/statutes/cite/{ch}/full")
    time.sleep(PAUSE)
    tm = re.search(r'<h1 class="chapter_title">(.*?)</h1>', page, re.S) or re.search(r"<title>(.*?)</title>", page, re.S)
    cname = clean(tm.group(1)) if tm else f"Chapter {ch}"
    starts = [m for m in re.finditer(r'<div class="section" id="stat\.([0-9A-Z.]+)">', page)]
    for i, m in enumerate(starts):
        chunk = page[m.end(): starts[i + 1].start() if i + 1 < len(starts) else len(page)]
        sec = m.group(1)
        hm = re.search(r'<h1 class="shn">(.*?)</h1>', chunk, re.S)
        head_ = clean(hm.group(1)) if hm else sec
        catch = head_[len(sec):].strip() if head_.startswith(sec) else head_
        body = clean(chunk[hm.end():] if hm else chunk)
        body = re.split(r"\n(?:History:|Official Publication of the State of Minnesota)", body)[0]
        rows.append({"c": "MS", "s": sec, "h": f"{cname} > {sec} {catch}"[:600], "t": f"{sec} {catch}\n{body}".strip()})
    if n % 100 == 0:
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
json.dump({"jurisdiction": "MN", "source": "https://www.revisor.mn.gov/statutes/ (Minnesota Office of the Revisor of Statutes)",
           "sourceDate": datetime.date.today().isoformat(), "sections": len(rows), "parts": part,
           "built": datetime.date.today().isoformat()}, open(os.path.join(out, "manifest.json"), "w"), indent=1)
print(len(rows), "sections in", part, "parts")
