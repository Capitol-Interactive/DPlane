#!/usr/bin/env python3
"""Recreate three Asana projects in Plane. Idempotent: state kept in asana_to_plane_state.json.

usage: asana_to_plane.py <fundraising|account|sales|all> [--dry-run]
Token is read from the uploaded CSV at run time and never printed.
"""
import csv, glob, html, json, os, sys, time, urllib.request, urllib.error

SCRATCH = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(SCRATCH, "asana_to_plane_state.json")
TOOLRES = "/root/.claude/projects/-home-user-DPlane/3d6a31d2-643f-5caf-9b3a-bd04549d1398/tool-results"
API = "https://api.destinationpass.dev/api/v1/workspaces/destination-pass"
ASANA_WS = "1213091593640700"

def load_token():
    f = sorted(glob.glob("/root/.claude/uploads/*/*secret-key*.csv"))[-1]
    with open(f, newline="") as fh:
        return list(csv.DictReader(fh))[0]["Secret key"].strip()

DRY = "--dry-run" in sys.argv
TOKEN = None if DRY else load_token()
_last = [0.0]

def call(method, path, body=None):
    if DRY:
        return {}
    wait = 1.15 - (time.time() - _last[0])
    if wait > 0:
        time.sleep(wait)
    for attempt in range(5):
        req = urllib.request.Request(API + path, method=method, data=None if body is None else json.dumps(body).encode(),
                                     headers={"X-API-Key": TOKEN, "Content-Type": "application/json"})
        try:
            _last[0] = time.time()
            with urllib.request.urlopen(req, timeout=60) as r:
                raw = r.read()
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            msg = e.read().decode()[:300]
            if e.code == 429:
                time.sleep(20); continue
            raise SystemExit(f"HTTP {e.code} on {method} {path}: {msg}")
    raise SystemExit(f"gave up on {method} {path}")

state = json.load(open(STATE)) if os.path.exists(STATE) else {}
def save():
    if not DRY:
        json.dump(state, open(STATE, "w"), indent=1)

def to_html(notes, footer):
    paras = []
    for block in (notes or "").replace("\r", "").split("\n\n"):
        block = block.strip("\n")
        if block.strip():
            paras.append("<p>" + "<br>".join(html.escape(l) for l in block.split("\n")) + "</p>")
    paras.append("<p><em>" + html.escape(footer) + "</em></p>")
    return "".join(paras)

def tasks_from(fname):
    return json.load(open(os.path.join(TOOLRES, fname)))["data"]

SUBTASKS = {  # parent asana gid -> subtask names (names only; notes/status were not returned by Asana)
    "1213076761138200": [""],  # one empty-named subtask, skipped
    "1213428552078248": ["Venue Managers", "Tourism Consultants & Destination Marketing Consultants", "Complementary Tech Vendors",
                         "Industry Associations & Media", "Event Planning Agencies & Production Companies", "Channel Partnership Setup"],
    "1213735401990190": [f"Sequence {i}: {n}" for i, n in enumerate(["Event Planner Outreach", "Venue Marketing Outreach", "Association Outreach",
                         "DevRel Outreach", "Museum Outreach", "Festival Outreach", "Higher Ed Outreach", "Corporate L&D Outreach",
                         "Sports & Entertainment Outreach", "Religious Org Outreach"], 1)],
    "1213735401990192": [f"Sequence {i} (Multi-Channel): {n}" for i, n in enumerate(["Event Planner Outreach", "Venue Marketing Outreach",
                         "Association Outreach", "DevRel Outreach", "Museum Outreach", "Festival Outreach", "Higher Ed Outreach",
                         "Corporate L&D Outreach", "Sports & Entertainment Outreach", "Religious Org Outreach"], 1)],
    "1213726305188598": ["Sequence 11: Website Visitor Nurture", "Sequence 12: Re-engagement (Stale Leads)", "Sequence 13: Post-Event Follow-up",
                         "Sequence 11 (Multi-Channel): Website Visitor Nurture", "Sequence 12 (Multi-Channel): Re-engagement (Stale Leads)",
                         "Sequence 13 (Multi-Channel): Post-Event Follow-up"],
    "1213909503503388": ["Seq A: Agency / PCO Champions (Email Only, 5 steps)", "Seq B: Association Champions (Email Only, 5 steps) — LAUNCH FIRST",
                         "Seq C: Corporate Champions (Email Only, 5 steps)", "Seq D: DMO Champions (Email Only, 4 steps) — Q3–Q4",
                         "Seq E: Agency / PCO Decision Makers (Multichannel, 10 steps) — Weeks 5-6",
                         "Seq F: Association Decision Makers (Multichannel, 9 steps) — Weeks 3-4",
                         "Seq G: Corporate Decision Makers (Multichannel, 9 steps) — Weeks 7-8"],
}

PROJECTS = {
    "fundraising": dict(name="Fundraising", ident="FUND", asana="1213084889256278", tasks=[
        dict(gid="1213191854695303", name="https://www.obviouslydc.com/business-funding-opportunities", notes="", completed=False, due_on=None,
             memberships=[{"section": {"name": "Untitled section"}}])]),
    "account": dict(name="Account Management", ident="ACCT", asana="1213270539233696",
                    tasks=lambda: tasks_from("mcp-Asana-get_tasks-1790724832673.txt")),
    "sales": dict(name="Sales", ident="SALES", asana="1213099897298811",
                  tasks=lambda: tasks_from("mcp-Asana-get_tasks-1790724833230.txt")),
}

def run(key):
    p = PROJECTS[key]
    tasks = p["tasks"]() if callable(p["tasks"]) else p["tasks"]
    s = state.setdefault(key, {"issues": {}, "modules": {}, "module_members": {}})
    print(f"\n=== {p['name']} ({p['ident']}): {len(tasks)} tasks, {sum(len(SUBTASKS.get(t['gid'], [])) for t in tasks)} subtask rows")

    if "project_id" not in s:
        net = 2
        if not DRY:
            existing = call("GET", "/projects/")
            net = (existing.get("results") or [{}])[0].get("network", 2)
        proj = call("POST", "/projects/", {"name": p["name"], "identifier": p["ident"], "network": net,
                                            "description": "Recreated from the Asana project of the same name."})
        s["project_id"] = proj.get("id", "DRY"); save(); print("  project created", s["project_id"])
    pid = s["project_id"]

    if "done_state" not in s:
        states = call("GET", f"/projects/{pid}/states/")
        rows = states.get("results", states) if isinstance(states, dict) else states
        done = [x for x in (rows or []) if x.get("group") == "completed"]
        s["done_state"] = done[0]["id"] if done else None; save()

    sections = []
    for t in tasks:
        sec = (t.get("memberships") or [{}])[0].get("section", {}).get("name")
        if sec and sec != "Untitled section" and sec not in sections:
            sections.append(sec)
    if sections and not s.get("modules_enabled"):
        call("PATCH", f"/projects/{pid}/", {"module_view": True})
        s["modules_enabled"] = True; save(); print("  enabled the Modules feature on this project")
    for sec in sections:
        if sec not in s["modules"]:
            m = call("POST", f"/projects/{pid}/modules/", {"name": sec})
            s["modules"][sec] = m.get("id", "DRY"); save(); print("  module", sec)

    for t in tasks:
        gid = t["gid"]
        if gid in s["issues"]:
            continue
        footer = f"Migrated from Asana: https://app.asana.com/0/{p['asana']}/{gid}"
        body = {"name": t["name"][:255], "description_html": to_html(t.get("notes"), footer),
                "external_source": "asana", "external_id": gid}
        if t.get("completed") and s["done_state"]:
            body["state"] = s["done_state"]
        if t.get("due_on"):
            body["target_date"] = t["due_on"]
        issue = call("POST", f"/projects/{pid}/issues/", body)
        iid = issue.get("id", "DRY"); s["issues"][gid] = iid; save()
        sec = (t.get("memberships") or [{}])[0].get("section", {}).get("name")
        if sec in s["modules"]:
            s["module_members"].setdefault(sec, []).append(iid)
        for i, sub in enumerate(SUBTASKS.get(gid, [])):
            sub = sub.strip()
            sk = f"{gid}:{i}"
            if not sub or sk in s["issues"]:
                continue
            si = call("POST", f"/projects/{pid}/issues/", {"name": sub[:255], "parent": iid,
                      "description_html": to_html("", f"Migrated from Asana subtask of: {t['name'][:80]}"),
                      "external_source": "asana", "external_id": sk})
            s["issues"][sk] = si.get("id", "DRY"); save()
    for sec, ids in s["module_members"].items():
        if ids and not s.get("module_done_" + sec):
            call("POST", f"/projects/{pid}/modules/{s['modules'][sec]}/module-issues/", {"issues": ids})
            s["module_done_" + sec] = True; save(); print(f"  module '{sec}': {len(ids)} work items linked")
    print(f"  done: {len(s['issues'])} work items recorded")

if __name__ == "__main__":
    keys = [k for k in sys.argv[1:] if not k.startswith("--")]
    for k in (list(PROJECTS) if keys == ["all"] else keys):
        run(k)
