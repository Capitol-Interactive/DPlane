# Asana to Plane migration (2026-09-29)

Three Asana projects were recreated in our Plane instance (`https://app.destinationpass.dev`, workspace `destination-pass`) through Plane's REST API. This folder records what was created so the migration can be revisited, extended or rolled back.

## Files

| File                | What it is                                                                                                                                                                                      |
| ------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `mapping.json`      | Machine-readable record: Plane project ids, "Done" state ids, module ids, and Asana task gid to Plane work-item UUID. Subtasks are keyed `<parentGid>:<index>`. Also the script's resume state. |
| `mapping.csv`       | The same mapping, readable: `project, plane_key, plane_issue_id, asana_gid, asana_url, parent_plane_key, module, name`. 80 rows.                                                                |
| `asana_to_plane.py` | The script that did the migration, kept for reference (see [Re-running](#re-running-or-extending)).                                                                                             |

No token, credential or task description is stored here. The CSV holds work-item names only.

## What was created

| Asana project                           | Plane project | Plane project id                       | Work items                           | Modules                                                                      |
| --------------------------------------- | ------------- | -------------------------------------- | ------------------------------------ | ---------------------------------------------------------------------------- |
| Fundraising (`1213084889256278`)        | `FUND`        | `5515b635-bee1-499d-b189-8c26365148da` | 1                                    | none                                                                         |
| Account Management (`1213270539233696`) | `ACCT`        | `fed19c86-3949-4685-8c25-8417d0a77315` | 12                                   | Collateral (12)                                                              |
| Sales (`1213099897298811`)              | `SALES`       | `24d7c935-1efc-4cf2-8947-ef61ff785420` | 67 (28 top-level, 39 sub-work-items) | Core Sales Documents (9), Sales Strategy (6), Apollo Setup (7), Outreach (6) |

Total: 3 projects, 80 work items, 5 modules. Asana's Bugs, Feature Flow, Conferences, Website, Marketing, Project Management and Assignments projects were not migrated.

Plane API base: `https://api.destinationpass.dev/api/v1/workspaces/destination-pass`. See `docs/plane-api-access.md` for the curl method used.

## How Asana concepts were mapped

| Asana          | Plane                                                                            |
| -------------- | -------------------------------------------------------------------------------- |
| Project        | Project (identifier `FUND`, `ACCT`, `SALES`; same visibility setting as `DESTI`) |
| Section        | Module (empty "Untitled section" ignored)                                        |
| Task           | Work item                                                                        |
| Subtask        | Sub-work-item (`parent` set), name only                                          |
| Task notes     | `description_html`, paragraphs and line breaks preserved, plus a footer link     |
| Completed task | "Done" state (incomplete tasks keep the project's default state)                 |
| Due date       | `target_date`                                                                    |
| Assignee       | Dropped (only one Plane user exists)                                             |

Every migrated item has `external_source = "asana"` and `external_id` set to the Asana task gid (subtasks: `<parentGid>:<index>`). Each description ends with `Migrated from Asana: https://app.asana.com/0/<project>/<task>`.

## What was NOT migrated

- Comments, attachments, followers, tags, custom fields, dependencies and the Asana project descriptions.
- Subtask details other than the name. Asana did not return subtask notes, due dates or completion status, so all sub-work-items are in the default state.
- One empty-named subtask under "One-Pagers / Leave-Behinds" (Plane requires a name).
- All work items appear as created by the token's owner, not by the original Asana users.

## Notes for anyone looking at the data

- New Plane projects have the Modules feature turned off. It was enabled (`module_view: true`) on `ACCT` and `SALES` so modules work. `FUND` has no modules.
- Plane's API allows 60 requests per minute per key. The script waits about 1.15 seconds between calls.
- `mapping.csv` `module` for a sub-work-item is the module of its parent (only the parent is a module member).

## Rolling back

Asana was only read, never changed. To undo the migration, delete the three Plane projects (`FUND`, `ACCT`, `SALES`) in Plane. That removes their work items and modules. Nothing else depends on them.

## Re-running or extending

`asana_to_plane.py` is idempotent: it records each created item in the state file and skips anything already made. It is kept as a reference, not as a ready-to-run tool, because it was written for the session it ran in:

- It reads the Plane token from an uploaded "secret key" CSV path under `/root/.claude/uploads/`. Replace that with an environment variable such as `PLANE_API_KEY`.
- It reads Asana task lists from session-local files (`TOOLRES`). Replace that with a fresh export or Asana API call.
- The subtask names are hard-coded in `SUBTASKS`, because the Asana connector returned only names.

To migrate another Asana project (for example Bugs, 182 tasks, or Feature Flow, 93): add an entry to `PROJECTS`, decide how to handle comments and attachments (not covered here), run `--dry-run` first, then pilot on a small project.

## Related

- `docs/deployment-brief.md`: what runs where and why
- `docs/plane-api-access.md`: how we call Plane's API with curl
