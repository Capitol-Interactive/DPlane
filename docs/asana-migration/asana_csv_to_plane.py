#!/usr/bin/env python3
"""Create Plane projects from Asana CSV exports (Conferences, Marketing). Idempotent; state in <key>_state.json.

usage: asana_csv_to_plane.py <conferences|marketing> [--dry-run | --apply | --verify]
Common mapping: sections -> modules (skipped when only 'Untitled section'); subtasks -> sub-work-items; assignees dropped;
description = header lines (project-specific) + Notes + Asana footer; Done when Completed At set (or Status == Done).
Token is read at run time from the uploaded secret-key CSV and never printed.
"""
import csv, glob, html, json, os, re, sys, time, urllib.request, urllib.error

UPLOADS = "/root/.claude/uploads/3d6a31d2-643f-5caf-9b3a-bd04549d1398"
SCRATCH = os.path.dirname(os.path.abspath(__file__))
API = "https://api.destinationpass.dev/api/v1/workspaces/destination-pass"
KEY = sys.argv[1]
MODE = "--apply" if "--apply" in sys.argv else "--verify" if "--verify" in sys.argv else "--dry-run"
CFG = {
    "conferences": dict(csv=f"{UPLOADS}/a05ed348-Conferences.csv", name="Conferences", ident="CONF", asana="1213191854695252",
                        labels={f"Relevance {n}": c for n, c in {"5": "#dc2626", "4": "#f59e0b", "3": "#3b82f6", "2": "#64748b"}.items()}),
    "marketing": dict(csv=f"{UPLOADS}/76be8880-Marketing.csv", name="Marketing", ident="MKT", asana="1213105580286221",
                      labels={"On Hold": "#64748b"}),
    "featureflow": dict(csv=f"{UPLOADS}/734e4335-Feature_Flow.csv", name="Feature Flow", ident="FLOW", asana="1213139940439760",
                        labels={"Feature Lock": "#8b5cf6", "Testing": "#3b82f6", "Needs Work": "#dc2626", "Feature Improvement": "#f59e0b",
                                "Web App": "#0ea5e9", "Mobile App": "#10b981"}),
}[KEY]
STATE = os.path.join(SCRATCH, f"{KEY}_state.json")
PRIO = {"High": "high", "Normal": "medium", "Low": "low"}

def to_html(text, footer):
    paras = []
    for block in (text or "").replace("\r", "").split("\n\n"):
        block = block.strip("\n")
        if block.strip():
            paras.append("<p>" + "<br>".join(html.escape(l) for l in block.split("\n")) + "</p>")
    paras.append("<p><em>" + html.escape(footer) + "</em></p>")
    return "".join(paras)
def plain(h):
    h = re.sub(r"<br\s*/?>", "\n", h or ""); h = re.sub(r"</p>", "\n\n", h); h = re.sub(r"<[^>]+>", "", h); return html.unescape(h)
def norm(s): return re.sub(r"\s+", " ", html.unescape(s or "")).strip()

rows = list(csv.DictReader(open(CFG["csv"], newline="", encoding="utf-8-sig")))
top = [r for r in rows if not (r["Parent task"] or "").strip()]
subs = [r for r in rows if (r["Parent task"] or "").strip()]
names = [r["Name"] for r in top]
assert all(r["Name"].strip() for r in rows), "empty names"
if KEY != "featureflow": assert len(set(names)) == len(names), "duplicate names"
for s in subs: assert names.count(s["Parent task"]) == 1, f"parent missing or ambiguous: {s['Parent task']}"

def desc_text(r):
    if KEY == "conferences":
        head = [f"{k}: {v}" for k, v in (("Location", r["Location"].strip()), ("Relevance", (r["Relevance"].strip() + "/5") if r["Relevance"].strip() else ""),
                                            ("Link", r["Link"].strip())) if v]
        return ("\n".join(head) + "\n\n" if head else "") + (r["Notes"] or "")
    if KEY == "featureflow":
        head = [f"{k}: {v}" for k, v in (("Bug Reference", r["Bug Reference"].strip()), ("Bugs", r["Bugs"].strip())) if v]
        return ("\n".join(head) + "\n\n" if head else "") + (r["Notes"] or "")
    return r["Notes"] or ""

def want(r):
    ws = (r.get("Status") or "").strip() if KEY in ("marketing", "featureflow") else ""
    done = ws == "Done" or bool((r.get("Completed At") or "").strip())
    st = "done" if done else "progress" if ws == "In Progress" else "default"
    lbls = []
    if ws == "On Hold": lbls.append("On Hold")
    if KEY == "featureflow":
        if ws in CFG["labels"]: lbls.append(ws)
        lbls += [p.strip() for p in r["Platform"].split(",") if p.strip()]
    if KEY == "conferences" and r["Relevance"].strip(): lbls.append(f"Relevance {r['Relevance'].strip()}")
    pr = PRIO.get((r.get("Priority (Bug)") or "").strip()) if KEY == "marketing" else None
    return st, lbls, pr

sections = [] if KEY == "conferences" else list(dict.fromkeys(r["Section/Column"] for r in top if r["Section/Column"] and r["Section/Column"] != "Untitled section"))
if KEY in ("marketing", "featureflow"): assert all(r["Section/Column"] in sections for r in top), "top-level task without a section"

if MODE == "--dry-run":
    from collections import Counter
    print(f"{CFG['name']} ({CFG['ident']}): top-level {len(top)}, subtasks {len(subs)}")
    print("states:", dict(Counter(want(r)[0] for r in rows)), "| labels:", dict(Counter(l for r in rows for l in want(r)[1])), "| priority:", dict(Counter(want(r)[2] for r in rows)))
    print("modules:", dict(Counter(r["Section/Column"] for r in top)) if sections else "none", "| target dates:", sum(1 for r in rows if r["Due Date"].strip()))
    print("sample description:\n" + desc_text(top[0])[:260])
    raise SystemExit(0)

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

state = json.load(open(STATE)) if os.path.exists(STATE) else {"issues": {}, "modules": {}, "labels": {}}
def save(): json.dump(state, open(STATE, "w"), indent=1)

if MODE == "--apply":
    if "project_id" not in state:
        net = (call("GET", "/projects/").get("results") or [{}])[0].get("network", 2)
        p = call("POST", "/projects/", {"name": CFG["name"], "identifier": CFG["ident"], "network": net,
                                        "description": "Recreated from the Asana project of the same name."})
        state["project_id"] = p["id"]; save(); print("project created", p["id"])
        if sections: call("PATCH", f"/projects/{p['id']}/", {"module_view": True}); print("modules enabled")
    pid = state["project_id"]
    if "states" not in state:
        rs = call("GET", f"/projects/{pid}/states/"); rs = rs.get("results", rs)
        state["states"] = {"done": next(x["id"] for x in rs if x["group"] == "completed"),
                           "progress": next(x["id"] for x in rs if x["name"] == "In Progress")}; save()
    for name, color in CFG["labels"].items():
        if name not in state["labels"]:
            state["labels"][name] = call("POST", f"/projects/{pid}/labels/", {"name": name, "color": color})["id"]; save(); print("label", name)
    for sec in sections:
        if sec not in state["modules"]:
            state["modules"][sec] = call("POST", f"/projects/{pid}/modules/", {"name": sec})["id"]; save(); print("module", sec)
    members = {}
    def make(r, parent_id=None):
        gid = r["Task ID"]
        if gid in state["issues"]: return state["issues"][gid]
        st, lbls, pr = want(r)
        body = {"name": r["Name"][:255], "external_source": "asana", "external_id": gid,
                "description_html": to_html(desc_text(r), f"Migrated from Asana: https://app.asana.com/0/{CFG['asana']}/{gid}")}
        if st in state["states"]: body["state"] = state["states"][st]
        if lbls: body["labels"] = [state["labels"][l] for l in lbls]
        if pr: body["priority"] = pr
        if (r.get("Due Date") or "").strip(): body["target_date"] = r["Due Date"].strip()
        if parent_id: body["parent"] = parent_id
        iid = call("POST", f"/projects/{pid}/issues/", body)["id"]; state["issues"][gid] = iid; save(); return iid
    for r in top:
        iid = make(r)
        if sections: members.setdefault(r["Section/Column"], []).append(iid)
        for s in [x for x in subs if x["Parent task"] == r["Name"]]: make(s, iid)
    for sec, ids in members.items():
        if not state.get("mod_done_" + sec):
            call("POST", f"/projects/{pid}/modules/{state['modules'][sec]}/module-issues/", {"issues": ids})
            state["mod_done_" + sec] = True; save(); print(f"module '{sec}': {len(ids)} linked")
    print(f"done: {len(state['issues'])} work items")

if MODE == "--verify":
    pid = state["project_id"]
    items, cur = [], None
    while True:
        pg = call("GET", f"/projects/{pid}/issues/?per_page=100" + (f"&cursor={cur}" if cur else ""))
        if isinstance(pg, list): items += pg; break
        items += pg.get("results", [])
        if not pg.get("next_page_results"): break
        cur = pg["next_cursor"]
    by_ext = {i["external_id"]: i for i in items}
    bad = 0
    for r in rows:
        i = by_ext.get(r["Task ID"])
        if not i: bad += 1; print("MISSING", r["Name"]); continue
        st, lbls, pr = want(r); errs = []
        d = norm(plain(i["description_html"])); d = re.sub(r"Migrated from Asana: https://app\.asana\.com/\S+$", "", d).strip()
        if d != norm(desc_text(r)): errs.append("description")
        if st == "done" and i["state"] != state["states"]["done"]: errs.append("state should be Done")
        if st == "progress" and i["state"] != state["states"]["progress"]: errs.append("state should be In Progress")
        if st == "default" and i["state"] in (state["states"]["done"], state["states"]["progress"]): errs.append("state should be default")
        if sorted(i.get("labels") or []) != sorted(state["labels"][l] for l in lbls): errs.append("labels")
        if (i.get("priority") or "none") != (pr or "none"): errs.append(f"priority {i.get('priority')} vs {pr}")
        if (i.get("target_date") or None) != ((r["Due Date"].strip() or None)): errs.append("target_date")
        if bool(i.get("parent")) != bool((r["Parent task"] or "").strip()): errs.append("parent")
        if r["Name"][:255] != i["name"]: errs.append("name")
        if errs: bad += 1; print("MISMATCH", r["Name"][:40], errs)
    mod_bad = 0
    for sec, mid in state["modules"].items():
        want_n = sum(1 for r in top if r["Section/Column"] == sec)
        got = call("GET", f"/projects/{pid}/modules/{mid}/module-issues/"); got = len(got.get("results", got))
        if got != want_n: mod_bad += 1; print("MODULE", sec, got, "vs", want_n)
    print(f"verify {CFG['name']}: {len(rows) - bad} of {len(rows)} work items match, {bad} mismatches; issues in Plane: {len(items)}; module count mismatches: {mod_bad}")
