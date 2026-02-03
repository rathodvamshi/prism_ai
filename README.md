# PRISM AI Studio

An end-to-end AI application suite combining a modern React/Vite frontend with a high-performance FastAPI backend, real-time token streaming (SSE), resilient state management, background processing (Celery + Redis), and deploy-ready blueprints for Render and Vercel.

---

## Table of Contents
- Overview
- Features
- Monorepo Structure
- Tech Stack
- Architecture
- Workflow
- Quick Start (Local)
- Configuration (Env Vars)
- Backend Services
- Frontend App
- Development Workflow
- Testing & Linting
- Docker & Containers
- Deployment (Render + Vercel)
- Health Checks & Ops Utilities
- Troubleshooting
- Security & Data
- Contributing
- FAQ

---

## Overview
PRISM AI Studio is built to deliver real-time, fault-tolerant AI experiences with a focus on robust generation lifecycles, cost-aware streaming, and operational visibility. The backend orchestrates model calls, streaming, persistence, and background jobs; the frontend provides a fast, polished UI built with shadcn, Tailwind, and TypeScript.

If you're new to the project, start with the architecture notes in [prism-backend/ARCHITECTURE.md](prism-backend/ARCHITECTURE.md) and the deployment walk-through in [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md).

---

## Features
- Real-time token streaming via SSE with smart buffering.
- Deterministic, state-driven generation lifecycle with idempotent operations.
- Resilient locking and recovery using Redis.
- Persistent storage in MongoDB; optional embeddings and memory via Pinecone.
- Background task processing with Celery (emails, scheduled jobs, cleanups).
- Health checks, watchdogs, and utility scripts for observability.
- Modern frontend (Vite + React + Tailwind + shadcn) ready for Vercel.
- Cloud blueprints for Render web service and worker.

---

## Monorepo Structure
- Frontend: [Frontend](Frontend)
  - Vite + React + TypeScript app, Tailwind, shadcn
  - See [Frontend/README.md](Frontend/README.md) for IDE-oriented tips
- Backend: [prism-backend](prism-backend)
  - FastAPI app under `app/` (e.g., routers, core, services)
  - Celery worker and utilities, Dockerfile, docker-compose
  - Requirements and cloud configs
- Root Ops Docs & Blueprints
  - Deployment: [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md), [render.yaml](render.yaml)
  - Backend Render: [prism-backend/render.yaml](prism-backend/render.yaml)

For deeper architecture details, read [prism-backend/ARCHITECTURE.md](prism-backend/ARCHITECTURE.md).

---

## Tech Stack
- Backend: FastAPI, Uvicorn/Gunicorn, Pydantic, Redis, MongoDB, Celery
- AI Services: Groq (primary LLM), optional Pinecone, FastEmbed
- Data & Graph: MongoDB (Motor), Neo4j
- Frontend: Vite, React 18, TypeScript, Tailwind, shadcn-ui, Radix
- Streaming: Server-Sent Events (SSE)
- Packaging: Docker, Render blueprints, Vercel (frontend)

Key backend dependencies listed in [prism-backend/requirements.txt](prism-backend/requirements.txt).

---

## Architecture

This project follows a layered architecture for clarity, testability, and operational resilience.

### Layer Overview
- Presentation (Client)
  - Technology: Vite + React + TypeScript, Tailwind, shadcn
  - Responsibilities: UI/UX, client state, SSE handling, calling API routes
  - Env: `VITE_API_URL` pointing to backend

- API Layer (FastAPI Routers)
  - Routers: streaming, chat, auth, tasks, media, health
  - Responsibilities: HTTP/SSE endpoints, validation, session/user context
  - Key files:
    - Streaming: [prism-backend/app/routers/streaming.py](prism-backend/app/routers/streaming.py)
    - Chat: [prism-backend/app/routers/chat.py](prism-backend/app/routers/chat.py)
    - Auth: [prism-backend/app/routers/auth.py](prism-backend/app/routers/auth.py)
    - Health: [prism-backend/app/routers/health.py](prism-backend/app/routers/health.py), [prism-backend/app/routers/health_llm.py](prism-backend/app/routers/health_llm.py)
    - Tasks: [prism-backend/app/routers/tasks.py](prism-backend/app/routers/tasks.py)

- Service Layer (Domain & Orchestration)
  - Responsibilities: state machine, streaming orchestration, memory ops, email, tasks
  - Highlights:
    - Generation lifecycle: [prism-backend/app/services/generation_manager.py](prism-backend/app/services/generation_manager.py)
    - Main generation: [prism-backend/app/services/main_brain.py](prism-backend/app/services/main_brain.py)
    - Input validation: [prism-backend/app/services/input_validator.py](prism-backend/app/services/input_validator.py)
    - Tasks/Email: [prism-backend/app/services/task_service.py](prism-backend/app/services/task_service.py), [prism-backend/app/services/email_service.py](prism-backend/app/services/email_service.py)
    - Memory: [prism-backend/app/services/memory_manager.py](prism-backend/app/services/memory_manager.py), [prism-backend/app/services/advanced_memory_manager.py](prism-backend/app/services/advanced_memory_manager.py)
    - Adaptive quality: [prism-backend/app/services/adaptive_quality.py](prism-backend/app/services/adaptive_quality.py)

- Data Layer (Persistence & Caching)
  - MongoDB (Motor): [prism-backend/app/db/mongo_client.py](prism-backend/app/db/mongo_client.py)
  - Redis: [prism-backend/app/db/redis_client.py](prism-backend/app/db/redis_client.py)
  - Graph (Neo4j): [prism-backend/app/db/neo4j_client.py](prism-backend/app/db/neo4j_client.py)
  - Vector (Pinecone): via services and [prism-backend/requirements.txt](prism-backend/requirements.txt)

- Integration Layer (External APIs)
  - LLM: Groq client and helpers: [prism-backend/app/utils/llm_client.py](prism-backend/app/utils/llm_client.py)
  - Email: SendGrid via [prism-backend/app/services/email_service.py](prism-backend/app/services/email_service.py)
  - Web automation: Playwright

- Background Processing
  - Celery app: [prism-backend/app/core/celery_app.py](prism-backend/app/core/celery_app.py)
  - Worker entry: Render blueprint worker in [prism-backend/render.yaml](prism-backend/render.yaml)
  - Queues: `email`, `default`

- Security & Middleware
  - Auth middleware + helpers: [prism-backend/app/middleware/auth_middleware.py](prism-backend/app/middleware/auth_middleware.py), [prism-backend/app/utils/auth.py](prism-backend/app/utils/auth.py)
  - JWT/crypto: configured via env; models under [prism-backend/app/routers/auth.py](prism-backend/app/routers/auth.py)
  - CORS: `CORS_ORIGINS` env; enforced at startup
  - Rate limiting: `slowapi` available via requirements

- Observability & Health
  - Health endpoints: [prism-backend/app/routers/health.py](prism-backend/app/routers/health.py), [prism-backend/app/routers/health_llm.py](prism-backend/app/routers/health_llm.py)
  - Utilities & checks: [prism-backend/check_api_health.py](prism-backend/check_api_health.py), [prism-backend/test_all_databases.py](prism-backend/test_all_databases.py), [prism-backend/mongodb_health_check.py](prism-backend/mongodb_health_check.py)

### Design Principles
- Deterministic state machine for generations; idempotent finalize; safe retries
- Atomic operations via Redis Lua + `SETNX` locks to prevent races
- SSE streaming with burst+flush strategy; metadata scrub before emit
- Soft timeouts (watchdog) to cancel stalled jobs and free resources
- Clear separation of concerns: routers → services → data clients → integrations

### Component Mapping
- Routers: `app/routers/*` (API surface)
- Services: `app/services/*` (business logic & orchestration)
- DB Clients: `app/db/*` (Mongo/Redis/Neo4j/http)
- Utilities: `app/utils/*` (auth, logging, retries, LLM helpers)
- Core: `app/core/*` (Celery app, shared bootstrapping)

### Request Lifecycle (Layered)
1. Client (Presentation): User submits a prompt → UI opens SSE to `/api/streaming/chat/{chat_id}/stream-now`.
2. API Layer: Router validates and resolves user context; picks API key/model.
3. Service Layer: `GenerationManager` creates state atomically; `main_brain` orchestrates model calls.
4. Streaming: SSE emits `thinking` → `ready` → `chunk` events; cancellation checked periodically.
5. Data Layer: Redis holds active state/content; on finalize, MongoDB persists messages; locks released.
6. Background: Celery tracks emails/tasks; usage tracking runs single-shot in background.
7. Observability: Health endpoints and scripts verify API/db status; soft timeouts and orphan cleanup ensure resilience.

### Deployment Architecture
- Backend API: Render web service (Gunicorn + Uvicorn) defined in [prism-backend/render.yaml](prism-backend/render.yaml)
- Background Worker: Render worker (Celery queues) also in [prism-backend/render.yaml](prism-backend/render.yaml)
- Frontend: Vercel serving `Frontend/dist`; points to backend via `VITE_API_URL`

For an extended narrative and rationale, see [prism-backend/ARCHITECTURE.md](prism-backend/ARCHITECTURE.md).

---

## Workflow

This section describes the precise generation lifecycle, endpoints, and SSE events used by the application.

### State Machine
- Statuses: `created` → `generating` → `streaming` → `completed` → `finalized` → `cleaned` (or `failed` / `cancelled`)
- Source of truth: Redis during active generation; MongoDB after finalization.
- Keys used:
  - `active_generation:{chat_id}`: currently active gen for a chat
  - `lock:{chat_id}`: short-lived lock to avoid races
  - `generation:{generation_id}`: state object
  - `generation:{generation_id}:content`: streamed content buffer
  - `cancel:{generation_id}`: fast cancellation flag
  - `usage_committed:{generation_id}`: single-shot usage tracking

Implementation in [prism-backend/app/services/generation_manager.py](prism-backend/app/services/generation_manager.py).

### Primary Endpoints
- Streaming router prefix: `/api/streaming`
  - Start+Stream immediately (SSE): `POST /api/streaming/chat/{chat_id}/stream-now`
  - Create generation (no stream): `POST /api/streaming/chat/{chat_id}/generate`
  - Finalize and persist: `POST /api/streaming/chat/{chat_id}/finalize/{generation_id}`
  - Cancel active generation: `DELETE /api/streaming/chat/{chat_id}/cancel/{generation_id}`
  - Get status for recovery: `GET /api/streaming/chat/{chat_id}/status/{generation_id}`
  - Get active generation for a chat: `GET /api/streaming/chat/{chat_id}/active`
- Health: `GET /health` (configured in Render blueprint)
- Chat management: `POST /chat/new`, `GET /chat/chats`, etc. (see [prism-backend/app/routers/chat.py](prism-backend/app/routers/chat.py))

Endpoints implemented in [prism-backend/app/routers/streaming.py](prism-backend/app/routers/streaming.py).

### SSE Event Model (Speculative Stream)
The `stream-now` endpoint emits a sequence of SSE events to provide near-zero perceived latency:
- `thinking`: sent immediately (<50ms) to show activity
- `ready`: generation is created; includes `generation_id`, `chat_id`, `model`, `key_source`
- `chunk`: streamed response content (batched and flushed for smoothness)
- `done`: generation finished; includes timing and `generation_id`
- `cancelled`: emitted if server detects cancellation
- `error`: emitted if any stream error occurs

Batching strategy: small bursts with time thresholds for smoother UI and reduced overhead. Internal metadata comments are filtered before sending.

### Typical Flows

- Start a new chat
  - Client: `POST /chat/new` → receives `chat_id`
  - Backend: stores session in MongoDB immediately

- Stream-now (combined start + stream)
  1. Client opens SSE via `POST /api/streaming/chat/{chat_id}/stream-now` with `prompt`
  2. Server emits `thinking` instantly
  3. Server validates input and resolves API key; creates generation atomically
  4. Server emits `ready` with `generation_id`
  5. Server streams `chunk` events (batched); periodically checks cancel flag
  6. On completion, emits `done` and updates status to `completed`
  7. Client calls finalize: `POST /api/streaming/chat/{chat_id}/finalize/{generation_id}` with aggregated content
  8. Backend persists user + assistant messages, marks `finalized`, triggers cleanup

- Generate then finalize (without SSE)
  1. Client: `POST /api/streaming/chat/{chat_id}/generate` → gets `generation_id`
  2. Server: creation + locking handled atomically
  3. Client can poll status or use other streaming endpoints (UI typically uses `stream-now` for the stream)
  4. Client: `POST /api/streaming/chat/{chat_id}/finalize/{generation_id}` to persist content

- Cancel
  - Client: `DELETE /api/streaming/chat/{chat_id}/cancel/{generation_id}`
  - Backend: sets fast cancel flag in Redis; stream stops; status moves to `cancelled`

- Refresh Recovery
  - Client on page refresh: `GET /api/streaming/chat/{chat_id}/active` to discover any in-progress generation
  - Client can also fetch: `GET /api/streaming/chat/{chat_id}/status/{generation_id}` for precise state
  - Backend ensures idempotency and safe lock release on terminal states

- Soft Timeout & Cleanup
  - The watchdog checks inactivity (default 30s) via `last_token_at` and cancels stalled generations
  - Finalization triggers `cleanup`, which frees Redis memory and removes locks
  - Orphan handling and stale lock cleanup are performed by background routines

Security & Idempotency:
- Ownership verified on finalize, cancel, and status endpoints
- Finalize is idempotent: duplicate calls return 200 OK and trigger cleanup safely

---

## Sequence Diagram

```text
Client (Frontend)                    Backend (FastAPI)               Redis / MongoDB
--------------------                 --------------------            ------------------------------
POST /chat/new            --->  create session (MongoDB)
                                 return chat_id

POST /api/streaming/chat/{chat_id}/generate  --->  validate, resolve key
                                                   create_generation (Lua atomic)
                                                   return generation_id

GET  /api/streaming/chat/{chat_id}/stream/{generation_id}  --->  open SSE
                                                   update_status: streaming
                                                   generate_ai_stream → chunk bursts
<=== SSE: thinking / ready / chunk / done
                                                   update_status: completed

POST /api/streaming/chat/{chat_id}/finalize/{generation_id}  --->  persist messages (MongoDB)
                                                   update_status: finalized
                                                   cleanup (free Redis; release locks)
```

---

## API Reference

- Streaming (prefix `/api/streaming`)
  - `POST /chat/{chat_id}/stream-now`: Speculative start SSE (immediate thinking → ready → chunk → done)
  - `POST /chat/{chat_id}/generate`: Create generation; returns `generation_id`
  - `GET  /chat/{chat_id}/stream/{generation_id}`: SSE stream for a given generation
  - `POST /chat/{chat_id}/finalize/{generation_id}`: Persist user + assistant messages; idempotent
  - `DELETE /chat/{chat_id}/cancel/{generation_id}`: Request cancellation
  - `GET  /chat/{chat_id}/status/{generation_id}`: Current generation status
  - `GET  /chat/{chat_id}/active`: Active generation for recovery

- Chat
  - `POST /chat/new`: Create new session; returns `chat_id`
  - `GET  /chat/chats`: List user chat sessions
  - `PATCH /chat/{chat_id}/title`: Rename chat
  - `PATCH /chat/{chat_id}/pin`: Pin/unpin session
  - `PATCH /chat/{chat_id}/save`: Save/unsave session

- Health
  - `GET /health`: API health check
  - `GET /api/streaming/quality/status`: Adaptive quality status

---

## Frontend SSE Integration (Example)

Basic pattern to stream with the GET SSE endpoint and then finalize:

```ts
// Start generation
const startGeneration = async (chatId: string, prompt: string) => {
  const res = await fetch(`${import.meta.env.VITE_API_URL}/api/streaming/chat/${chatId}/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ prompt })
  });
  const data = await res.json();
  return data.generation_id as string;
};

// Stream via SSE (GET endpoint)
const streamResponse = (chatId: string, generationId: string, onChunk: (text: string) => void) => {
  const url = `${import.meta.env.VITE_API_URL}/api/streaming/chat/${chatId}/stream/${generationId}`;
  const es = new EventSource(url, { withCredentials: true });

  es.addEventListener('chunk', (e) => {
    const payload = JSON.parse((e as MessageEvent).data);
    onChunk(payload.content);
  });

  es.addEventListener('done', () => {
    es.close();
  });

  es.addEventListener('cancelled', () => es.close());
  es.addEventListener('error', () => es.close());
  return es;
};

// Finalize (persist messages)
const finalizeGeneration = async (chatId: string, generationId: string, finalContent: string) => {
  await fetch(`${import.meta.env.VITE_API_URL}/api/streaming/chat/${chatId}/finalize/${generationId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ final_content: finalContent })
  });
};
```

Speculative streaming (`stream-now`) uses `POST` + SSE; for clients, prefer the GET SSE endpoint above or use a `fetch()` stream reader if you need speculative start.

---

## Quick Start (Local)

### Prerequisites
- Node.js ≥ 18 (see [package.json](package.json))
- Python 3.10+ (Dockerfile uses 3.10; local dev works on 3.10/3.11)
- MongoDB & Redis (local or cloud)

### Start Frontend (Dev)
```bash
cd Frontend
npm install
npm run dev
```

### Start Backend (Dev)
```bash
cd prism-backend
python -m venv .venv
.venv\\Scripts\\activate   # Windows
pip install -r requirements.txt

# Create a .env with the required variables (see below).

# Run FastAPI locally
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# (Optional) Run Celery worker
celery -A app.core.celery_app worker --loglevel=info --queues=email,default
```

### Local Services
- Redis: Install locally or use Docker (`docker-compose up redis` inside backend directory).
- MongoDB: Local install or Atlas connection.

---

## Configuration (Env Vars)
Set these environment variables (locally via `.env`, on cloud via dashboard or blueprint):

- Core
  - `ENVIRONMENT`: `development` or `production`
  - `CORS_ORIGINS`: Allowed frontend origins (comma-separated)
- Persistence & Memory
  - `MONGO_URI`: MongoDB connection string
  - `REDIS_URL`: Redis connection URL
  - `PINECONE_API_KEY`, `PINECONE_INDEX_NAME` (optional)
- AI Services
  - `GROQ_API_KEY`: Groq API key (primary LLM)
- Graph DB (optional)
  - `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`
- Security (cloud will generate if using Render blueprint)
  - `JWT_SECRET`, `ENCRYPTION_KEY`
- Email & Tasks
  - `SENDGRID_API_KEY`, `SENDER_EMAIL`
  - `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` (often same as `REDIS_URL`)

See backend blueprint in [prism-backend/render.yaml](prism-backend/render.yaml) and root [render.yaml](render.yaml) for a complete list.

---

## Backend Services
- API Service: FastAPI app entry at `app.main:app` (local: `uvicorn app.main:app --reload`)
- Background Worker: Celery app at `app.core.celery_app` (queues: `email`, `default`)
- Data Stores: MongoDB (Motor client), Redis (locks, cache, celery), optional Neo4j
- Streaming: SSE endpoints for real-time token delivery

Container configs:
- Dockerfile: [prism-backend/Dockerfile](prism-backend/Dockerfile)
- Compose: [prism-backend/docker-compose.yml](prism-backend/docker-compose.yml)

---

## Frontend App
- Vite + React + TypeScript with Tailwind and shadcn
- Scripts:
  - Dev: `npm run dev`
  - Build: `npm run build`
  - Preview: `npm run preview`
- Root scripts proxy to Frontend:
  - `npm run dev` (from repo root) runs Frontend dev
  - `npm run build` (from repo root) builds Frontend
  - `npm run start` (from repo root) previews Frontend

See [Frontend/package.json](Frontend/package.json) and [Frontend/README.md](Frontend/README.md).

---

## Development Workflow
- Use feature branches; keep commits scoped and descriptive.
- Run the frontend and backend locally; point frontend to backend via `VITE_API_URL`.
- Keep `.env` values out of commits; use secrets managers on cloud.
- Monitor backend logs for streaming and task events.

---

## Testing & Linting
- Frontend: `npm run lint` (see [Frontend/package.json](Frontend/package.json))
- Backend: ad-hoc test utilities exist (e.g., [prism-backend/test_all_endpoints.py](prism-backend/test_all_endpoints.py), [prism-backend/test_all_databases.py](prism-backend/test_all_databases.py)); run them under an activated venv.

---

## Docker & Containers
Run backend stack with Redis and workers via compose:
```bash
cd prism-backend
docker-compose up --build
```

This brings up:
- `prism-api` on port `8000`
- `prism-celery` worker
- `redis`

---

## Deployment (Render + Vercel)
End-to-end deployment guidance is in [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md).

### Backend on Render
- Blueprint: [prism-backend/render.yaml](prism-backend/render.yaml)
- Web service start: Gunicorn + Uvicorn workers
- Worker: Celery (`email,default` queues)
- Required env vars are defined in the blueprint with `sync:false` or `generateValue`.

### Frontend on Vercel
- Project root: `Frontend`
- Build command: `npm run build`
- Output dir: `dist`
- Set `VITE_API_URL` to the Render backend URL; update backend `CORS_ORIGINS` accordingly.

---

## Health Checks & Ops Utilities
- API Health: `/health` endpoint (see [prism-backend/health_check.py](prism-backend/health_check.py))
- System & DB checks: [prism-backend/check_api_health.py](prism-backend/check_api_health.py), [prism-backend/test_all_databases.py](prism-backend/test_all_databases.py), [prism-backend/mongodb_health_check.py](prism-backend/mongodb_health_check.py)
- Task queue scripts: start/stop Celery ([prism-backend/start_celery_worker.bat](prism-backend/start_celery_worker.bat), [prism-backend/start_celery_beat.bat](prism-backend/start_celery_beat.bat))
- Cleanup utilities: [prism-backend/cleanup_highlights.py](prism-backend/cleanup_highlights.py), [prism-backend/cleanup_highlights_pro.py](prism-backend/cleanup_highlights_pro.py)

---

## Troubleshooting
- Frontend cannot reach API:
  - Verify `VITE_API_URL` and backend `CORS_ORIGINS`.
  - Check that API `/health` returns 200.
- Celery tasks not running:
  - Confirm `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND` point to Redis.
  - Check worker logs; ensure queues `email,default` are declared.
- Streaming stalls:
  - Inspect Redis locks/state; verify soft timeout watchdog.
  - Confirm model provider API key and quota.

---

## Security & Data
- Secrets must not be committed; use env vars and cloud secret stores.
- JWT and encryption keys are auto-generated in Render via blueprint.
- Validate and sanitize payloads; see architecture notes for non-blocking security checks.

---

## Contributing
- Open issues with clear reproduction steps and context.
- Keep PRs focused; add or update docs where behavior changes.
- Align with existing code style and organization.

---

## FAQ
- Can I run only the frontend locally?
  - Yes. Use `npm run dev` in `Frontend` and point to a deployed backend via `VITE_API_URL`.
- Do I need Docker to develop?
  - No. Docker is optional; helpful for parity and running Redis quickly.
- Which Node version?
  - Node ≥ 18 (see [package.json](package.json)).
- Which Python version?
  - 3.10+ (Dockerfile uses 3.10). 3.11 is typically fine.

---

For deeper details and operational guides, see:
- Architecture: [prism-backend/ARCHITECTURE.md](prism-backend/ARCHITECTURE.md)
- Deployment: [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
- Backend Blueprint: [prism-backend/render.yaml](prism-backend/render.yaml)
- Root Render Config: [render.yaml](render.yaml)