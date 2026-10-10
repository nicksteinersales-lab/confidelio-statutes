// Checks one state's index before it is published. Exits 1 on any failure, so
// the release keeps the last good version and GitHub emails the owner.
// Usage: node check.mjs <STATE> <index.sqlite> <out manifest.json> [previous manifest.json]
//
// 1. At least checks.json minSections sections.
// 2. No more than a 2% drop from the last published build.
// 3. Every well-known section in checks.json is present and reads correctly.
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { DatabaseSync } from "node:sqlite";

const [jurArg, file, outManifest, prevManifest] = process.argv.slice(2);
const jur = jurArg.toUpperCase();
const checks = JSON.parse(readFileSync(`states/${jurArg.toLowerCase()}/checks.json`, "utf8"));
const db = new DatabaseSync(file, { readOnly: true });
const failures = [];

const meta = db.prepare("SELECT source, source_date AS sourceDate, sections FROM meta WHERE jurisdiction = ?").get(jur) ?? {};
const count = Number(db.prepare("SELECT count(*) AS n FROM sections").get().n);
if (count < checks.minSections) failures.push(`only ${count} sections; expected at least ${checks.minSections}`);

if (prevManifest && existsSync(prevManifest)) {
  const prev = JSON.parse(readFileSync(prevManifest, "utf8"));
  if (prev.sections && count < prev.sections * 0.98) failures.push(`sections fell from ${prev.sections} to ${count} (more than 2%)`);
}

const get = db.prepare("SELECT body FROM sections WHERE code = ? AND sec = ? LIMIT 1");
for (const k of checks.known) {
  const r = get.get(k.code, k.section);
  if (!r) failures.push(`${k.code} ${k.section} missing`);
  else if (!String(r.body).toLowerCase().includes(k.contains.toLowerCase())) failures.push(`${k.code} ${k.section} does not contain "${k.contains}"`);
}

const search = db.prepare("SELECT count(*) AS n FROM sections WHERE sections MATCH ?").get('"court"').n;
if (!search) failures.push("full-text search returned nothing for \"court\"");

if (failures.length) {
  console.error(`${jur} FAILED checks:\n - ` + failures.join("\n - "));
  process.exit(1);
}
writeFileSync(
  outManifest,
  JSON.stringify(
    {
      jurisdiction: jur,
      name: checks.name,
      sections: count,
      source: meta.source ?? "",
      sourceDate: meta.sourceDate ?? "",
      built: new Date().toISOString().slice(0, 10),
      file: `${jurArg.toLowerCase()}.sqlite.gz`,
    },
    null,
    1,
  ),
);
console.log(`${jur} passed: ${count} sections, ${checks.known.length} known sections read correctly.`);
