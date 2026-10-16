# Agents

Agents are Claude agents that work in the workspace like teammates. Each one is a **bot user** (`User.is_bot`):
it cannot log in, and it acts through its own API token, so its comments, pages and updates carry its name.

## What an agent is

- A `User` with `is_bot=True` and an unusable password (login is blocked in `authentication/adapter/base.py`).
- `bot_type`: the job title shown on the Agents page ("Finance and billing"; 30 characters at most).
- `bot_reports_to`: the user (person or agent) it reports to. Migration `0125`.
- A workspace membership, plus project memberships for the projects it works in.
- An API token (`APIToken`, `user_type=1`). Requests made with it run as the agent, so a comment posted through
  `POST /api/v1/.../comments/` is saved with `actor` = the agent.

## Creating an agent

```bash
python manage.py create_agent \
  --workspace destination-pass \
  --email fiona@agents.example.com \
  --name "Finance Fiona" \
  --role "Finance and billing" \
  --reports-to joe@example.com
```

It creates or updates the user, adds it to the workspace (member role by default) and prints a new API token once
when the agent has none (`--new-token` makes another). Store the token as that agent's own secret. Add the agent
to projects with `create_project_member` or the project's Members settings.

## Where agents show up

- Assignee pickers, @mention search and the workspace and project member lists include bots (the
  `is_bot=False` filters were removed from the member and search views).
- Seat counts, analytics and telemetry still exclude bots.
- **Agents > Agent team** (`components/agents/agent-roster.tsx`) lists them with role, manager, open work items
  and recent comments, from `GET /api/workspaces/<slug>/agents/` (`app/views/agents/base.py`).

## Tests

`plane/tests/contract/app/test_agents_app.py` covers the roster endpoint, bots in the project member list and the
`create_agent` command.
