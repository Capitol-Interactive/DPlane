#!/usr/bin/env python3
"""Fix SALES sub-work-item descriptions/state from the Asana Sales CSV export.

usage: fix_sales_subtasks.py [--dry-run | --apply | --verify]
Matches CSV subtask rows to Plane sub-work-items by (parent name, subtask name). Aborts on any ambiguity.
Only PATCHes description_html and (for completed subtasks) state. Token is read at run time, never printed.
"""
import csv, glob, html, json, re, sys, time, urllib.request, urllib.error

UPLOADS = "/root/.claude/uploads/3d6a31d2-643f-5caf-9b3a-bd04549d1398"
CSV_PATH = f"{UPLOADS}/73ef9bba-Sales.csv"
MAPPING_CSV = "/home/user/DPlane/docs/asana-migration/mapping.csv"
MAPPING_JSON = "/home/user/DPlane/docs/asana-migration/mapping.json"
API = "https://api.destinationpass.dev/api/v1/workspaces/destination-pass"
ASANA_PROJECT = "1213099897298811"
MODE = "--apply" if "--apply" in sys.argv else "--verify" if "--verify" in sys.argv else "--dry-run"

def norm(s): return re.sub(r"\s+", " ", html.unescape(s or "")).strip().lower()

def to_html(notes, footer):
    paras = []
    for block in (notes or "").replace("\r", "").split("\n\n"):
        block = block.strip("\n")
        if block.strip():
            paras.append("<p>" + "<br>".join(html.escape(l) for l in block.split("\n")) + "</p>")
    paras.append("<p><em>" + html.escape(footer) + "</em></p>")
    return "".join(paras)

def plain(h):
    h = re.sub(r"<br\s*/?>", "\n", h or ""); h = re.sub(r"</p>", "\n\n", h); h = re.sub(r"<[^>]+>", "", h)
    return html.unescape(h)

tok = list(csv.DictReader(open(sorted(glob.glob(f"{UPLOADS}/*secret-key*.csv"))[-1])))[0]["Secret key"].strip()
_last = [0.0]
def call(method, path, body=None):
    wait = 1.15 - (time.time() - _last[0])
    if wait > 0: time.sleep(wait)
    for _ in range(5):
        req = urllib.request.Request(API + path, method=method, data=None if body is None else json.dumps(body).encode(),
                                     headers={"X-API-Key": tok, "Content-Type": "application/json"})
        try:
            _last[0] = time.time()
            with urllib.request.urlopen(req, timeout=60) as r:
                raw = r.read(); return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            if e.code == 429: time.sleep(20); continue
            raise SystemExit(f"HTTP {e.code} on {method} {path}: {e.read().decode()[:200]}")
    raise SystemExit(f"gave up on {method} {path}")

# ---- build the match table
rows = list(csv.DictReader(open(CSV_PATH, newline="", encoding="utf-8-sig")))
sub = [r for r in rows if (r.get("Parent task") or "").strip() and (r.get("Name") or "").strip()]
mp = list(csv.DictReader(open(MAPPING_CSV)))
key = {r["plane_key"]: r for r in mp}
plane = [r for r in mp if r["project"] == "Sales" and r["parent_plane_key"]]
by_plane = {(norm(key[r["parent_plane_key"]]["name"]), norm(r["name"])): r for r in plane}
by_csv = {}
for r in sub:
    k = (norm(r["Parent task"]), norm(r["Name"]))
    if k in by_csv: raise SystemExit(f"ambiguous CSV row {k}")
    by_csv[k] = r
if set(by_csv) != set(by_plane) or len(by_plane) != 39:
    raise SystemExit(f"MATCH FAILED: csv {len(by_csv)} vs plane {len(by_plane)}; only-csv {set(by_csv)-set(by_plane)}; only-plane {set(by_plane)-set(by_csv)}")
done_state = json.load(open(MAPPING_JSON))["sales"]["done_state"]
pid = json.load(open(MAPPING_JSON))["sales"]["project_id"]
print(f"mode {MODE}: 39/39 subtasks matched (CSV subtask rows used: {len(sub)}; empty-named skipped: {sum(1 for r in rows if r.get('Parent task') and not r['Name'].strip())})")

changed = mism = 0
for k, r in by_csv.items():
    p = by_plane[k]
    want_html = to_html(r["Notes"], f"Migrated from Asana: https://app.asana.com/0/{ASANA_PROJECT}/{r['Task ID']}")
    want_done = bool((r.get("Completed At") or "").strip())
    label = f"{p['plane_key']:<9} {r['Name'][:52]:<52} notes={len(r['Notes']):>5} done={'Y' if want_done else '-'}"
    if MODE == "--dry-run":
        print("  would set", label); continue
    cur = call("GET", f"/projects/{pid}/issues/{p['plane_issue_id']}/")
    if MODE == "--verify":
        ok_desc = norm(plain(cur.get("description_html"))).replace("migrated from asana: ", "") .startswith(norm(r["Notes"])[:200])
        full = norm(re.sub(r"https://app\.asana\.com/\S+\s*$", "", norm(plain(cur.get("description_html"))))) == norm(r["Notes"]) or \
               norm(plain(cur.get("description_html"))).replace(norm("Migrated from Asana: https://app.asana.com/0/%s/%s" % (ASANA_PROJECT, r["Task ID"])), "").strip() == norm(r["Notes"])
        ok_state = (cur.get("state") == done_state) == want_done if want_done else cur.get("state") != done_state
        if not (full and ok_state): mism += 1; print("  MISMATCH", label, "| desc", full, "| state", ok_state)
        continue
    body = {}
    if (cur.get("description_html") or "") != want_html: body["description_html"] = want_html
    if want_done and cur.get("state") != done_state: body["state"] = done_state
    if body:
        call("PATCH", f"/projects/{pid}/issues/{p['plane_issue_id']}/", body); changed += 1
        print("  patched", label, list(body))
    else:
        print("  already ok", label)
if MODE == "--apply": print(f"\napplied: {changed} of 39 patched")
if MODE == "--verify": print(f"\nverify: {39 - mism} of 39 match, {mism} mismatches")
