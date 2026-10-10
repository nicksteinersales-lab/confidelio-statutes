# California codes bundle, from the Legislature's own bulk download,
# pubinfo_YYYY.zip at https://downloads.leginfo.legislature.ca.gov/
#
# Usage: python3 states/ca/bundle.py <pubinfo zip> <out dir>
# One JSON line per active code section: {"c": code, "s": section, "h": heading path, "t": text}.
import gzip, io, json, os, re, sys, zipfile, datetime

src, out = sys.argv[1], sys.argv[2]
z = zipfile.ZipFile(src)

def cols(line):
    return [None if c == "NULL" else c.strip("`") for c in line.rstrip("\n").split("\t")]

toc = {}
for line in io.TextIOWrapper(z.open("LAW_TOC_TBL.dat"), encoding="utf-8", errors="replace"):
    c = cols(line)
    if len(c) < 7:
        continue
    toc[tuple(x or "" for x in c[0:6])] = re.sub(r"\s*\[[^\]]*\]\s*$", "", c[6] or "").strip()

def heading_path(code, vals):
    parts = []
    for i in range(1, 6):
        key = tuple([code] + [(vals[j] or "") if j < i else "" for j in range(5)])
        if vals[i - 1] and key in toc:
            parts.append(toc[key])
    return " > ".join(parts)

tag = re.compile(r"<[^>]+>")
names = set(z.namelist())
rows = []
for line in io.TextIOWrapper(z.open("LAW_SECTION_TBL.dat"), encoding="utf-8", errors="replace"):
    c = cols(line)
    if len(c) < 16 or c[15] != "Y":
        continue
    code, sec = c[1], (c[2] or "").rstrip(".")
    lob = c[14]
    xml = z.read(lob).decode("utf-8", "replace") if lob in names else ""
    text = re.sub(r"[ \t]+", " ", tag.sub(" ", xml.replace("</p>", "\n"))).strip()
    text = re.sub(r"\s*\n\s*", "\n", text)
    rows.append({"c": code, "s": sec, "h": heading_path(code, c[8:13]), "t": text})

rows.sort(key=lambda r: (r["c"], [int(x) if x.isdigit() else x for x in re.split(r"(\d+)", r["s"])]))
os.makedirs(out, exist_ok=True)
for f in os.listdir(out):
    if f.startswith("part-"):
        os.remove(os.path.join(out, f))
part, buf, written = 0, io.BytesIO(), 0
g = gzip.GzipFile(fileobj=buf, mode="wb", compresslevel=9, mtime=0)
def flush(last=False):
    global part, buf, g
    g.close()
    with open(os.path.join(out, f"part-{part:02d}.jsonl.gz"), "wb") as fh:
        fh.write(buf.getvalue())
    part += 1
    if not last:
        buf = io.BytesIO()
        g = gzip.GzipFile(fileobj=buf, mode="wb", compresslevel=9, mtime=0)
raw = 0
for r in rows:
    line = (json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n").encode()
    g.write(line)
    raw += len(line)
    if raw > 30_000_000:  # about 8 MB compressed
        flush()
        raw = 0
flush(last=True)
src_date = max(z.getinfo(n).date_time for n in ("LAW_SECTION_TBL.dat",))
json.dump({"jurisdiction": "CA", "source": "https://downloads.leginfo.legislature.ca.gov/" + os.path.basename(src),
           "sourceDate": "%04d-%02d-%02d" % src_date[:3], "sections": len(rows), "parts": part,
           "built": datetime.date.today().isoformat()}, open(os.path.join(out, "manifest.json"), "w"), indent=1)
print(len(rows), "sections in", part, "parts")
