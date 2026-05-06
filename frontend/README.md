# Olho Regional (Frontend)

Nuxt 4 app with Vuetify 3, GSAP, and Drizzle ORM over Turso (libSQL). Browsable catalog of 600+ Portuguese regional newspapers and their archived articles.

## Quick Start

```bash
yarn install
yarn dev               # http://localhost:3000
```

No import step needed for local dev — the dev server reads `../processamento/database/olho-regional.db` directly via `@libsql/client` (file driver).

## Scripts

| Command | Description |
|---|---|
| `yarn dev` | Start Nuxt dev server (reads local SQLite) |
| `yarn build` | Build for Cloudflare Pages (production) |
| `yarn preview` | Build + preview locally via `wrangler pages dev` |
| `yarn deploy` | Build + deploy to Cloudflare Pages |
| `yarn db:deploy` | Upload local DB to Turso (destroy + recreate, no row writes) |
| `yarn db:stats` | Show total row count (estimate Turso impact) |
| `yarn analises:compile` | Compile analysis source JSONs into data-baked versions |

## How It Works

In **development**, `server/utils/db.ts` uses `@libsql/client` with a `file:` URL pointing to `../processamento/database/olho-regional.db` — instant startup, no import needed.

In **production**, the server uses a failover strategy:
1. **VPS (full DB)** — tries `VPS_DATABASE_URL` first with a `SELECT 1` health check
2. **Turso (lite DB)** — falls back automatically if the VPS is unreachable

The failover check runs on each Worker cold start (~every 30s of inactivity). If the VPS goes down mid-session, queries that fail are retried against Turso automatically.

A `<DbSourceChip>` in the footer shows which database is active:
- 🟢 **BD completa** — VPS (full dataset)
- 🟡 **BD lite** — Turso (limited dataset)

## Database: Turso (libSQL)

### Setting up Turso (one-time)

```bash
# Install the CLI
curl -sSfL https://get.tur.so/install.sh | bash

# Login
turso auth login

# Create a database (IRE is closest to Portugal)
turso db create olho-regional --location aws-eu-west-1

# Get the connection URL
turso db show olho-regional --url
# → libsql://olho-regional-<your-org>.turso.io

# Create an auth token
turso db tokens create olho-regional
```

### Uploading the database

Uses `--from-file` to replace the database from the local SQLite file (no per-row write operations):

```bash
yarn db:deploy
# This destroys and recreates the DB, then you must regenerate the auth token:
turso db tokens create olho-regional
# Update the TURSO_AUTH_TOKEN secret in CF Pages dashboard
```

> **Note:** `db:deploy` destroys and recreates the database to avoid per-row writes
> against Turso's billing quota. The trade-off is you need to update the auth token
> in Cloudflare Pages after each deploy. Use `yarn db:stats` to check total row count.

### Configuring Cloudflare Pages

Environment variables in `wrangler.toml` under `[vars]` (plain text, committed):
- `VPS_DATABASE_URL` — your self-hosted libSQL URL (e.g. `https://olho-regional.lubina.org`)
- `TURSO_DATABASE_URL` — Turso fallback URL

**Secrets** (add in CF Pages dashboard → Settings → Environment Variables → Production):
- `VPS_AUTH_TOKEN` — JWT key for your VPS sqld instance
- `TURSO_AUTH_TOKEN` — Turso database auth token

### Rebuilding the database from scratch

```bash
cd ../processamento/database
python scripts/insert_data.py
# Dev server will pick up the new data on next request

# To update Turso after rebuild:
yarn db:deploy
turso db tokens create olho-regional
# Update TURSO_AUTH_TOKEN secret in CF Pages dashboard
```

## Production Deployment (Cloudflare Pages)

### Analysis Pages

Analysis pages are driven by JSON files in `public/analises/`. See [`public/analises/README.md`](public/analises/README.md) for the full schema.

**Development workflow:**
1. Edit `public/analises/<id>.json` — define filters and viz types
2. Visit `http://localhost:3001/analises/<id>` — data compiles on the fly from the local DB
3. Save the JSON → refresh to see changes immediately

**Deploy workflow:**
1. With the dev server running, run `yarn analises:compile`
2. This queries the API and writes `public/analises/_compiled/<id>.json` with all data baked in
3. In production, the server serves the compiled version (no DB queries needed for analyses)

### CI/CD via GitHub Actions

Add these secrets in your GitHub repo settings (Settings → Secrets → Actions):

- `CLOUDFLARE_API_TOKEN` — create at dash.cloudflare.com/profile/api-tokens with "Cloudflare Pages:Edit" permissions
- `CLOUDFLARE_ACCOUNT_ID` — found on your Cloudflare dashboard

## Stack

- **Nuxt 4** — SSR framework
- **Vuetify 3** — Material Design components (via `vuetify-nuxt-module`)
- **GSAP** — Animations (client-only plugin)
- **Drizzle ORM** — Type-safe SQL over libSQL
- **Turso** — Managed libSQL database (fallback / lite version)
- **Self-hosted libSQL (sqld)** — Full database on VPS via Docker + Caddy + Cloudflare proxy
- **Cloudflare Pages** — Hosting
- **Wrangler** — Cloudflare local dev + deployment tool
