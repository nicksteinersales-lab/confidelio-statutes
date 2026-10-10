// Builds one state's search index from its parts.
// Usage: node build-index.mjs <STATE> <parts dir> <out.sqlite>
//
// Parts are part-NN.jsonl.gz files, one JSON line per section:
// {"c": code, "s": section, "h": heading path, "t": text}. Every state's reader
// writes this same shape, so this file never changes when a state is added.
// Output: SQLite with FTS5 (porter stemming), read-only at runtime.
import { createReadStream, existsSync, readdirSync, readFileSync, rmSync } from "node:fs";
import { createGunzip } from "node:zlib";
import { createInterface } from "node:readline";
import path from "node:path";
import { DatabaseSync } from "node:sqlite";

const [jurArg, dir, outFile] = process.argv.slice(2);
if (!jurArg || !dir || !outFile) {
  console.error("Usage: node build-index.mjs <STATE> <parts dir> <out.sqlite>");
  process.exit(2);
}
const jur = jurArg.toUpperCase();
if (existsSync(outFile)) rmSync(outFile);
const manifestPath = path.join(dir, "manifest.json");
const manifest = existsSync(manifestPath) ? JSON.parse(readFileSync(manifestPath, "utf8")) : {};

const db = new DatabaseSync(outFile);
db.exec(`
  PRAGMA journal_mode = OFF;
  PRAGMA synchronous = OFF;
  CREATE TABLE meta (jurisdiction TEXT PRIMARY KEY, source TEXT, source_date TEXT, sections INTEGER);
  CREATE VIRTUAL TABLE sections USING fts5(
    jur UNINDEXED, code UNINDEXED, sec UNINDEXED, head, body,
    tokenize = 'porter unicode61'
  );
`);
const insert = db.prepare("INSERT INTO sections (jur, code, sec, head, body) VALUES (?, ?, ?, ?, ?)");
let n = 0;
db.exec("BEGIN");
for (const f of readdirSync(dir).filter((f) => /^part-\d+\.jsonl\.gz$/.test(f)).sort()) {
  const rl = createInterface({ input: createReadStream(path.join(dir, f)).pipe(createGunzip()), crlfDelay: Infinity });
  for await (const line of rl) {
    if (!line) continue;
    const r = JSON.parse(line);
    if (!r.c || !r.s) continue;
    insert.run(jur, String(r.c), String(r.s), r.h ?? "", r.t ?? "");
    n++;
  }
}
db.exec("COMMIT");
db.prepare("INSERT INTO meta VALUES (?, ?, ?, ?)").run(jur, manifest.source ?? "", manifest.sourceDate ?? "", n);
db.exec("INSERT INTO sections(sections) VALUES('optimize')");
db.close();
console.log(`${jur}: ${n} sections indexed (source ${manifest.sourceDate ?? "?"})`);
