#!/usr/bin/env python3
"""Create the Plane WEB project from the Asana Website CSV export. Idempotent (state in website_state.json).

usage: asana_website_to_plane.py [--dry-run | --apply | --verify]
Mapping: sections -> modules; subtasks -> sub-work-items; assignees dropped; description = Notes + Asana footer.
State: Done when Web Status == Done or Completed At set; In Progress when Web Status == In Progress; else default (Backlog).
Web Status Needs Images / On Hold / Hidden -> labels. Token is read at run time, never printed.
"""
import csv, glob, html, json, os, re, sys, time, urllib.request, urllib.error

UPLOADS = "/root/.claude/uploads/3d6a31d2-643f-5caf-9b3a-bd04549d1398"
CSV_PATH = f"{UPLOADS}/cf55d7b8-Website-tasks.csv"
SCRATCH = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(SCRATCH, "website_state.json")
API = "https://api.destinationpass.dev/api/v1/workspaces/destination-pass"
ASANA_PROJECT = "1213105580286215"
MODE = "--apply" if "--apply" in sys.argv else "--verify" if "--verify" in sys.argv else "--dry-run"
LABELS = {"Needs Images": "#f59e0b", "On Hold": "#64748b", "Hidden": "#8b5cf6"}

def to_html(notes, footer):
    paras = []
    for block in (notes or "").replace("\r", "").split("\n\n"):
        block = block.strip("\n")
        if block.strip():
            paras.append("<p>" + "<br>".join(html.escape(l) for l in block.split("\n")) + "</p>")
    paras.append("<p><em>" + html.escape(footer) + "</em></p>")
    return "".join(paras)
def plain(h):
    h = re.sub(r"<br\s*/?>", "\n", h or ""); h = re.sub(r"</p>", "\n\n", h); h = re.sub(r"<[^>]+>", "", h); return html.unescape(h)
def norm(s): return re.sub(r"\s+", " ", html.unescape(s or "")).strip()

rows = list(csv.DictReader(open(CSV_PATH, newline="", encoding="utf-8-sig")))
top = [r for r in rows if not (r["Parent task"] or "").strip()]
subs = [r for r in rows if (r["Parent task"] or "").strip()]
names = [r["Name"] for r in top]
assert len(top) == 40 and len(subs) == 7 and all(r["Name"].strip() for r in rows), "unexpected CSV shape"
assert len(set(names)) == len(names), "duplicate top-level names"
for s in subs: assert s["Parent task"] in names, f"parent not found: {s['Parent task']}"

if MODE != "--dry-run":
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
            raise SystemExit(f"HTTP {e.code} on {method} {path}: {e.read().decode()[:300]}")
    raise SystemExit(f"gave up on {method} {path}")

def want(r):
    ws = (r.get("Web Status") or "").strip()
    done = ws == "Done" or bool((r.get("Completed At") or "").strip())
    st = "done" if done else "progress" if ws == "In Progress" else "default"
    return st, ([ws] if ws in LABELS else [])

if MODE == "--dry-run":
    from collections import Counter
    print(f"top-level {len(top)}, subtasks {len(subs)}")
    print("states:", dict(Counter(want(r)[0] for r in rows)))
    print("labels:", dict(Counter(l for r in rows for l in want(r)[1])))
    print("modules:", dict(Counter(r["Section/Column"] for r in top)))
    print("subtasks under:", dict(Counter(s["Parent task"] for s in subs)))
    print("total notes chars:", sum(len(r["Notes"]) for r in rows))
    raise SystemExit(0)

state = json.load(open(STATE)) if os.path.exists(STATE) else {"issues": {}, "modules": {}, "labels": {}}
def save(): json.dump(state, open(STATE, "w"), indent=1)

if MODE == "--apply":
    if "project_id" not in state:
        net = (call("GET", "/projects/").get("results") or [{}])[0].get("network", 2)
        p = call("POST", "/projects/", {"name": "Website", "identifier": "WEB", "network": net,
                                        "description": "Recreated from the Asana project of the same name."})
        state["project_id"] = p["id"]; save(); print("project created", p["id"])
        call("PATCH", f"/projects/{state['project_id']}/", {"module_view": True}); print("modules enabled")
    pid = state["project_id"]
    if "states" not in state:
        rowsS = call("GET", f"/projects/{pid}/states/"); rowsS = rowsS.get("results", rowsS)
        state["states"] = {"done": next(x["id"] for x in rowsS if x["group"] == "completed"),
                           "progress": next(x["id"] for x in rowsS if x["name"] == "In Progress")}; save()
    for name, color in LABELS.items():
        if name not in state["labels"]:
            state["labels"][name] = call("POST", f"/projects/{pid}/labels/", {"name": name, "color": color})["id"]; save(); print("label", name)
    for sec in dict.fromkeys(r["Section/Column"] for r in top):
        if sec not in state["modules"]:
            state["modules"][sec] = call("POST", f"/projects/{pid}/modules/", {"name": sec})["id"]; save(); print("module", sec)
    members = {}
    def make(r, parent_id=None):
        gid = r["Task ID"]
        if gid in state["issues"]: return state["issues"][gid]
        st, lbls = want(r)
        body = {"name": r["Name"][:255], "external_source": "asana", "external_id": gid,
                "description_html": to_html(r["Notes"], f"Migrated from Asana: https://app.asana.com/0/{ASANA_PROJECT}/{gid}")}
        if st in state["states"]: body["state"] = state["states"][st]
        if lbls: body["labels"] = [state["labels"][l] for l in lbls]
        if (r.get("Due Date") or "").strip(): body["target_date"] = r["Due Date"].strip()
        if parent_id: body["parent"] = parent_id
        iid = call("POST", f"/projects/{pid}/issues/", body)["id"]; state["issues"][gid] = iid; save(); return iid
    by_name = {}
    for r in top:
        iid = make(r); by_name[r["Name"]] = iid; members.setdefault(r["Section/Column"], []).append(iid)
        for s in [x for x in subs if x["Parent task"] == r["Name"]]: make(s, iid)
    for sec, ids in members.items():
        if not state.get("mod_done_" + sec):
            call("POST", f"/projects/{pid}/modules/{state['modules'][sec]}/module-issues/", {"issues": ids})
            state["mod_done_" + sec] = True; save(); print(f"module '{sec}': {len(ids)} linked")
    print(f"done: {len(state['issues'])} work items")

if MODE == "--verify":
    pid = state["project_id"]
    items = call("GET", f"/projects/{pid}/issues/?per_page=100"); items = items.get("results", items)
    by_ext = {i["external_id"]: i for i in items}
    bad = 0
    for r in rows:
        i = by_ext.get(r["Task ID"])
        if not i: bad += 1; print("MISSING", r["Name"]); continue
        st, lbls = want(r)
        desc = norm(plain(i["description_html"])); desc = re.sub(r"Migrated from Asana: https://app\.asana\.com/\S+$", "", desc).strip()
        errs = []
        if desc != norm(r["Notes"]): errs.append("description")
        if st == "done" and i["state"] != state["states"]["done"]: errs.append("state should be Done")
        if st == "progress" and i["state"] != state["states"]["progress"]: errs.append("state should be In Progress")
        if st == "default" and i["state"] in (state["states"]["done"], state["states"]["progress"]): errs.append("state should be default")
        if sorted(i.get("labels") or []) != sorted(state["labels"][l] for l in lbls): errs.append("labels")
        if bool(i.get("parent")) != bool((r["Parent task"] or "").strip()): errs.append("parent")
        if errs: bad += 1; print("MISMATCH", r["Name"][:40], errs)
    print(f"verify: {len(rows) - bad} of {len(rows)} match, {bad} mismatches; issues in Plane: {len(items)}")
