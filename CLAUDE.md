# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

AthleteFlow v1.0 — a multi-tenant SaaS web application for sports team training management. Solo developer + Claude Code build. Target launch Q3 2026.

*** project documents ***
/prj/coruscant/athlete_manager_v2/documents/docs
- api_spec.md
- arch_overview.md
- critical_user_flow.md
- data_model.md
- prod_req_doc.md
- system_design.md
- test_strat.md
- file_system.md

*** deliverables and timeline ***
/prj/coruscant/athlete_manager_v2/documents/docs
- deliverables.md

## Stack

| Layer      | Technology |
|------------|------------|
| Backend | FastAPI (Python 3.12) |
| Frontend | React 18 (TypeScript) + Tailwind CSS |
| Database | PostgreSQL 16 — schema-separated multi-tenancy |
| Migrations | Alembic |
| Auth | DB sessions at launch; planned Auth0 migration post-v1.0 |
| CI/CD | GitHub Actions |

## Ports (local)

| Service | Host port |
|---|---|
| PostgreSQL | 20301 |
| Backend API | 20310 |
| Frontend | 20305 |

## Commands

### Backend (run from `backend/`)

```bash
pip install -e ".[dev]"          # install with dev dependencies
uvicorn app.main:app --reload    # run dev server on :8000
pytest                           # run all tests
pytest tests/unit/test_security.py                  # run a single test file
pytest tests/integration/test_auth.py::test_login   # run a single test
pytest --cov=app --cov-report=term-missing          # with coverage
ruff check .                     # lint
ruff format .                    # format
```

### Frontend (run from `frontend/`)

```bash
npm install
npm run dev          # Vite dev server on :5173
npm run build        # tsc --noEmit then vite build
npm run lint         # eslint
npx playwright test  # run E2E tests
npx playwright test e2e/auth.spec.ts   # run a single E2E file
```

### Docker

```bash
cp .env.example .env             # first time only — fill in SECRET_KEY
docker-compose up --build        # boot postgres + backend + frontend
docker-compose up athlete_db     # boot only the database (for local backend dev)
```

## Architecture

### Multi-tenancy

The entire isolation model rests on PostgreSQL schemas. There is a `public` schema for global tables and a `tenant_{slug}` schema per tenant for all domain data. Every authenticated request sets `search_path = tenant_{slug}` before any query runs. This is handled by the `set_tenant_schema` FastAPI dependency in `backend/app/dependencies.py`.

Never query tenant-schema tables without `set_tenant_schema` in the dependency chain.

### Backend layout

```
backend/app/
├── main.py          # FastAPI app instance, middleware, router registration
├── config.py        # pydantic-settings — reads all env vars
├── database.py      # SQLAlchemy engine + session factory
├── dependencies.py  # get_current_user, set_tenant_schema, require_role — used on every protected route
├── api/v1/          # one file per domain (auth, admin, users, athletes, teams, exercises, plans, activity_logs)
├── models/
│   ├── public/      # global schema: tenants, user_identities, sessions, password_reset_tokens
│   └── tenant/      # per-tenant schema: users, athlete_profiles, teams, exercises, training_plans, plan_activities, activity_logs
├── schemas/         # Pydantic request/response models
├── services/        # business logic — no HTTP, no DB sessions; receive session as parameter
└── utils/
    ├── security.py  # hash_password, verify_password, generate_token, hash_token
    └── tenant.py    # slug_to_schema_name, derive_slug
```

Services contain no FastAPI or SQLAlchemy session imports — they receive a DB session as a parameter, making them unit-testable without spinning up the app or a database.

### Authentication flow

```
POST /auth/login → resolve public.user_identities by email
               → verify password_hash
               → SET search_path = tenant_{slug}
               → load tenant users row (role)
               → insert public.sessions (hashed token)
               → return raw token to client
```

Subsequent requests: `get_current_user` reads the `Authorization: Bearer` header, hashes the token, looks it up in `public.sessions`, then loads the user. `set_tenant_schema` fires next, then `require_role` if the route restricts by role.

### Roles

Four roles exist within a tenant schema: `tenant_admin`, `coach`, `trainer`, `athlete`. A fifth identity — `saas_admin` — is not stored in any tenant schema; it is identified by matching `SAAS_ADMIN_EMAIL` at login.

### Frontend layout

```
frontend/src/
├── api/          # typed fetch functions — all HTTP calls go through api/client.ts
├── components/   # reusable UI: ActivityCard, ActivityStatusBadge, DateNavigator, EmptyState
├── contexts/     # AuthContext — session state, login/logout
├── hooks/        # useAuth
├── layouts/      # AppShell — auth guard + role-based route protection
├── pages/        # one file per route
└── types/        # shared TypeScript interfaces
```

`api/client.ts` is the sole fetch entry point. It attaches the `Authorization` header and handles 401s. No page or component calls `fetch` directly.

### VITE_API_URL

This variable is baked into the bundle at `vite build` time. In docker-compose it is passed as a build `arg`, not a runtime env var. For local `npm run dev`, set it in `frontend/.env.local`.

### Alembic

Migrations are split into two directories:
- `backend/alembic/versions/public/` — run once at deploy; creates global schema tables
- `backend/alembic/versions/tenant/` — run as a template each time a new tenant is provisioned via `POST /api/v1/admin/tenants`

### Testing

Integration tests require a real PostgreSQL instance — no mocking the database. Each integration test suite provisions its own tenant schema and tears it down after the run. The test DB connection string is set in `backend/tests/conftest.py`.

E2E tests live in `frontend/e2e/` and run via Playwright against the full running stack. Seed data is in `frontend/e2e/fixtures/seed.py`.
