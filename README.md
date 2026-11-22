# 42 Team Finder

A local, production-oriented dashboard for discovering 42 Network students who may need a team and teams that may have capacity. It uses the official 42 API through a credential-protected FastAPI backend; the browser never receives the client secret.

The application runs in **demo mode automatically** when credentials are absent. Demo mode exercises the real database, background scan, filtering, classification, pagination, and export paths with clearly labeled fixtures. It must not be mistaken for live 42 data.

## Start

Requirements: Docker with Compose.

```bash
cp .env.example .env
# Add FT_CLIENT_ID and FT_CLIENT_SECRET for live API data, or leave blank for demo mode.
make up
```

`make up` is the primary startup command. It creates `.env` from `.env.example` when missing, builds both containers, starts them in the background, and preserves an existing `.env` containing your credentials. Run `make help` to see the stop, rebuild, logs, status, and test commands. The equivalent command without Make is `docker compose up --build -d`.

Open [http://localhost:3000](http://localhost:3000) locally. Backend API documentation is available inside the Compose network and, for development, at `http://localhost:8000/docs` when the backend port is published manually.

## Project matchmaking

After a verified 42 sign-in, **Discover** is the primary experience. It shows only people who are present in the same completed, eligible project scan and who have opted into a visible local profile. Passes and interests are stored per project; a match is created only when both students choose Interested for that exact project. **Explore** keeps the original scan dashboard and is where an eligibility scan is started.

Profiles, swipes, matches, local planning teams, invitations, and notifications live in SQLite alongside scan history. They are deliberately separate from official 42 Intra teams: creating or accepting a platform team never writes to the 42 API. A member's editable contact field is revealed only to mutual matches. The scanner remains the source of truth for eligibility, and no missing scan/API record is interpreted as eligibility.

The forward-only SQLite schema change is recorded in [backend/migrations/001_matchmaking.sql](backend/migrations/001_matchmaking.sql). Normal Compose startup applies missing SQLAlchemy tables non-destructively; do not delete the named volume when upgrading an active instance.

To stop:

```bash
docker compose down
```

SQLite data is kept in the named `team_finder_data` volume. Use `docker compose down -v` only when you intentionally want to erase scan history and cache data.

## Free private hosting

The simplest safe zero-cost option is to keep the Docker Compose application on one always-on computer and publish it privately with [Tailscale Serve](https://tailscale.com/docs/use-cases/application-testing/share-local-dev-server-with-team). This preserves SQLite and avatar-cache data on that computer and does not expose student records to the public internet.

1. Install Tailscale on the host and sign in with a personal account.
2. Invite the people who should have access to the same tailnet and have them install Tailscale.
3. Start this application, then publish port 3000 in the background:

```bash
docker compose up --build -d
tailscale serve --bg 3000
```

Tailscale prints a private `https://<machine>.<tailnet>.ts.net` URL. Check or remove the share with:

```bash
tailscale serve status
tailscale serve reset
```

The free Personal plan currently supports up to six users. For a short external demonstration without requiring visitors to install Tailscale, a Cloudflare Quick Tunnel can provide a temporary URL and email verification:

```bash
cloudflared tunnel --url http://localhost:3000 --allowed-mail you@example.com
```

Quick Tunnel URLs change when restarted and are intended for testing, not permanent production hosting. A campus-wide public deployment needs application authentication, scan quotas, and a retention policy before it should be exposed.

### Oracle Cloud Always Free VM

For a persistent public demo, the same Compose stack runs on an Always Free-eligible
Ampere A1 VM. Keep the shape marked **Always Free-eligible**, keep total boot/block
storage within Oracle's Always Free allowance, and do not upgrade the account. On
the VM, use these additional `.env` values so the app listens on normal HTTP and
paces requests below 42's burst limiter:

```dotenv
FRONTEND_PORT=80
CORS_ORIGINS=http://YOUR_SERVER_IP
API_CONCURRENCY=4
API_MIN_INTERVAL_SECONDS=0.6
```

Open inbound TCP 80 publicly, restrict TCP 22 to your own IP address, install
Docker with its Compose v2 plugin, and run `make up`. HTTPS and access control
should be added before sharing student data beyond a trusted group.

## 42 student access control

The application includes a server-side **Continue with 42** login. It uses the
OAuth authorization-code flow and then calls `GET /v2/me`; an account must have
at least one `cursus_users` enrollment to receive a session. The 42 access token
is discarded after this identity check. Browsers receive only an opaque,
HTTP-only session cookie stored as a hash in SQLite; logout revokes it.

To enable it for a public instance:

1. In the 42 application's settings, add this exact Redirect URI:
   `https://YOUR_DOMAIN/api/auth/callback`.
2. Set these environment values and redeploy:

```dotenv
PUBLIC_BASE_URL=https://YOUR_DOMAIN
AUTH_REQUIRED=true
SESSION_COOKIE_SECURE=true
```

The server's current bare `http://IP` address is unsuitable for a production
login: `SESSION_COOKIE_SECURE` must remain false over HTTP, which leaves a
session vulnerable on untrusted networks. Put the app behind a free HTTPS
endpoint (for example Cloudflare with a domain you control, or Tailscale Serve
for a private group) before enabling public authentication. Once
`AUTH_REQUIRED=true`, all data and scan endpoints return `401` until the user
has signed in; `/api/health` and the OAuth handshake remain reachable.

For the included Oracle deployment, use the public Compose profile. Point an
`A` record for your domain at the VM, set `PUBLIC_BASE_URL` to that HTTPS
domain, and add `${PUBLIC_BASE_URL}/api/auth/callback` to the 42 OAuth
application redirect URIs. Caddy obtains and renews the Let's Encrypt
certificate automatically:

```bash
FRONTEND_PORT=3000 HTTP_PORT=80 HTTPS_PORT=443 docker compose --profile public up --build -d
```

Allow inbound TCP 80 and 443 in both the Oracle security list and host firewall.

## 42 API credentials

Create an OAuth application in your 42 profile and put its UID and secret in `.env`:

```dotenv
FT_CLIENT_ID=your_application_uid
FT_CLIENT_SECRET=your_application_secret
```

The backend uses the OAuth2 client-credentials grant, renews expiring tokens, handles pagination, bounds concurrency, retries transient failures, respects `Retry-After`, and uses request timeouts. Credentials are environment-only and are not persisted.

42's CDN requires the same bearer token for many student photos. The browser therefore loads official CDN photos through the same-origin `/api/avatars` backend endpoint. The endpoint only accepts `https://cdn.intra.42.fr` URLs, never exposes the token, validates image type and size, and caches downloaded photos in the persistent data volume. Failed images fall back to student initials.

## How classification works

Promotion definitions are deliberately local and auditable:

- **Cursus enrollment year:** year of the selected user's most recent active cursus enrollment (`cursus_users.begin_at`, falling back to the most recent enrollment).
- **Piscine year/month:** exact `pool_year` plus case-insensitive `pool_month` match.
- **Enrollment date range:** inclusive dates applied to the same cursus enrollment date used above.

Student status:

- `searching_group`: the project registration explicitly returns `searching_a_group` and complete team data has no active membership.
- `registered_without_team`: a non-completed project registration exists and complete team data has no active membership.
- `not_registered`: no project registration and complete team data has no active membership.
- `uncertain`: team retrieval was partial/unavailable. Missing data is never used as proof of no team.
- `active_team` / `completed`: hidden by default; available with the advanced checkbox.

Students are excluded for black-hole status only when the selected cursus has a completed lifecycle transition whose `end_at` closely matches its `blackholed_at` deadline. A deadline alone is not treated as proof: 42 can retain a past `blackholed_at` value for active Cadets. The scan summary and warnings disclose the confirmed exclusion count.

Project mode and team-size defaults:

- The app reads the selected campus's project session from `GET /v2/projects/:id` and then its rules from `GET /v2/project_sessions/:id`.
- A session marked `solo` switches the result view to **Students working on this project**, fixes the target size at one, and skips team lookups.
- For group projects, `GroupSizeBetweenNAndM` rules are used when present; otherwise the documented session `max_people` is used. The official maximum becomes the default, while the user can lower or raise the search target deliberately.
- If neither field is supplied by 42, the UI says so and uses a conservative fallback of five rather than claiming an official maximum.

Team availability:

- `confirmed_joinable`: narrowly reserved for an API-unlocked team in `creating_group` with room below the user-selected size target.
- `potential_capacity`: member count is below the chosen target, but the API does not explicitly confirm that the team can be joined.
- `unavailable`: closed, completed, validated, marked, or at the selected target.

The target size is a search preference, not necessarily the project's official maximum. “Potential spots” are therefore capacity estimates and are never presented as universally confirmed joinable.

## API usage and verified assumptions

The implementation uses documented collection routes:

- `GET /v2/campus` for campus metadata
- `GET /v2/projects` for project metadata
- `GET /v2/cursus_users` with campus, cursus, and enrollment-window filters for cursus-year/date promotions
- `GET /v2/campus/:campus_id/users` for Piscine cohorts
- `GET /v2/projects_users` with documented project/user filters, in bounded batches
- `GET /v2/teams` filtered by team IDs referenced in the cohort registrations, for complete memberships
- `GET /v2/projects/:id` and `GET /v2/project_sessions/:id` for campus-specific solo and group-size rules

The official team representation documents `status`, `users`, `locked?`, `validated?`, and `closed?`. Because no universal “joinable” field is documented, only the conservative unlocked/creating-group combination is labeled confirmed; all ordinary size-based openings remain potential. See the [official 42 API documentation](https://api.intra.42.fr/apidoc/2.0.html).

Live response structures were verified on 2026-11-20 with valid client credentials using read-only Paris 2024 scans: `ft_transcendence` resolved to an official 4–5 member range and Libft resolved as solo. The real scans also verified black-hole exclusions and completed successfully. API changes or application permission differences surface as recoverable scan warnings/errors rather than false classifications.

## Architecture

```text
frontend (React + TypeScript + Vite + Tailwind + shadcn-style Radix primitives)
    │ /api via same-origin nginx proxy
backend (FastAPI + Pydantic v2 + HTTPX)
    ├── OAuth/token and resilient 42 API client
    ├── persisted background scans and evidence-aware classifier
    └── SQLAlchemy 2 async repositories
         └── SQLite cache, scan history/results, saved searches
```

Backend modules live under `backend/app/{api,core,models,repositories,schemas,services}`. The frontend is split into pages, reusable components, API services, and shared types. Nginx serves the production Vite build on port 3000 and proxies API traffic privately to FastAPI.

## Development and tests

Run everything in containers so Python 3.12 and Node 22 match production:

```bash
docker build -t team-finder-backend-test -f backend/Dockerfile backend
docker run --rm --user root -e PYTHONPATH=/app -v "$PWD/backend:/app" -w /app team-finder-backend-test sh -c "pip install -r requirements-dev.txt && pytest -q"

docker build --target build -t team-finder-frontend-test frontend
docker run --rm team-finder-frontend-test npm test -- --run
docker run --rm team-finder-frontend-test npm run lint
docker run --rm team-finder-frontend-test npm run build
```

Backend tests cover OAuth reuse, complete pagination, retry-after rate limiting, duplicate records, all promotion definitions, partial team data, completed records, membership/classification, persistence, filtering, validation, and CSV/JSON exports. Frontend tests cover filter submission, student search/detail rendering, and joinability-safe team labels.

## Operational and privacy limitations

- Background work uses in-process tasks and persisted status, appropriate for a single local backend replica. Use a durable job queue before horizontal scaling.
- SQLite is appropriate for local/small-team use, not a high-write public service.
- Saved-search persistence exists in the API; the local UI prioritizes automatically restoring the most recent filters.
- Local mode leaves authentication disabled by default. Public deployments should enable the included 42 student login, use HTTPS, and retain scan data only as long as necessary.
- The 42 API does not expose a single, documented, universal statement that a team accepts new members. Capacity and joinability remain explicitly separate.
