# Shared helpers for the state bundles (4 Nov 2026): polite fetching, HTML to
# text, a worker pool, and writing the parts + manifest that build-index.mjs
# reads. A bundle imports it with:
#   sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "lib"))
#   from statelib import *
import concurrent.futures as cf, datetime, gzip, html, io, json, os, re, sys, time, urllib.error, urllib.request

UA = "Confidelio statute index (https://confidelio.com)"
_TAG = re.compile(r"<[^>]+>")

def get(url, binary=False, encoding="utf-8", pause=0.25, allow404=False, timeout=180):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                b = r.read()
            time.sleep(pause)
            return b if binary else b.decode(encoding, "replace")
        except urllib.error.HTTPError as e:
            if e.code == 404 and allow404:
                return None
            if e.code in (401, 403):  # refused: never retry past a block
                raise
            if attempt == 4:
                raise
            if e.code == 429:  # the site asked us to slow down: wait as long as it says
                try: wait = min(300, int(e.headers.get("Retry-After", "60")))
                except ValueError: wait = 60
                time.sleep(wait)
                continue
        except Exception:
            if attempt == 4:
                raise
        time.sleep(5 * (attempt + 1))

def clean(s):
    s = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", s)
    s = re.sub(r"(?i)</(p|div|li|h\d|tr|table)>", "\n", s)
    s = re.sub(r"(?i)<br\s*/?>", "\n", s)
    s = html.unescape(_TAG.sub(" ", s)).replace(" ", " ").replace(" ", " ").replace(" ", " ")
    s = re.sub(r"[ \t]+", " ", s)
    return re.sub(r"\s*\n\s*", "\n", s).strip()

def oneline(s):
    return re.sub(r"\s+", " ", clean(s)).strip()

def pool(fn, items, workers=4, every=1000, label="items"):
    out = []
    with cf.ThreadPoolExecutor(workers) as ex:
        for n, r in enumerate(ex.map(fn, items), 1):
            if r:
                out.extend(r if isinstance(r, list) else [r])
            if n % every == 0:
                print(f"{n}/{len(items)} {label}, {len(out)} sections", flush=True)
    return out

def row(code, sec, heading, catch, body):
    sec = str(sec).strip().rstrip(".")
    return {"c": code, "s": sec, "h": " > ".join(x for x in [heading, f"{sec} {catch}".strip()] if x)[:600], "t": f"{sec} {catch}".strip() + (f"\n{body.strip()}" if body and body.strip() else "")}

def write(rows, out, jurisdiction, source, source_date=None):
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
        nonlocal part, raw, buf, g
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
    today = datetime.date.today().isoformat()
    json.dump({"jurisdiction": jurisdiction, "source": source, "sourceDate": source_date or today, "sections": len(rows), "parts": part, "built": today},
              open(os.path.join(out, "manifest.json"), "w"), indent=1)
    print(len(rows), "sections in", part, "parts", flush=True)
