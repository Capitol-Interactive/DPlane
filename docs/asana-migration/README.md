# Asana to Plane migration (2026-09-29 to 2026-09-30)

Seven Asana projects were recreated in our Plane instance (`https://app.destinationpass.dev`, workspace `destination-pass`) through Plane's REST API. This folder records what was created so the migration can be revisited, extended or rolled back.

## Files

| File                                 | What it is                                                                                                                                           |
| ------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| `mapping.json` / `mapping.csv`       | First batch (Fundraising, Account Management, Sales; 80 items). Plane project ids, "Done" state ids, module ids, Asana gid to Plane work-item UUID.  |
| `mapping-csv-projects.json` / `.csv` | Second batch (Website, Conferences, Marketing, Feature Flow; 245 items). Same idea, plus state, label and module ids. CSV has `plane_key` and names. |
| `asana_to_plane.py`                  | First batch script (Asana connector data, names only for subtasks).                                                                                  |
| `fix_sales_subtasks.py`              | Fixed the Sales subtask descriptions and Done state from the Asana CSV export (2026-09-30).                                                          |
| `asana_website_to_plane.py`          | Website project, from its Asana CSV export.                                                                                                          |
| `asana_csv_to_plane.py`              | Conferences, Marketing and Feature Flow, from their Asana CSV exports (`conferences`, `marketing`, `featureflow` argument).                          |
| `migrate_attachments.py`             | Uploaded Asana-hosted images to Plane work items and added Google Drive links to descriptions.                                                       |

No token, credential, Asana CSV export or temporary download URL is stored here. The mapping CSVs hold work-item names only. The Asana CSV exports contain the full business content and are deliberately not in the repo.

## What was created

| Asana project (gid)                     | Plane project | Work items                           | Modules                                                                      |
| --------------------------------------- | ------------- | ------------------------------------ | ---------------------------------------------------------------------------- |
| Fundraising (`1213084889256278`)        | `FUND`        | 1                                    | none                                                                         |
| Account Management (`1213270539233696`) | `ACCT`        | 12                                   | Collateral (12)                                                              |
| Sales (`1213099897298811`)              | `SALES`       | 67 (28 top-level, 39 sub-work-items) | Core Sales Documents (9), Sales Strategy (6), Apollo Setup (7), Outreach (6) |
| Website (`1213105580286215`)            | `WEB`         | 47 (40 + 7 sub-work-items)           | 5 (from sections)                                                            |
| Conferences (`1213191854695252`)        | `CONF`        | 46                                   | none (single untitled section)                                               |
| Marketing (`1213105580286221`)          | `MKT`         | 39 (29 + 10 sub-work-items)          | Website, Blog Posts, Case Studies, Podcasts, Advertising, Outreach           |
| Feature Flow (`1213139940439760`)       | `FLOW`        | 113 (93 + 20 sub-work-items)         | Web App (50), Future Roadmap (29), Mobile App (14)                           |

Total: 7 projects, 325 work items. Plane project ids are in the mapping JSON files. Asana's Bugs (182 tasks), Project Management and Assignments were not migrated.

Plane API base: `https://api.destinationpass.dev/api/v1/workspaces/destination-pass`. See `docs/plane-api-access.md` for the curl method used.

## How Asana concepts were mapped

| Asana                                   | Plane                                                                                                           |
| --------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| Project                                 | Project (same visibility setting as `DESTI`)                                                                    |
| Section                                 | Module (empty "Untitled section" ignored)                                                                       |
| Task                                    | Work item                                                                                                       |
| Subtask                                 | Sub-work-item (`parent` set), with its own description, state and completion                                    |
| Task notes                              | `description_html` (plain text, paragraphs and line breaks kept), plus a footer link back to Asana              |
| Completed task                          | "Done" state                                                                                                    |
| Due date                                | `target_date`                                                                                                   |
| Assignee                                | Dropped                                                                                                         |
| Priority (Marketing)                    | Plane priority (Normal becomes Medium)                                                                          |
| Status (Marketing, Website)             | Done / In Progress states; On Hold, Needs Images, Hidden as labels                                              |
| Status (Feature Flow)                   | Done / In Progress states; Feature Lock, Testing, Needs Work, Feature Improvement as labels                     |
| Relevance, Location, Link (Conferences) | Relevance as labels (`Relevance 2` to `5`); Location, Relevance, Link as a header at the top of the description |
| Platform (Feature Flow)                 | Labels `Web App`, `Mobile App`                                                                                  |
| Bug Reference / Bugs (Feature Flow)     | Header at the top of the description                                                                            |
| Attachment (Asana upload)               | Plane work-item attachment (5 images on Feature Flow items)                                                     |
| Attachment (Google Drive link)          | Link appended to the description (2, on Sales items)                                                            |

Every migrated item has `external_source = "asana"` and `external_id` set to the Asana task gid (first batch subtasks: `<parentGid>:<index>`). Each description ends with `Migrated from Asana: https://app.asana.com/0/<project>/<task>`.

## What was NOT migrated

- Comments, followers, tags, dependencies, and Asana project descriptions. Dependencies were checked: none exist in the Sales, Website, Conferences, Marketing or Feature Flow exports. Fundraising and Account Management were not checked.
- Rich-text formatting in notes (bold, headings, bullets). The CSV export is plain text.
- Subtask due dates in Sales.
- Assignees and original authors. Items appear as created by the token owner on the migration date.
- Custom fields other than those in the mapping above (for example Marketing Type, Submission Status).
- Three images (`1.jpg`, `2.png`, `3.png`) that a scan attributed to the "Security" subtask of Feature Flow's `2.8 Workspace Settings`. Asana did not return them on a re-check, so they are unverified.
- One empty-named subtask under Sales "One-Pagers / Leave-Behinds" (Plane requires a name).

## Verification

Each CSV-based script has a `--verify` mode that reads every item back from Plane and compares description, state, labels, priority, target date, parent and module counts with the source. All seven projects verified with 0 mismatches. Attachments were verified by downloading each file back through the API and comparing size.

## Notes for anyone looking at the data

- New Plane projects have the Modules feature off. It was enabled (`module_view: true`) on every project that uses modules.
- Plane's API allows 60 requests per minute per key. The scripts wait about 1.15 seconds between calls.
- The `verify` step must page through issues (`per_page=100` plus `cursor`). Projects over 100 items otherwise look incomplete.
- `mapping.csv` `module` for a sub-work-item is its parent's module; only the parent is a module member.
- Attachment uploads work end to end: Plane returns a presigned POST for the Railway bucket, the bucket accepts it, and the bucket allows browser requests from any origin (CORS `*`). The bucket has no backups.

## Rolling back

Asana was only read, never changed. To undo, delete the Plane projects (`FUND`, `ACCT`, `SALES`, `WEB`, `CONF`, `MKT`, `FLOW`) in Plane. That removes their work items, modules and attachment records. Attachment files stay in the bucket until removed there.

## Re-running or extending

The scripts are idempotent (state files record what was created) and are kept as references, not ready-to-run tools, because they were written for the session they ran in:

- They read the Plane token from an uploaded "secret key" CSV under `/root/.claude/uploads/`. Replace that with an environment variable such as `PLANE_API_KEY`.
- They read Asana CSV exports from the same uploads folder. Export the project from Asana (Project menu, Export/Print, CSV).
- `migrate_attachments.py` needs a `urls.json` of temporary Asana download URLs (from the connector's `get_attachments`). It is not committed.

To migrate another project, add an entry to the config in `asana_csv_to_plane.py`, run `--dry-run`, decide how to map its custom fields, then `--apply` and `--verify`. Bugs (182 tasks) is the largest remaining project; its sections (In Progress, High Priority, Needs Testing) look like workflow states, so they probably map to states, not modules.

## Related

- `docs/deployment-brief.md`: what runs where and why
- `docs/plane-api-access.md`: how we call Plane's API with curl
