# Michigan Compiled Laws bundle (4 Nov 2026), from the Michigan Legislature's
# official site, legislature.mi.gov. The chapter index lists each chapter, each
# chapter lists its acts, and every act is published as one official PDF with
# the full text of its sections. This walks them one request at a time with a
# pause, and splits each act's text into sections.
#
# Usage: python3 states/mi/bundle.py <out dir> [max chapters, for testing]
# One JSON line per section: {"c": "MCL", "s": "554.613", "h": heading path, "t": text}.
import datetime, gzip, html, io, json, os, re, subprocess, sys, tempfile, time, urllib.request

out = sys.argv[1]
LIMIT = int(sys.argv[2]) if len(sys.argv) > 2 else 0
SITE = "https://www.legislature.mi.gov"
PAUSE = 0.25

def get(url, binary=False):
    req = urllib.request.Request(url, headers={"User-Agent": "Confidelio statute index (https://confidelio.com)"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                b = r.read()
                return b if binary else b.decode("utf-8", "replace")
        except Exception:
            if attempt == 3:
                raise
            time.sleep(5 * (attempt + 1))

def pdf_text(data):
    with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
        f.write(data); f.flush()
        return subprocess.run(["pdftotext", "-enc", "UTF-8", f.name, "-"], capture_output=True, check=True).stdout.decode("utf-8", "replace")

FOOT = re.compile(r"^(Michigan Compiled Laws Complete Through.*|Rendered .*Page \d+ of \d+.*|Page \d+ of \d+|Courtesy of legislature\.mi\.gov|Rendered .*)$")
SEC = re.compile(r"^(\d{1,3}[A-Za-z]?\.\d+[a-z0-9]*)\s+(.+)$")

index = get(SITE + "/Laws/ChapterIndex")
chapters = list(dict.fromkeys(re.findall(r"objectName=(mcl-chap[0-9A-Za-z]+)", index)))
if LIMIT:
    chapters = chapters[:LIMIT]
acts = []  # (chapter heading, act object name)
for ch in chapters:
    page = get(f"{SITE}/Home/GetObject?objectName={ch}")
    time.sleep(PAUSE)
    t = re.search(r"<title>(.*?)</title>", page, re.S)
    cname = html.unescape(re.sub(r"\s+", " ", t.group(1))).replace(" - Michigan Legislature", "").strip() if t else ch
    for a in dict.fromkeys(re.findall(r"objectName=(mcl-Act-[0-9A-Za-z]+-of-\d{4})", page)):
        if a not in [x[1] for x in acts]:
            acts.append((cname, a))
print(f"Michigan Compiled Laws: {len(chapters)} chapters, {len(acts)} acts", flush=True)

def one_act(item):
    cname, act = item
    try:
        text = pdf_text(get(f"{SITE}/documents/mcl/pdf/{act.replace('mcl-', 'MCL-')}.pdf", binary=True))
    except Exception as e:
        print(f"{act}: skipped ({e})", flush=True)
        return []
    time.sleep(PAUSE)
    lines = [l.strip() for l in text.replace("\f", "\n").split("\n")]
    lines = [l for l in lines if l and not FOOT.match(l)]
    aname = lines[0] if lines else act
    actno = act.replace("mcl-", "").replace("-", " ")
    out, cur = [], None
    for i, ln in enumerate(lines):
        m = SEC.match(ln)
        nxt = lines[i + 1] if i + 1 < len(lines) else ""
        if m and (nxt.startswith("Sec.") or "Repealed" in m.group(2) or nxt.startswith("***")):
            if cur:
                out.append(cur)
            sec, catch = m.group(1), m.group(2).strip()
            h = " > ".join([cname, f"{aname} ({actno})", f"{sec} {catch}"])
            cur = {"c": "MCL", "s": sec, "h": h[:600], "t": f"{sec} {catch}"}
        elif cur:
            cur["t"] += "\n" + ln
    if cur:
        out.append(cur)
    return out

import concurrent.futures as cf
rows = []
with cf.ThreadPoolExecutor(4) as ex:
    for n, got in enumerate(ex.map(one_act, acts), 1):
        rows += got
        if n % 100 == 0:
            print(f"{n}/{len(acts)} acts, {len(rows)} sections", flush=True)

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
json.dump({"jurisdiction": "MI", "source": "https://www.legislature.mi.gov/Laws/ChapterIndex (Michigan Legislative Council)",
           "sourceDate": datetime.date.today().isoformat(), "sections": len(rows), "parts": part,
           "built": datetime.date.today().isoformat()}, open(os.path.join(out, "manifest.json"), "w"), indent=1)
print(len(rows), "sections in", part, "parts")
