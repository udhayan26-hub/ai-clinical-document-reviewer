# 006. Deployment: Docker-first locally, AWS deferred, environment-branch mapping

## Problem

The finished application must eventually run publicly on AWS, while local development must not depend on AWS being reachable, and the branch strategy (`main`/`staging`/`dev`) needs a clear (even if not-yet-automated) relationship to deployment environments.

## Decision

- Local development runs entirely via Docker Compose (`docker-compose.yml`: `frontend`, `backend`, `db` services) — no AWS dependency to develop or run tests locally.
- Each service ships its own `Dockerfile` (`backend/Dockerfile`, `frontend/Dockerfile`) so the same container images that run locally are the ones that would be deployed, rather than maintaining a separate "production build" path.
- Branch → environment mapping is: `dev` (integration, maps to a future dev/preview environment), `staging` (pre-production validation), `main` (production, deployable). See `README.md` "Branching Strategy".
- AWS infrastructure specifics (which compute service, networking, CI/CD deployment automation) are explicitly **deferred** and will be recorded in `infrastructure/` and a future decision record once undertaken — this record only commits to the container-first shape that makes that later decision tractable.

## Rationale

- Containerizing both services now, even before AWS work begins, means "how does this get deployed" doesn't require re-architecting the app later — it requires choosing where to run an existing container, not building a container story from scratch under deployment pressure.
- Keeping local development AWS-independent (Docker Compose + local Postgres) means contributors don't need cloud credentials to build or test the application, and CI (`.github/workflows/ci.yml`) can run without any cloud dependency either.
- The `feature/* → dev → staging → main` flow gives a natural place to eventually attach environment-specific deploys (e.g. `dev` auto-deploys to a dev environment, `main` deploys to production) without requiring separate repositories per environment, which the assignment explicitly asked to avoid.

## Alternatives Considered

- **Deciding the specific AWS compute target now** (e.g. ECS/Fargate vs. Elastic Beanstalk vs. EC2 vs. App Runner) — deferred rather than decided, since committing to a specific service without the workload's actual requirements (the AI pipeline isn't built yet, so its resource/latency profile is unknown) risks a premature, hard-to-justify choice. This will be its own decision record when AWS work starts.
- **Serverless-first (Lambda) backend** — not ruled out, but deferred for the same reason: FastAPI's request/response model and the (future) potentially long-running document/AI processing steps need to be understood before picking a compute model that has cold-start and execution-time implications.
- **Deploying straight from a developer machine / no containers** — rejected: would mean the local dev environment and any deployed environment could silently diverge, defeating the point of Docker Compose existing at all.

## Trade-offs

- No deployment URL, environment, or infrastructure-as-code exists yet — this is accurate to the current phase (architecture/contracts only) and is tracked as pending in the README roadmap, not silently glossed over.
- Deferring the AWS compute decision means today's Docker setup is a *necessary* but not *sufficient* condition for deployment — some adaptation (env var wiring, secrets management, networking) should be expected when that phase begins, but the container boundary itself should not need to change.
- No cost or performance claims are made about any future AWS setup here; none have been evaluated.
