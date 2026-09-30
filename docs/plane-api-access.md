# Accessing DPlane with curl (interim method)

Until we decide whether to adopt the stdio or HTTP MCP server (see [Plane's MCP docs](https://developers.plane.so/dev-tools/mcp-server)), we read and edit Plane data by calling its REST API directly with `curl`. This is the same API an MCP server would wrap. No MCP server, plugin or extra service is involved.

"Local" here means a command line, not a specific machine: the calls work from any shell with internet access, including Claude Code's cloud session, because the API is public at `https://api.destinationpass.dev`.

## Connection details

| Item                                 | Value                                                                |
| ------------------------------------ | -------------------------------------------------------------------- |
| API base                             | `https://api.destinationpass.dev/api/v1`                             |
| Workspace slug                       | `destination-pass`                                                   |
| Project `Destination Pass` (`DESTI`) | `71420f7d-e513-4e7c-9afd-333ba350c3a8`                               |
| Auth header                          | `X-API-Key: <personal access token>`                                 |
| Web app (for viewing results)        | `https://app.destinationpass.dev/destination-pass/browse/DESTI-<n>/` |

Two hosts, one instance: the app lives at `app.` and the API at `api.`. Always call the API host, never the app host.

## Token handling

- Create a personal access token in Plane (profile > personal access tokens). Give it an expiry.
- The token acts with its owner's permissions: it can read, edit and delete anything that person can. Treat it like a password.
- Keep it in an environment variable, never in a file inside the repo, a commit, an issue or a chat:

  ```bash
  read -rs PLANE_API_KEY && export PLANE_API_KEY
  ```

- Plane's "Download secret key" CSV contains the token in plain text. Delete it after use.
- Revoke tokens when a task or test is finished. For shared or automated use, create a dedicated bot user with only the access it needs and issue the token from that account.

## Verified calls

These were run against the live instance and worked on 2026-09-29. Set `B` once per shell:

```bash
B=https://api.destinationpass.dev/api/v1/workspaces/destination-pass
P=71420f7d-e513-4e7c-9afd-333ba350c3a8   # project id
H="X-API-Key: $PLANE_API_KEY"
```

| Task                  | Command                                                                                                                     |
| --------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| Who am I (auth check) | `curl -sS -H "$H" https://api.destinationpass.dev/api/v1/users/me/`                                                         |
| List projects         | `curl -sS -H "$H" "$B/projects/"`                                                                                           |
| List work items       | `curl -sS -H "$H" "$B/projects/$P/issues/"`                                                                                 |
| Get one work item     | `curl -sS -H "$H" "$B/projects/$P/issues/<issue-id>/"`                                                                      |
| Edit a work item      | `curl -sS -X PATCH -H "$H" -H "Content-Type: application/json" -d '{"priority":"low"}' "$B/projects/$P/issues/<issue-id>/"` |

Notes:

- Work items are addressed by UUID (`id`), not by the `DESTI-8` label. List the issues and match on `sequence_id` (8 for `DESTI-8`).
- List responses are paginated under `results`; check `total_count` and follow the cursor for more.
- Descriptions are HTML (`description_html`).
- A successful edit returns HTTP 200 with the updated object. Read the item back to confirm.

## Not yet verified

Create, comment, delete, state changes, labels, cycles and modules have not been exercised. Check Plane's API reference (https://developers.plane.so/api-reference/introduction, not fetched during setup) for exact paths and payloads, and try them on test data first.

## Ground rules for edits (especially by Claude Code)

1. **Read before write.** Fetch the item first and show what will change.
2. **Smallest possible change.** Send only the fields you mean to change in a `PATCH`.
3. **Test data first.** Use a throwaway work item for anything new.
4. **No deletes or bulk changes without an explicit go-ahead.**
5. **Verify after writing.** Read the item back and, for anything user-visible, open it in the web app.
6. **Never print or store the token.** Don't echo it into logs, files, commit messages or issue text.
7. **Mind the rate limit.** The API's default key limit is `60/minute` (`API_KEY_RATE_LIMIT` in `apps/api/.env.example`). Loop with a short sleep.

## When to move to MCP

Curl is fine for one-off reads and edits and for scripts. Consider the stdio MCP server when:

- People (or agents) will use Plane through Claude Code or Cursor every day, so typed-out `curl` calls become a chore.
- We want structured tools (create, comment, link, cycles, modules) without hand-writing payloads.
- We want per-user tokens managed in each client rather than pasted into shells.

The stdio setup needs `uv` and Python 3.10+ on each user's machine. Set `PLANE_BASE_URL=https://api.destinationpass.dev` (the API host, since ours is split from the app host), `PLANE_WORKSPACE_SLUG=destination-pass` and `PLANE_API_KEY` from an env var. The docs' OAuth option is not available on Community Edition. The HTTP-with-token option depends on an MCP endpoint we haven't confirmed exists on this deployment.

## Related

- `docs/deployment-brief.md`: what runs where and why
- Plane MCP server: https://developers.plane.so/dev-tools/mcp-server
- Plane authentication settings: https://developers.plane.so/self-hosting/govern/authentication
