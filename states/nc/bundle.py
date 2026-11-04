# North Carolina General Statutes bundle (4 Nov 2026), read chapter by chapter
# from the General Assembly's official site, ncleg.gov. Each chapter's HTML page
# carries the full text of every section, so this walks the table of contents,
# then each chapter, one request at a time with a pause between requests.
#
# Usage: python3 states/nc/bundle.py <out dir> [max chapters, for testing]
# One JSON line per section: {"c": "GS", "s": "42-52", "h": heading path, "t": text}.
import datetime, gzip, html, io, json, os, re, sys, time, urllib.request

out = sys.argv[1]
LIMIT = int(sys.argv[2]) if len(sys.argv) > 2 else 0
SITE = "https://www.ncleg.gov"
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
def text_of(s):
    s = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", s)
    s = re.sub(r"(?i)</(p|div|li|h\d|tr)>", "\n", s)
    s = re.sub(r"(?i)<br\s*/?>", "\n", s)
    s = html.unescape(TAG.sub(" ", s)).replace("\u00a0", " ")
    s = re.sub(r"[ \t]+", " ", s)
    return re.sub(r"\s*\n\s*", "\n", s).strip()

toc = get(SITE + "/Laws/GeneralStatutesTOC")
chapters = list(dict.fromkeys(re.findall(r'href="(/EnactedLegislation/Statutes/HTML/ByChapter/Chapter_[0-9A-Z]+\.html)"', toc)))
if LIMIT:
    chapters = chapters[:LIMIT]
print(f"North Carolina General Statutes: {len(chapters)} chapters", flush=True)

SEC = re.compile(r"^§+\s*(\d+[A-Z]{0,2}-\d+(?:\.\d+)*[A-Z]?)\.\s*(.*)$")
rows = []
for n, path in enumerate(chapters, 1):
    lines = text_of(get(SITE + path)).split("\n")
    time.sleep(PAUSE)
    chapter, article, cur, naming = "", "", None, None
    for ln in lines:
        if naming and not SEC.match(ln) and not re.match(r"^(Chapter|Article|SUBCHAPTER|Part) [0-9A-Z]", ln):
            if naming == "chapter":
                chapter = f"{chapter.rstrip('.')} {ln.strip()}"
            else:
                article = f"{article.rstrip('.')} {ln.strip()}"
            naming = None
            continue
        naming = None
        if re.match(r"^Chapter [0-9A-Z]+\.$", ln):
            chapter, naming = ln.strip(), "chapter"
            continue
        m = SEC.match(ln)
        if m:
            if cur:
                rows.append(cur)
            sec, catch = m.group(1), m.group(2).strip()
            heading = " > ".join(x for x in [chapter, article, f"{sec} {catch}".strip()] if x)
            cur = {"c": "GS", "s": sec, "h": heading[:600], "t": f"{sec} {catch}"}
            continue
        if re.match(r"^(Article|SUBCHAPTER|Part) [0-9A-Z]", ln):
            if cur:
                rows.append(cur); cur = None
            article, naming = ln.strip(), "article"
            continue
        if cur:
            cur["t"] += "\n" + ln
    if cur:
        rows.append(cur)
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
json.dump({"jurisdiction": "NC", "source": "https://www.ncleg.gov/Laws/GeneralStatutesTOC (North Carolina General Assembly)",
           "sourceDate": datetime.date.today().isoformat(), "sections": len(rows), "parts": part,
           "built": datetime.date.today().isoformat()}, open(os.path.join(out, "manifest.json"), "w"), indent=1)
print(len(rows), "sections in", part, "parts")
