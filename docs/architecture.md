# Hosted Workflow Baseline

- Backend: FastAPI + Uvicorn
- Session store: Redis with TTL
- Order store: PostgreSQL
- Trace replay: `agent_events` table + JSONL logs
- Contract: OpenAPI exported to `backend/openapi/openapi.json`
- Frontend type source: generated from OpenAPI into `frontend/src/generated/api-types.ts`
