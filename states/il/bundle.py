# Illinois Compiled Statutes bundle, from the Illinois General Assembly's public file
# repository (ftp.ilga.gov/ILCS), which ILGA names as the place for automated access.
# It holds one HTML file per section, plus chapter, act and article headings, and
# "aReadMe/Section Sequence.txt" gives their order. ILGA refreshes it about once a year,
# so when the edition matches the one already published, the last build is reused
# instead of downloading 80,000 files again.
#
# Usage: python3 states/il/bundle.py <out dir> [max documents, for testing]
# One JSON line per section: {"c": "765/710", "s": "1", "h": heading path, "t": text}.
# The code is chapter/act, so the citation is "765 ILCS 710/1".
import concurrent.futures as cf, datetime, gzip, html, http.client, io, json, os, re, sqlite3, ssl, subprocess, sys, threading, time
import urllib.parse, urllib.request

out = sys.argv[1]
LIMIT = int(sys.argv[2]) if len(sys.argv) > 2 else 0
BASE = "https://ftp.ilga.gov/ILCS/"
WORKERS = 4
UA = {"User-Agent": "Confidelio statute index (https://confidelio.com)"}

# ftp.ilga.gov does not send its intermediate certificate, so add it (it still has to
# chain to a root the system trusts, so this does not weaken verification).
CTX = ssl.create_default_context(cafile=os.environ.get("SSL_CERT_FILE") or None)
der = urllib.request.urlopen("http://crt.sectigo.com/SectigoPublicServerAuthenticationCAOVR40.crt", timeout=60).read()
CTX.load_verify_locations(cadata=ssl.DER_cert_to_PEM_cert(der))

# One kept-alive connection per worker, so 80,000 small files cost a handful of TLS
# handshakes instead of 80,000 (faster, and gentler on ILGA's server).
_local = threading.local()
def get(url):
    u = urllib.parse.urlsplit(url)
    path = u.path + (f"?{u.query}" if u.query else "")
    for attempt in range(8):
        try:
            c = getattr(_local, "conn", None)
            if c is None:
                proxy = urllib.parse.urlsplit(os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy") or "")
                if proxy.hostname:
                    c = http.client.HTTPSConnection(proxy.hostname, proxy.port or 80, timeout=60, context=CTX)
                    c.set_tunnel(u.netloc)
                else:
                    c = http.client.HTTPSConnection(u.netloc, timeout=60, context=CTX)
                _local.conn = c
            c.request("GET", path, headers={**UA, "Connection": "keep-alive"})
            r = c.getresponse()
            body = r.read()
            if r.status != 200:
                raise OSError(f"HTTP {r.status} for {url}")
            return body.decode("utf-8", "replace")
        except Exception:
            try:
                _local.conn.close()
            except Exception:
                pass
            _local.conn = None
            if attempt == 7:
                raise
            time.sleep(min(60, 3 * 2 ** attempt))

readme = get(BASE + "aReadMe/aReadMe.txt")
m = re.search(r"updated on (\d{1,2})/(\d{1,2})/(\d{4}) with all Public Acts through Public Act ([\d-]+)", readme)
if not m:
    sys.exit("Could not read the edition date from aReadMe.txt")
edition = f"{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"
source_date = f"{edition} (through P.A. {m.group(4)})"
print("Illinois Compiled Statutes, edition", source_date, flush=True)

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
    json.dump({"jurisdiction": "IL", "source": BASE + " (Illinois General Assembly file repository)",
               "sourceDate": source_date, "sections": len(rows), "parts": part + 1,
               "built": datetime.date.today().isoformat()}, open(os.path.join(out, "manifest.json"), "w"), indent=1)
    print(len(rows), "sections in", part + 1, "parts")

# Same edition as the published build? Reuse it (only in the weekly job, where gh is set up).
if not LIMIT and os.environ.get("GH_TOKEN"):
    try:
        prev = json.loads(subprocess.run(["gh", "release", "download", "latest", "-p", "il.json", "-O", "-"],
                                         capture_output=True, check=True).stdout)
        if prev.get("sourceDate") == source_date:
            subprocess.run(["gh", "release", "download", "latest", "-p", "il.sqlite.gz", "-D", "/tmp/il-prev", "--clobber"], check=True)
            subprocess.run(["gunzip", "-f", "/tmp/il-prev/il.sqlite.gz"], check=True)
            db = sqlite3.connect("/tmp/il-prev/il.sqlite")
            rows = [{"c": c, "s": s, "h": h, "t": t} for c, s, h, t in db.execute("SELECT code, sec, head, body FROM sections ORDER BY rowid")]
            print("Edition unchanged since the last build; reusing it.", flush=True)
            write_parts(rows)
            sys.exit(0)
    except Exception as e:
        print("No reusable build (", e, "); downloading the edition.", flush=True)

seq = [l.strip() for l in get(BASE + "aReadMe/Section%20Sequence.txt").splitlines()]
docs = [d for d in seq if re.match(r"^\d{9}[AFHK]", d)]
if LIMIT:
    docs = docs[:LIMIT]
print(len(docs), "documents", flush=True)

def url(d):
    return BASE + urllib.parse.quote(f"Ch {d[:4]}/Act {d[4:8]}/{d}.html")

TAG = re.compile(r"<[^>]+>")
def text(page):
    s = re.sub(r"\s+", " ", page)
    s = re.sub(r"(?i)<br\s*/?>|</p>", "\n", s)
    s = html.unescape(TAG.sub("", s)).replace("\u00a0", " ")
    lines = [re.sub(r"[ \t\r]+", " ", l).strip() for l in s.split("\n")]
    return "\n".join(l for l in lines if l)

def catchline(page):
    # ILGA puts "Sec. 1. " and the catchline ("Statement of damage. ") in separate
    # <font> runs; a long run after the number is the text itself (no catchline).
    runs = [html.unescape(TAG.sub("", r)).replace("\u00a0", " ").strip() for r in re.findall(r"<font[^>]*>(.*?)</font>", page, re.S)]
    runs = [r for r in runs if r]
    for i, r in enumerate(runs[:-1]):
        if re.fullmatch(r"Sec\. [^ ]+\.?", r):
            nxt = re.sub(r"\s+", " ", runs[i + 1])
            return nxt.rstrip(".").strip() if 0 < len(nxt) <= 160 and nxt.endswith(".") else ""
    return ""

def fetch(d):
    try:
        page = get(url(d))
        return d, (text(page), catchline(page) if d[9] == "K" else "")
    except Exception:
        return d, None

pages = {}
with cf.ThreadPoolExecutor(WORKERS) as ex:
    for n, (d, got) in enumerate(ex.map(fetch, docs), 1):
        pages[d] = got
        if n % 5000 == 0:
            print(f"{n}/{len(docs)}", flush=True)
missing = [d for d, got in pages.items() if got is None]
print(len(missing), "documents could not be read", flush=True)
if len(missing) > max(50, len(docs) // 200):
    sys.exit("Too many documents failed to download")

def act_num(d):
    a = int(d[4:9])
    return str(a // 10) + (f".{a % 10}" if a % 10 else "")

rows, chapter, act, article = [], "", "", ""
for d in docs:
    got = pages.get(d)
    if not got:
        continue
    t, catch = got
    kind = d[9]
    if kind == "A":
        chapter, act, article = " ".join(t.split("\n")[:2]), "", ""
    elif kind == "F":
        st = re.search(r"Short title:\s*(.+)", t)
        name = st.group(1) if st else (re.search(r"\(\d+ ILCS [^)]*\)\s*\((.+?)\)", t) or [None, ""])[1]
        act, article = f"{name.strip().rstrip('.')} ({int(d[:4])} ILCS {act_num(d)})".strip(), ""
    elif kind == "H":
        article = " ".join(t.split("\n")[:3])[:200]
    else:
        sec = d[10:]
        body = re.sub(r"^\(\d+ ILCS [^)]*\)[^\n]*\n", "", t)
        if re.match(r"^Sec\. [^ ]+\.? ?\(Repealed\)", body) or not body:
            continue
        heading = " > ".join(x for x in [chapter, act, article, f"Sec. {sec} {catch}".strip()] if x)
        rows.append({"c": f"{int(d[:4])}/{act_num(d)}", "s": sec, "h": heading[:600], "t": body})

# A section can appear in more than one version (e.g. before and after an amendment
# takes effect); both are kept in one file by ILGA, so keys are already unique.
seen = set()
rows = [r for r in rows if not ((r["c"], r["s"]) in seen or seen.add((r["c"], r["s"])))]
write_parts(rows)
