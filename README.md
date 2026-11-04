# Confidelio statutes

Full text of state codes, rebuilt weekly from each state's official source and published as search indexes on the [latest release](../../releases/tag/latest).

| State | Source |
|---|---|
| California | California Legislature bulk download, https://downloads.leginfo.legislature.ca.gov/ |
| Texas | Texas Legislative Council code downloads, https://statutes.capitol.texas.gov/Download.aspx (all codes and the Constitution, except Special District Local Laws) |
| Florida | Florida Legislature, Online Sunshine, http://www.leg.state.fl.us/statutes/ (every chapter of the Florida Statutes, read page by page; no bulk download exists) |
| Illinois | Illinois General Assembly public file repository, https://ftp.ilga.gov/ILCS/ (the Illinois Compiled Statutes, one file per section; ILGA refreshes it about once a year, so an unchanged edition reuses the last build) |
| Washington | Washington State Legislature, Code Reviser public law files, https://lawfilesext.leg.wa.gov/law/RCW/ (the Revised Code of Washington, one file per section; an unchanged edition reuses the last build) |
| Ohio | Ohio Legislative Service Commission, https://codes.ohio.gov/ohio-revised-code (the Ohio Revised Code, read chapter by chapter; each chapter page carries every section) |
| North Carolina | North Carolina General Assembly, https://www.ncleg.gov/Laws/GeneralStatutesTOC (the General Statutes, read chapter by chapter) |
| Virginia | Virginia Division of Legislative Services, https://law.lis.virginia.gov/vacode/ (the Code of Virginia, read chapter by chapter) |
| New York | New York State Senate Open Legislation API, https://legislation.nysenate.gov (every consolidated and unconsolidated law; needs the NY_OPENLEG_KEY repo secret) |
| Michigan | Michigan Legislature, https://www.legislature.mi.gov/Laws/ChapterIndex (the Michigan Compiled Laws, one official PDF per act) |
| Arizona | Arizona Legislature, https://www.azleg.gov/arstitle/ (the Arizona Revised Statutes, one page per section) |
| New Jersey | New Jersey Legislature, https://pub.njleg.gov/statutes/ (the statutes in plain text, updated every weekday) |
| Minnesota | Office of the Revisor of Statutes, https://www.revisor.mn.gov/statutes/ (the Minnesota Statutes, read chapter by chapter) |
| Oregon | Oregon Legislative Counsel, https://www.oregonlegislature.gov/bills_laws/Pages/ORS.aspx (the Oregon Revised Statutes, one file per chapter) |
| Massachusetts | Massachusetts General Court, https://malegislature.gov/Laws/GeneralLaws (the General Laws, one page per section) |
| Missouri | Missouri Revisor of Statutes, https://revisor.mo.gov (the Revised Statutes of Missouri, one page per section) |
| South Carolina | South Carolina Legislative Council, https://www.scstatehouse.gov/code/statmast.php (the Code of Laws, one page per chapter) |
| Nevada | Legislative Counsel Bureau, https://www.leg.state.nv.us/NRS/ (the Nevada Revised Statutes, one page per chapter) |
| Delaware | Delaware Code Revisors, https://delcode.delaware.gov (the Delaware Code, one page per chapter) |
| Vermont | Office of Legislative Counsel, https://legislature.vermont.gov/statutes/ (the Vermont Statutes, one page per chapter) |

## How it works

1. `states/<state>/fetch.sh` downloads the official source and writes parts: one JSON line per section, `{"c": code, "s": section, "h": heading, "t": text}`.
2. `build-index.mjs` turns the parts into a SQLite full-text index. It is the same for every state.
3. `check.mjs` runs before anything is published. It requires a minimum section count, allows no more than a 2% drop from the last build, and checks that the well-known sections in `states/<state>/checks.json` are present and read correctly.
4. If the checks pass, `<state>.sqlite.gz` and `<state>.json` (with its SHA-256) replace the old ones on the release. If they fail, the run fails and the release keeps the last good version.
5. `index.json` lists every state on the release. The app downloads it at deploy time and verifies each file's SHA-256.

## Adding a state

Shared helpers for new bundles live in `lib/statelib.py` (fetching, HTML to text, a worker pool, writing parts).

Add `states/<state>/fetch.sh` and `states/<state>/checks.json`. Nothing else changes.
