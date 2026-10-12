# Revised Code of Washington bundle, from the Washington Legislature's public law
# files (lawfilesext.leg.wa.gov/law/RCW). It holds one HTML file per section, in a
# folder per title and chapter, and the Code Reviser republishes it after each
# session. When the folder dates show the same edition as the published build, the
# last build is reused instead of reading every section again.
#
# Usage: python3 states/wa/bundle.py <out dir> [max chapters, for testing]
# One JSON line per section: {"c": "RCW", "s": "59.18.280", "h": heading path, "t": text}.
import concurrent.futures as cf, datetime, gzip, html, http.client, io, json, os, re, sqlite3, ssl, subprocess, sys, threading, time
import urllib.parse

out = sys.argv[1]
LIMIT = int(sys.argv[2]) if len(sys.argv) > 2 else 0
HOST = "lawfilesext.leg.wa.gov"
ROOT = "/law/RCW/"
WORKERS = 4
UA = {"User-Agent": "Confidelio statute index (https://confidelio.com)"}
CTX = ssl.create_default_context(cafile=os.environ.get("SSL_CERT_FILE") or None)

# One kept-alive connection per worker (tens of thousands of small files).
_local = threading.local()
def get(path):
    for attempt in range(8):
        try:
            c = getattr(_local, "conn", None)
            if c is None:
                proxy = urllib.parse.urlsplit(os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy") or "")
                if proxy.hostname:
                    c = http.client.HTTPSConnection(proxy.hostname, proxy.port or 80, timeout=60, context=CTX)
                    c.set_tunnel(HOST)
                else:
                    c = http.client.HTTPSConnection(HOST, timeout=60, context=CTX)
                _local.conn = c
            c.request("GET", path, headers={**UA, "Connection": "keep-alive"})
            r = c.getresponse()
            body = r.read()
            if r.status != 200:
                raise OSError(f"HTTP {r.status} for {path}")
            return body.decode("utf-8-sig", "replace")
        except Exception:
            try:
                _local.conn.close()
            except Exception:
                pass
            _local.conn = None
            if attempt == 7:
                raise
            time.sleep(min(60, 3 * 2 ** attempt))

LISTING = re.compile(r'(\d{1,2})/(\d{1,2})/(\d{4})\s+[\d:]+\s+[AP]M\s+(?:&lt;dir&gt;|<dir>|\d+)\s*<A HREF="([^"]+)"', re.I)
def listing(path):
    return [(f"{y}-{int(m):02d}-{int(d):02d}", href) for m, d, y, href in LISTING.findall(get(path))]

TAG = re.compile(r"<[^>]+>")
def clean(s):
    s = re.sub(r"(?i)</div>|<br\s*/?>", "\n", s)
    s = html.unescape(TAG.sub("", s)).replace(" ", " ")
    lines = [re.sub(r"[ \t\r]+", " ", l).strip() for l in s.split("\n")]
    return "\n".join(l for l in lines if l)

def field(page, name):
    m = re.search(r"<!-- field: " + name + r" -->(.*?)<!-- field: -->", page, re.S)
    return m.group(1) if m else ""

# The edition: the newest title folder date.
titles = listing(ROOT)
titles = [(d, h) for d, h in titles if h.rstrip("/").endswith("TITLE")]
edition = max(d for d, _ in titles)
source_date = f"RCW as published {edition}"
print("Revised Code of Washington,", source_date, len(titles), "titles", flush=True)

def write_parts(rows):
    os.makedirs(out, exist_ok=True)
    for f in os.listdir(out):
        if f.startswith("part-"):
            os.remove(os.path.join(out, f))
    part, raw, buf = 0, 0, io.BytesIO()
    g = gzip.GzipFile(fileobj=buf, mode="wb", compresslevel=9, mtime=0)
    for r in rows:
        line = (json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n").encode()
        g.write(line)
        raw += len(line)
        if raw > 30_000_000:
            g.close()
            open(os.path.join(out, f"part-{part:02d}.jsonl.gz"), "wb").write(buf.getvalue())
            part, raw, buf = part + 1, 0, io.BytesIO()
            g = gzip.GzipFile(fileobj=buf, mode="wb", compresslevel=9, mtime=0)
    g.close()
    open(os.path.join(out, f"part-{part:02d}.jsonl.gz"), "wb").write(buf.getvalue())
    json.dump({"jurisdiction": "WA", "source": f"https://{HOST}{ROOT} (Washington State Legislature, Code Reviser)",
               "sourceDate": source_date, "sections": len(rows), "parts": part + 1,
               "built": datetime.date.today().isoformat()}, open(os.path.join(out, "manifest.json"), "w"), indent=1)
    print(len(rows), "sections in", part + 1, "parts")

if not LIMIT and os.environ.get("GH_TOKEN"):
    try:
        prev = json.loads(subprocess.run(["gh", "release", "download", "latest", "-p", "wa.json", "-O", "-"],
                                         capture_output=True, check=True).stdout)
        if prev.get("sourceDate") == source_date:
            subprocess.run(["gh", "release", "download", "latest", "-p", "wa.sqlite.gz", "-D", "/tmp/wa-prev", "--clobber"], check=True)
            subprocess.run(["gunzip", "-f", "/tmp/wa-prev/wa.sqlite.gz"], check=True)
            db = sqlite3.connect("/tmp/wa-prev/wa.sqlite")
            rows = [{"c": c, "s": s, "h": h, "t": t} for c, s, h, t in db.execute("SELECT code, sec, head, body FROM sections ORDER BY rowid")]
            print("Edition unchanged since the last build; reusing it.", flush=True)
            write_parts(rows)
            sys.exit(0)
    except Exception as e:
        print("No reusable build (", e, "); reading the edition.", flush=True)

# Titles -> chapter folders -> section files.
def chapters_of(title_href):
    return [h for _, h in listing(title_href) if h.rstrip("/").endswith("CHAPTER")]
with cf.ThreadPoolExecutor(WORKERS) as ex:
    chapter_dirs = [h for hs in ex.map(chapters_of, [h for _, h in titles]) for h in hs]
if LIMIT:
    chapter_dirs = chapter_dirs[:LIMIT]
print(len(chapter_dirs), "chapters", flush=True)

def title_name(title_href):
    inner = [h for _, h in listing(title_href) if h.rstrip("/").endswith("TITLE")]
    if not inner:
        return ""
    files = [h for _, h in listing(inner[0]) if h.endswith(".htm")]
    if not files:
        return ""
    p = get(files[0])
    return f"{clean(field(p, 'Citations'))} {clean(field(p, 'CaptionsTitles'))}".strip()

def chapter(ch_href):
    files = [h for _, h in listing(ch_href) if h.endswith(".htm")]
    head = [h for h in files if h.endswith("CHAPTER.htm")]
    name = ""
    if head:
        p = get(head[0])
        name = f"{clean(field(p, 'Citations'))} {clean(field(p, 'CaptionsTitles'))}".strip()
    secs = []
    for h in files:
        if h.endswith("CHAPTER.htm"):
            continue
        p = get(h)
        sec = re.sub(r"\s+", "", clean(field(p, "Citations")).replace("RCW", ""))
        cap = clean(field(p, "CaptionsTitles")).replace("\n", " ")
        m = re.search(r"<!-- field: Text -->(.*?)<!-- TextEnd -->", p, re.S)
        body = clean(m.group(1)) if m else clean(field(p, "Text"))
        hist = clean(field(p, "History"))
        if not sec or (not body and re.search(r"\b(Repealed|Recodified|Decodified|Expired)\b", cap + " " + hist)):
            continue
        secs.append((sec, cap, body, hist))
    return ch_href, name, secs

title_names = {}
with cf.ThreadPoolExecutor(WORKERS) as ex:
    for (_, h), n in zip(titles, ex.map(title_name, [h for _, h in titles])):
        title_names[h] = n

rows, failed = [], 0
with cf.ThreadPoolExecutor(WORKERS) as ex:
    futs = [ex.submit(chapter, h) for h in chapter_dirs]
    for n, f in enumerate(futs, 1):
        try:
            ch_href, name, secs = f.result()
        except Exception as e:
            failed += 1
            print("chapter failed:", e, flush=True)
            continue
        tname = title_names.get(ch_href.rsplit("/", 2)[0] + "/", "")
        for sec, cap, body, hist in secs:
            heading = " > ".join(x for x in [tname, name, f"RCW {sec} {cap}".strip()] if x)
            text = f"RCW {sec} {cap}\n{body}" + (f"\n[{hist}]" if hist else "")
            rows.append({"c": "RCW", "s": sec, "h": heading[:600], "t": text.strip()})
        if n % 250 == 0:
            print(f"{n}/{len(chapter_dirs)} chapters, {len(rows)} sections", flush=True)
print(failed, "chapters could not be read", flush=True)
if failed > max(5, len(chapter_dirs) // 200):
    sys.exit("Too many chapters failed to download")

seen = set()
rows = [r for r in rows if not (r["s"] in seen or seen.add(r["s"]))]
rows.sort(key=lambda r: [int(x) if x.isdigit() else x for x in re.split(r"(\d+)", r["s"])])
write_parts(rows)
