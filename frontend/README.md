# ThinkingSOC Frontend (Hackathon)

External analyst UI for the Splunk hackathon demo: NeonGlass theme, [Animate UI](https://animate-ui.com/) components, and FastAPI backend proxy.

## Prerequisites

- Node.js 20+
- Backend running at `http://127.0.0.1:9876` (see `backend/README.md`)
- PostgreSQL configured on the backend for inventory and stored analysis (`TSOC_POSTGRES_DSN`)
- Matching `TSOC_INGEST_TOKEN` on backend and frontend (if ingest protection is enabled)

## Setup

```bash
cd frontend
cp .env.example .env.local
npm install
npm run build
npm run start
```

After `install.sh`, the stack uses **production** mode (`npm run start`), not `npm run dev`. Use `npm run dev` only for local UI development with hot reload.

Open the app at the host root only (no path required):

- Local: [http://localhost:3000/](http://localhost:3000/)
- LAN / DNS: `http://<server-ip-or-dns>/` (frontend listens on `0.0.0.0:3000`)

Unauthenticated visits redirect to `/login`; signed-in users go to `/dashboard`.

**Demo login:** `admin` / `123456@a`

## Pages

| Route | Purpose |
|-------|---------|
| `/login` | Demo authentication |
| `/dashboard` | Overview and navigation |
| `/inventory` | Users & assets CRUD |
| `/identity-rules` | Identity rule editor |
| `/analysis` | Triage queue + stored SOC/Ops events |
| `/analysis/investigation/[id]` | Security investigation (overview, recommended action, hunter & defender, enrichment, **Admin question** tab when org gap is suggested) |
| `/analysis/ops-investigation/[id]` | Observability investigation detail |
| `/splunk-connection` | LLM, MCP, integration settings |

## Architecture

- **Auth:** HttpOnly `tsoc_session` cookie; credentials validated server-side only.
- **API:** Browser calls `/api/backend/*`; Next.js forwards to FastAPI with `Authorization: Bearer $TSOC_INGEST_TOKEN` (never sent to the client).

## Build

Same as production run (`package.json` maps `start` → `next start -H 0.0.0.0 -p 3000`):

```bash
npm run build
npm run start
```
