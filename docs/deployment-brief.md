# DPlane deployment: technical brief

DPlane is Capitol Interactive's deployment of [Plane](https://github.com/makeplane/plane) (project management), run from a fork of the upstream repo. This brief records what runs where, why, and how the pieces connect. Written 2026-09-29 after go-live.

No secrets are recorded here. Credentials live in Railway variables (references between services) and in the Plane admin app.

## At a glance

| Public address                      | What it is                                    | Host                           |
| ----------------------------------- | --------------------------------------------- | ------------------------------ |
| `https://app.destinationpass.dev`   | Plane web app (static SPA)                    | Vercel project `d-plane-web`   |
| `https://admin.destinationpass.dev` | Plane instance admin ("god mode", static SPA) | Vercel project `d-plane-admin` |
| `https://api.destinationpass.dev`   | Plane API (Django)                            | Railway service `api`          |
| `https://live.destinationpass.dev`  | Real-time collaboration server (websockets)   | Railway service `live`         |

All four sit under one parent domain on purpose: Plane's session and CSRF cookies must be same-site (see [Design decisions](#design-decisions-and-why)).

## Services and what each is for

### Vercel (team: Capitol Interactive Dev, Pro plan)

| Project         | Purpose                                       | Build settings                                                                                                                                      |
| --------------- | --------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| `d-plane-web`   | User-facing app. Static build (`ssr: false`). | Root `apps/web`; install `cd ../.. && pnpm install --frozen-lockfile`; build `cd ../.. && pnpm turbo run build --filter=web`; output `build/client` |
| `d-plane-admin` | Instance admin app. Static build.             | Same, with root `apps/admin` and `--filter=admin`                                                                                                   |

Build-time env vars on both (`VITE_*`, baked into the bundle, so a change needs a redeploy):
`VITE_API_BASE_URL`, `VITE_WEB_BASE_URL`, `VITE_ADMIN_BASE_URL` (the three `destinationpass.dev` addresses above), `VITE_SPACE_BASE_URL` (placeholder until `space` exists), `VITE_LIVE_BASE_URL` and `VITE_LIVE_BASE_PATH=/live`. On `d-plane-web`, `VITE_LIVE_BASE_URL` is `https://live.destinationpass.dev` for Production; Preview still has a placeholder.
Do **not** set `VITE_ADMIN_BASE_PATH` or `VITE_SPACE_BASE_PATH`: a value of `/` becomes `//` and the Vite build fails with "Invalid URL".

### Railway (project `plane`, environment `production`)

All backend pieces run in one project so they talk over Railway's private network.

| Service                | Purpose                                                                                               | Source / image                                                                                  |
| ---------------------- | ----------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| `api`                  | Django API behind gunicorn/uvicorn, port 8000, public domain `api.destinationpass.dev`                | Repo branch `production`, root `apps/api`, `Dockerfile.api`                                     |
| `worker`               | Celery worker: background tasks (activity/history, notifications, webhooks, emails, file metadata)    | Same image, start `./bin/docker-entrypoint-worker.sh`                                           |
| `beat-worker`          | Celery beat scheduler: recurring jobs (email digests every 5 min, nightly cleanup and archiving)      | Same image, start `./bin/docker-entrypoint-beat.sh`                                             |
| `migrator`             | Runs Django migrations, then exits (restart policy Never). Reruns on each redeploy.                   | Same image, start `./bin/docker-entrypoint-migrator.sh`                                         |
| `live`                 | Hocuspocus/Yjs collaboration server for the page editor, port 3000, domain `live.destinationpass.dev` | Repo branch `production`, repo root, `apps/live/Dockerfile.railway`, healthcheck `/live/health` |
| Postgres 18            | Primary database (database `plane`), 5 GB volume                                                      | Railway template (`postgres-ssl:18`)                                                            |
| Redis 8.2              | Cache and result store, 5 GB volume                                                                   | Railway template                                                                                |
| RabbitMQ 3.13.6        | Celery message broker, vhost `plane`, 5 GB volume                                                     | Official image `rabbitmq:3.13.6-management-alpine`                                              |
| Bucket `plane-uploads` | S3-compatible object storage for attachments and avatars                                              | Railway Storage Bucket (region `sjc`)                                                           |

Wiring: the API, worker, beat and migrator get `DATABASE_URL`, `REDIS_URL`, `RABBITMQ_*` and `AWS_*` as Railway variable **references** (for example `${{Postgres.DATABASE_URL}}`), never pasted values. `SECRET_KEY` and `LIVE_SERVER_SECRET_KEY` are environment-level shared variables. The API also carries `PORT=8000`, `COOKIE_DOMAIN=.destinationpass.dev`, `CORS_ALLOWED_ORIGINS`, `WEB_URL`, `APP_BASE_URL`, `ADMIN_BASE_URL`, `USE_MINIO=0`.

The `live` service gets `REDIS_URL` (reference to Redis), `LIVE_SERVER_SECRET_KEY` (the shared variable), `PORT=3000`, `API_BASE_URL=https://api.destinationpass.dev`, `LIVE_BASE_PATH=/live`, `CORS_ALLOWED_ORIGINS` and `WEB_BASE_URL` (both `https://app.destinationpass.dev`). It authenticates editors by forwarding their session cookie to the API, which is why it must sit under `destinationpass.dev`. Its watch patterns (`/apps/live/**`, `/packages/**`, `/pnpm-lock.yaml`, `/turbo.json`) mean merges that do not touch the live server are skipped instead of rebuilt.

### DNS (`destinationpass.dev`, hosted at Vercel)

- `app` and `admin`: created automatically when attached to the Vercel projects.
- `api`: `CNAME` to Railway's target **plus** a `TXT` record `_railway-verify.api` (Railway requires both; without the TXT the certificate stays in "validating ownership").
- `live`: same pattern as `api` (`CNAME` to Railway's target plus `TXT` `_railway-verify.live`). Do **not** attach `live.destinationpass.dev` to a Vercel project; it is served by Railway.
- Existing locked records (`CAA` for pki.goog, sectigo.com and letsencrypt.org, `ALIAS`, `HTTPS`) are Vercel-managed. Leave them alone.

### GitHub (`Capitol-Interactive/DPlane`, a fork of upstream Plane)

| Branch           | Role                                                                                                             |
| ---------------- | ---------------------------------------------------------------------------------------------------------------- |
| `dev`            | Integration branch and GitHub default branch. Protected.                                                         |
| `production`     | What Railway deploys. Vercel should also use it as its Production Branch (set in each project's Settings > Git). |
| feature branches | Cut from `dev`, named `<type>/<work-item-id>-<short-description>`                                                |

`main` cannot be created: a repo ruleset blocks branches that contain merge commits, and upstream history has them.

### Planned or not yet set up

| Item                            | Status                                                       |
| ------------------------------- | ------------------------------------------------------------ |
| Email (SMTP) via Resend         | Decided, not configured. Set in the admin app under Email.   |
| `space` (public pages, SSR)     | Not deployed. Vercel preset or Railway container.            |
| Postgres backups                | Not configured. Railway does not back up volumes on its own. |
| Bucket CORS for browser uploads | Not verified. Required by Plane's storage docs.              |

## Design decisions and why

- **Split hosting.** Vercel serves the two static frontends. Railway runs everything that needs long-running processes (Celery workers, scheduler, websockets, Postgres, Redis, RabbitMQ). Vercel functions cannot run those.
- **One parent domain.** Frontends on `vercel.app` and the API on `railway.app` fail login with "CSRF Verification Failed", because the cookies are cross-site and Plane has no setting for the cookie's SameSite mode. Same-site subdomains plus `COOKIE_DOMAIN` fix it.
- **`CORS_ALLOWED_ORIGINS` also feeds CSRF.** The API builds `CSRF_TRUSTED_ORIGINS` from it. Unset means CORS allows everything but trusted origins are empty.
- **Railway Postgres, not a managed service.** It is a container with a volume: cheap and private-network, but backups and upgrades are ours.
- **Versions beyond Plane's documented defaults.** Plane documents Postgres 15.5 and Redis 7.2.4; we run 18 and 8.2. Django 5.2 supports Postgres 18 and everything works, but it is outside documented support.
- **Only `dev` and `production`.** The fork no longer keeps a `preview` mirror of upstream (removed 2026-10-08). Upstream Plane is merged straight into `dev` from a sync branch (see Common tasks), which keeps upstream changes reviewable in one PR.

## Operational gotchas

- Railway's first deployment of a service uses default settings before service config applies. Set root directory, Dockerfile and start command straight after creating it. A deployment status of `SUCCESS` only means the container started.
- Set `PORT` explicitly. Railway injected 8080 while the domain targeted 8000 (fixed with `PORT=8000`). `apps/live` has the same trap: its Dockerfile exposes 3000 but the env default is 3100, so the `live` service sets `PORT=3000`.
- Do not repeatedly remove and re-add a Railway custom domain. Let's Encrypt allows 5 duplicate certificates per domain per week.
- Add a Railway custom domain's DNS records **before** (or within seconds of) attaching it. If Railway checks before the `TXT` exists, it can stay in "validating ownership" indefinitely even after the record is correct. The fix that worked for `live`: delete the domain on Railway and re-attach it once. A re-attach can issue a **new `CNAME` target**, so update the `CNAME` to match.
- Railway rejects BuildKit cache mounts without a service-specific id prefix (`--mount=type=cache,id=pnpm-store`). `apps/live/Dockerfile.railway` is `Dockerfile.live` minus those two flags; when an upstream sync changes `Dockerfile.live`, mirror the change there.
- Never use Vercel DNS's "replace zone" operation. It overwrites the whole zone.
- New public domains are scanned within minutes (certificate transparency). Keep sign-up closed once the instance is claimed.
- Vercel Authentication protects `*.vercel.app` URLs (team login). Custom domains are public.

## Common tasks

| Task                        | How                                                                                                                                                                                                                       |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Deploy a backend change     | Merge to `production`. Railway rebuilds `api`, `worker`, `beat-worker` and `migrator` (each ~4 min); the migrator applies migrations. `live` rebuilds only when its watch patterns match; otherwise redeploy it manually. |
| Deploy a frontend change    | Merge to `production` (once Vercel's Production Branch is set).                                                                                                                                                           |
| Change a `VITE_*` value     | Edit in Vercel, then **redeploy** (values are baked in at build time).                                                                                                                                                    |
| Change an API setting       | Edit the Railway variable on the service; Railway redeploys it.                                                                                                                                                           |
| Pull upstream Plane updates | See "Pulling upstream Plane" below. Not yet rehearsed.                                                                                                                                                                    |
| Check health                | Railway: deployment status and HTTP logs per service. Vercel: deployments and build logs.                                                                                                                                 |

## Pulling upstream Plane

There is no `preview` mirror any more, so pull upstream from a sync branch cut from `dev`:

```bash
git remote add upstream https://github.com/makeplane/plane.git   # once
git fetch upstream preview
git checkout -b chore/upstream-sync-<date> origin/dev
git merge upstream/preview      # resolve conflicts here; fork-only routes live in apps/web/app/routes/extended.ts
git push -u origin chore/upstream-sync-<date>
```

Open a PR into `dev`, let CI run, then promote `dev` to `production` as usual. Not yet rehearsed: the repo ruleset
that blocks branches containing merge commits (see above) may reject the sync branch, in which case the ruleset
needs an exception for `chore/upstream-sync-*`.

## Related documentation

Plane (self-hosting):

- Overview: https://developers.plane.so/self-hosting/overview
- Email / SMTP: https://developers.plane.so/self-hosting/govern/communication
- External database and storage (env vars, bucket CORS and IAM): https://developers.plane.so/self-hosting/govern/database-and-storage
- Instance admin (sign-up, workspace and telemetry toggles): https://developers.plane.so/self-hosting/govern/instance-admin
- Authentication methods: https://developers.plane.so/self-hosting/govern/authentication

Railway:

- Custom domains (CNAME + TXT): https://docs.railway.com/networking/domains/working-with-domains#custom-domains
- SSL troubleshooting (stuck certificates): https://docs.railway.com/networking/troubleshooting/ssl
- Storage Buckets (variable references, egress, CORS): https://docs.railway.com/storage-buckets

Not fetched during setup (verify before relying on them):

- Vercel monorepos and root directories: https://vercel.com/docs/monorepos
- Vercel domains: https://vercel.com/docs/domains
- Resend SMTP: https://resend.com/docs/send-with-smtp

In this repo:

- `docker-compose.yml`: the reference topology this deployment mirrors
- `apps/api/.env.example`, `apps/web/.env.example`, `apps/live/.env.example`: variable names
- `apps/api/bin/docker-entrypoint-*.sh`: what each backend service runs at start
- `apps/api/plane/settings/common.py`: CORS, CSRF, cookie and storage settings
- `apps/api/plane/utils/instance_config_variables/core.py`: instance settings, including the SMTP keys
- `apps/web/vercel.json`, `apps/admin/vercel.json`: SPA rewrites (on branch `claude/exciting-fermi-n1g1qz`, not yet merged)
- `deployments/`: upstream's other deployment methods (CLI, Swarm, Kubernetes, all-in-one)
