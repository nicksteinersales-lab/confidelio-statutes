# Confidelio statutes

Full text of state codes, rebuilt weekly from each state's official source and published as search indexes on the [latest release](../../releases/tag/latest).

| State | Source |
|---|---|
| California | California Legislature bulk download, https://downloads.leginfo.legislature.ca.gov/ |
| Texas | Texas Legislative Council code downloads, https://statutes.capitol.texas.gov/Download.aspx (all codes and the Constitution, except Special District Local Laws) |

## How it works

1. `states/<state>/fetch.sh` downloads the official source and writes parts: one JSON line per section, `{"c": code, "s": section, "h": heading, "t": text}`.
2. `build-index.mjs` turns the parts into a SQLite full-text index. It is the same for every state.
3. `check.mjs` runs before anything is published. It requires a minimum section count, allows no more than a 2% drop from the last build, and checks that the well-known sections in `states/<state>/checks.json` are present and read correctly.
4. If the checks pass, `<state>.sqlite.gz` and `<state>.json` (with its SHA-256) replace the old ones on the release. If they fail, the run fails and the release keeps the last good version.
5. `index.json` lists every state on the release. The app downloads it at deploy time and verifies each file's SHA-256.

## Adding a state

Add `states/<state>/fetch.sh` and `states/<state>/checks.json`. Nothing else changes.
