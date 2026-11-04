# Code of Virginia bundle (4 Nov 2026), read chapter by chapter from the
# Division of Legislative Services' official site, law.lis.virginia.gov. The
# "vacodefull" page of each chapter carries the full text of every section, so
# this walks the titles (and subtitles), then each chapter, one request at a
# time with a pause between requests.
#
# Usage: python3 states/va/bundle.py <out dir> [max chapters, for testing]
# One JSON line per section: {"c": "VA", "s": "55.1-1226", "h": heading path, "t": text}.
import datetime, gzip, html, io, json, os, re, sys, time, urllib.request

out = sys.argv[1]
LIMIT = int(sys.argv[2]) if len(sys.argv) > 2 else 0
SITE = "https://law.lis.virginia.gov"
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
    s = re.sub(r"(?i)</(p|div|li|h\d)>", "\n", s)
    s = re.sub(r"(?i)<br\s*/?>", "\n", s)
    s = html.unescape(TAG.sub(" ", s)).replace("\u00a0", " ")
    s = re.sub(r"[ \t]+", " ", s)
    return re.sub(r"\s*\n\s*", "\n", s).strip()

def heading(page, tag="h2"):
    hs = re.findall(r"<%s[^>]*>(.*?)</%s>" % (tag, tag), page, re.S)
    hs = [clean(h) for h in hs if "pg-title" not in h]
    return hs[-1] if hs else ""

root = get(SITE + "/vacode/")
titles = list(dict.fromkeys(re.findall(r"href='(/vacode/title[0-9.A-Z]+/)'", root)))
chapters = []  # (title heading, chapter path)
for t in titles:
    page = get(SITE + t)
    time.sleep(PAUSE)
    tname = re.sub(r"\s*Read Title$", "", heading(page)) or t
    subs = list(dict.fromkeys(re.findall(r"href='(%ssubtitle[0-9A-Z.]+/)'" % re.escape(t), page)))
    pages = [page]
    for sub in subs:
        pages.append(get(SITE + sub)); time.sleep(PAUSE)
    for p in pages:
        for ch in dict.fromkeys(re.findall(r"href='(%s(?:subtitle[0-9A-Z.]+/)?(?:part[0-9A-Z.]+/)?chapter[0-9A-Z.]+/)'" % re.escape(t), p)):
            if ch not in [c[1] for c in chapters]:
                chapters.append((tname, ch))
if LIMIT:
    chapters = chapters[:LIMIT]
print(f"Code of Virginia: {len(titles)} titles, {len(chapters)} chapters", flush=True)

rows = []
for n, (tname, ch) in enumerate(chapters, 1):
    page = get(SITE + ch.replace("/vacode/", "/vacodefull/", 1))
    time.sleep(PAUSE)
    cname = heading(page)
    for m in re.finditer(r"<b>§\s*([0-9.]+:?[0-9.]*-[0-9.:A-Z]+)\.\s*(.*?)</b>\s*<section class='body'>(.*?)</section>", page, re.S):
        sec, catch, body = m.group(1), clean(m.group(2)), clean(m.group(3))
        h = " > ".join(x for x in [tname, cname, f"{sec} {catch}".strip()] if x)
        rows.append({"c": "VA", "s": sec, "h": h[:600], "t": f"{sec} {catch}\n{body}".strip()})
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
json.dump({"jurisdiction": "VA", "source": "https://law.lis.virginia.gov/vacode/ (Virginia Division of Legislative Services)",
           "sourceDate": datetime.date.today().isoformat(), "sections": len(rows), "parts": part,
           "built": datetime.date.today().isoformat()}, open(os.path.join(out, "manifest.json"), "w"), indent=1)
print(len(rows), "sections in", part, "parts")
