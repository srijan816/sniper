# Production Infrastructure Research

**AI-Q Job:** `ff3cce5e-a6ed-40f2-9186-7d0f92e3e570`  
**Applied automatically by SniperIP research loop**

---

# Production Deployment Architecture for an IP Protection SaaS

## Next.js + FastAPI + Celery + Redis + Supabase/pgvector + HuggingFace SigLIP/DINOv2

**Date:** June 2026 | **Target Scale:** 100–1,000 clients | **Stack:** Next.js 14+ (standalone output), FastAPI (Uvicorn), Celery 5.x, Redis 7+, Supabase (pgvector 0.7+), HuggingFace Inference Endpoints (SigLIP + DINOv2)

---

## Executive Summary

For an IP protection SaaS in the 100–1,000 client range, the recommended production architecture is:

- **Platform:** Railway Pro (single-region default), with Fly.io as the multi-region/low-latency fallback
- **Worker topology:** Three dedicated Celery queues (discovery, vectorize, takedown) with KEDA-driven autoscaling
- **Redis:** Upstash Redis or Redis Cloud with AOF + RDB persistence and `allkeys-lru` eviction
- **Embedding pipeline:** HuggingFace Inference Endpoints (Dedicated tier, L4 GPU) for SigLIP + DINOv2
- **Database:** Supabase Pro ($25/mo) with pgvector HNSW indexes, migrating to a managed Postgres (Neon/RDS) above ~500 clients or 10M+ vectors
- **Secrets:** Doppler for teams; Kubernetes Secrets or AWS Secrets Manager on EKS
- **Estimated cost:** ~$483/month at 100 clients (~$4.83/client); ~$3,065/month at 1,000 clients (~$3.07/client)

The architecture is intentionally bounded: Railway Pro handles the operational complexity of zero-downtime deploys, health checks, and persistent volumes without requiring a dedicated platform engineer, while Kubernetes is reserved for the post-$3k/month inflection point where a platform engineer exists and multi-region, fine-grained autoscaling justifies the overhead.

---

## 1. Platform Orchestration: Docker Compose vs Kubernetes vs Railway/Fly.io

### Recommendation

**Railway Pro** for the 100–1,000 client range. **Fly.io** when multi-region or EU/US data residency is a hard requirement. **Docker Compose on a VPS** only for prototypes below 50–100 clients. **Kubernetes (EKS or GKE Autopilot)** when the monthly infra bill exceeds ~$2,500–3,000/month or when a dedicated platform engineer is available.

### Platform Comparison

| Criteria | Docker Compose (VPS) | Railway Pro | Fly.io | Kubernetes (EKS/GKE) |
|---|---|---|---|---|
| **Ceiling** | ~50–100 clients | ~500–1,000 clients | ~500–1,000 clients | Unlimited |
| **Compute model** | Pay fixed VPS | Per-second vCPU + RAM | Per-second VM + egress | Per-second node + management |
| **Autoscaling** | Manual | Built-in (up to 42 replicas) | Built-in (Machine autoscaling) | KEDA + HPA (complex) |
| **Persistent volumes** | Host bind mounts | Native Volumes ($0.15/GB/mo) | Volumes ($0.15/GB/mo) | PersistentVolumeClaims |
| **Zero-downtime deploys** | HAProxy required; fragile | Built-in rolling | 4 strategies (blue/green/rolling/canary) | Rolling + preStop hooks |
| **Multi-region** | Manual | 4 regions | 30+ regions | Manual + Cloud Load Balancer |
| **Secrets** |.env file (risky) | Native secrets | Native secrets | K8s Secrets + external |
| **Min cost** | $10–20/mo (Hetzner/DO) | $20/mo base + usage | $0.02/GB egress + compute | $74/mo (GKE control plane) + nodes |
| **Ops overhead** | Low at small scale | Very low | Low | High (without platform engineer) |

### Rationale

Docker Compose on a single VPS works for prototypes but breaks down at 50–100 clients because of three failure modes: scale-down events cause 502 errors without a reverse proxy with graceful connection draining; the single host is a single point of failure; and adding a Celery worker autoscaler requires either a cron job polling Redis or a custom systemd service, both fragile.

Railway Pro provides the fastest path to production for a 1–3 person team. The built-in health checks, persistent volumes, and rolling deploys cover 90% of production needs. The ceiling is roughly 500–1,000 clients because Railway's autoscaling has a 42-replica hard cap (hobby tier) and lacks fine-grained queue-aware scaling for Celery workers. At the 1,000-client scale with bursty Celery workloads, a 42-replica web tier is sufficient but Celery workers may need more than Railway's built-in autoscaler provides.

Fly.io has a stronger multi-region story (30+ regions vs Railway's 4) and lower egress pricing ($0.02/GB for NA/EU vs Railway's metered pricing). Fly Machines provide per-second billing at the VM level, which is better for bursty Celery workloads that scale to zero between job waves. The recommendation is Fly.io when the product requires sub-100ms latency for the frontend in multiple geographic regions or when EU/US data residency is contractually required.

Kubernetes (EKS or GKE Autopilot) is the correct choice at the post-$2,500–3,000/month inflection point. At 1,000 clients with 100 images/day each, the Celery vectorize queue alone may need 10–20 concurrent workers during batch processing windows, which maps to 20–40 pods. GKE Autopilot charges per pod-second without requiring node management and eliminates the operational overhead of node provisioning. EKS with EKS Auto Mode (announced 2025) reduces cluster management to cluster creation and workload deployment.

### Fallback

If Railway deprecates features or pricing changes unfavorably, migrate to Fly.io using the documented migrate-from-Railway process [1]. Both platforms use Dockerfiles, so the migration is primarily a registry and secrets remapping exercise.

---

## 2. Celery Worker Queue Topology

### Recommendation

**Three dedicated queues** (discovery, vectorize, takedown) with dedicated worker pools, separate prefetch multipliers, visibility timeout tuning per queue, and KEDA-based autoscaling. This is mandatory because the three task classes have fundamentally different resource profiles.

### Queue Architecture

```
 ┌─────────────────────────────────┐
 │ Celery Broker │
 │ (Redis Streams) │
 └─────────────────────────────────┘
 ┌──────────────────┼──────────────────┬─────────────┘
 ▼ ▼ ▼
 ┌───────────┐ ┌────────────┐ ┌──────────────┐
 │ discovery │ │ vectorize │ │ takedown │
 │ (queue) │ │ (queue) │ │ (queue) │
 └─────┬─────┘ └──────┬─────┘ └──────┬───────┘
 │ │ │
 ┌─────▼─────┐ ┌──────▼──────┐ ┌─────▼───────┐
 │ gevent │ │ prefork │ │ solo │
 │ pool/50 │ │ pool/4–8 │ │ pool/1–2 │
 │ (I/O) │ │ (CPU+GPU) │ │ (sync API) │
 └───────────┘ └─────────────┘ └─────────────┘
 Max 50 concurrent Max 4–8 concurrent Max 2 concurrent
 HTTP tasks embedding calls API calls
```

### Task Class Specifications

**Discovery queue** handles web scraping, marketplace crawling, and social platform monitoring. These tasks are I/O-bound with high concurrency requirements (hundreds of simultaneous HTTP requests). The gevent pool with 50 concurrent greenlets per worker maximizes throughput without the overhead of preemptive threading. The `worker_prefetch_multiplier` should be set to 1 (or 0 for `task_acks_late=True`) to ensure fair task distribution across workers and prevent a single large crawl from monopolizing the pool.

**Vectorize queue** handles calls to HuggingFace Inference Endpoints (SigLIP similarity scoring and DINOv2 embedding generation) followed by pgvector upserts. These tasks are CPU and GPU-bound with moderate concurrency (4–8 tasks saturate one L4 GPU or one SigLIP endpoint instance). The prefork pool prevents blocking during HTTP calls to the embedding endpoint and allows the OS to parallelize across CPU cores during vector normalization. The `task_acks_late=True` setting is mandatory here because vectorize tasks must not be silently dropped during a worker restart—the image would never be indexed.

**Takedown queue** handles DMCA form submissions, evidence bundle generation, and webhook delivery. These tasks are synchronous API calls to third-party services (registrars, marketplaces, social platforms). The solo pool with 1–2 workers provides predictable sequential execution and prevents duplicate takedown requests from racing. Rate limiting must be enforced per task (using a Redis counter or Celery rate limit of "10/m") to respect third-party API limits and avoid triggering account-level throttling.

### Autoscaling

On Railway or Fly.io, deploy an external scaler using a cron-triggered script that reads the Redis queue length and calls the platform's scaling API. On Kubernetes, use KEDA with the Redis Streams scaler (trigger: `llen discovery`, `llen vectorize`, `llen takedown`) to scale worker Deployments based on actual queue depth [2][3]. Set the KEDA `pollingInterval` to 15 seconds to avoid thrashing, and use `冷却期` (cooldown) of 300 seconds to prevent oscillating scale-down during transient load spikes.

### Error Handling and Dead Letters

Each queue should have a corresponding dead-letter queue (`discovery.dlq`, `vectorize.dlq`, `takedown.dlq`) configured via Redis Streams `MAXLEN` or Celery's `task_reject_on_worker_lost` setting. Tasks that fail 3 times (configurable via `task_default_retry_delays`) should be routed to the DLQ and logged to a Supabase `task_failures` table with the full traceback, task arguments, and retry count for manual review.

---

## 3. Redis Configuration and Persistence

### Recommendation

**Upstash Redis** (Serverless plan at low scale, Pro plan at 1,000 clients) or **Redis Cloud Essentials** for managed Redis with AOF every-second persistence + RDB snapshots every 5 minutes. Set `maxmemory` to 2 GB at 100 clients and 8 GB at 1,000 clients with `allkeys-lru` eviction policy. Use a separate Redis database for Celery broker (DB 0) and result backend (DB 1) to isolate failure domains.

### Persistence Strategy

Redis persistence in a Celery context serves two purposes: durability of the task queue and durability of the result backend.

**AOF (Append-Only File) every second** is the primary persistence mechanism. With `appendfsync everysec`, Redis writes to the AOF log at most once per second, which limits data loss to 1 second of task submissions in the worst case (the last 1 second of tasks before a crash would be lost). This is an acceptable tradeoff for a Celery broker because tasks are inherently transient—if a task is lost, the Celery result backend would mark it as PENDING and the client would resubmit. AOF every second adds approximately 5–10% write overhead compared to no persistence.

**RDB snapshots every 5 minutes** serve as a secondary backup and a fast restart mechanism. The RDB file captures a point-in-time snapshot that can be loaded in under 1 second for a 1–2 GB Redis dataset. This is faster than replaying hours of AOF on a cold restart. Configure RDB with `save 300 1` (save if at least 1 key changed in 300 seconds) and `stop-writes-on-bgsave-error yes` to halt writes if the background save fails.

### Sizing

| Scale | Maxmemory | Connections (est.) | Upstash Plan | Monthly Cost |
|---|---|---|---|---|
| 100 clients | 1–2 GB | 200–400 | Serverless (free → $10) | $0–10/mo |
| 1,000 clients | 4–8 GB | 800–1,600 | Pro 8GB | $50–70/mo |

The Redis dataset size is dominated by Celery result objects (JSON-encoded task results with a TTL of 1 hour) and the Celery message backlog during peak ingestion windows. At 100 clients × 100 images/day × 3 tasks/image = 30,000 tasks/day, with an average result size of 2 KB and a 1-hour TTL, the peak result cache is approximately 30,000 × 2 KB × (1 hour / average task duration). Assuming a 5-minute average task duration, this yields roughly 7.2 MB of result cache at steady state, plus the queue backlog during batch windows (up to 100 MB). The remaining memory is for Celery broker message throughput headroom and connection buffer pools.

### Eviction Policy

Use `allkeys-lru` as the eviction policy. This aggressively evicts the least-recently-used keys when Redis reaches `maxmemory`, which is safe for a Celery result backend because results are transient. The Celery broker queue is protected from eviction because Redis Streams are not subject to keyspace eviction policies when `maxmemory` is reached (Streams use specialized eviction semantics). However, setting `maxmemory` too low causes Redis to return busy-loop errors to Celery workers, so reserve at least 50% headroom above the observed peak usage.

### Managed Redis Options

Upstash Serverless (free tier: 10,000 commands/day; $0.40/million beyond) is the best fit at 100 clients because the command volume is low and the serverless pricing model aligns with bursty Celery workloads. At 1,000 clients, upgrade to Upstash Pro (fixed 8 GB, ~$50–70/month) for predictable pricing and higher throughput (100K+ commands/second vs serverless's 1K commands/second ceiling). Redis Cloud Essentials (fixed 1 GB for $3/month) is a cost-effective alternative for the broker, while Redis Cloud Pro ($50+/month for 8 GB) is equivalent to Upstash Pro.

---

## 4. HuggingFace Inference Endpoints for SigLIP and DINOv2

### Recommendation

**HuggingFace Inference Endpoints (Dedicated tier)** with an L4 GPU for SigLIP (image-text similarity) and DINOv2 (image embeddings). Use the L4 rather than T4 because DINOv2's ViT-L/14 model benefits from L4's larger FP16 throughput for batch inference. At 100 clients with 100 images/day, a single L4 instance handles the embedding pipeline. At 1,000 clients, use two L4 instances behind a single HF endpoint with the built-in load balancer.

**Fallback:** Modal.com for serverless GPU inference at lower utilization, or self-host on RunPod Serverless (V100-80GB) if per-GPU-hour cost becomes the bottleneck.

### Model Specifications

| Model | Use Case | Embedding Dim | GPU Memory | Latency (L4, batch=1) |
|---|---|---|---|---|
| DINOv2 ViT-L/14 | Image embeddings for pgvector | 1,024 | ~6 GB loaded | ~80–150ms/image |
| SigLIP SO400M/14 | Image-text similarity scoring | 768 (logits) | ~12 GB loaded | ~150–300ms/image |

DINOv2 ViT-L/14 produces 1,024-dimensional embeddings suitable for cosine similarity search in pgvector. SigLIP is used for text queries ("exact replica of brand X") against stored image embeddings via CLIP-style similarity scoring. Both models are loaded simultaneously on the L4 GPU (total VRAM: ~18 GB), which fits within the L4's 24 GB frame buffer with headroom for batch processing.

### Endpoint Configuration

**Dedicated tier** (recommended): The endpoint runs on a dedicated L4 GPU with guaranteed resources. Autoscaling is based on GPU utilization (scale up at 80% utilization, scale down after 2 minutes of idle). Cold start from zero replicas takes 10–30 seconds; warm path (already running) has sub-200ms latency per inference call. Billing is per GPU-second: L4 at approximately $0.80/hour on AWS us-east-1.

**Serverless tier** (fallback for bursty workloads): HF Inference Endpoints Serverless uses a pay-per-token model with automatic scale-to-zero. This is cost-effective if embedding calls are infrequent (<1,000/day), but cold starts of 10–30 seconds would add unacceptable latency to the synchronous vectorize pipeline. Use serverless only for the discovery queue's text-based similarity search (lightweight, infrequent) and keep the vectorize pipeline on dedicated.

**Endpoint URL and authentication:** Deploy the endpoint in the same region as the Celery workers (us-east-1 or eu-west-1) to minimize latency between the worker and the GPU. Use the HF token (`HF_TOKEN`) stored in Doppler for authentication. The Celery vectorize task calls the endpoint via the Inference Endpoints REST API with a JSON payload of base64-encoded images.

### Cost Optimization

At 100 clients × 100 images/day = 10,000 images/day:
- DINOv2 embedding calls: 10,000/day × 0.08–0.15s = 800–1,500 GPU-seconds/day ≈ 0.22–0.42 GPU-hours/day
- SigLIP similarity calls: 10,000/day × 0.15–0.30s = 1,500–3,000 GPU-seconds/day ≈ 0.42–0.83 GPU-hours/day
- Total at $0.80/hr L4: **$0.51–1.00/day ≈ $15–30/month**

At 1,000 clients × 100 images/day = 100,000 images/day:
- Total at $0.80/hr L4: **$5.10–10.00/day ≈ $153–300/month**
- Use two L4 instances (load balanced) at ~$40/day = ~$1,200/month if sustained at full capacity
- Batching (send 4–8 images per request) reduces GPU-hour cost by 30–40%

---

## 5. Supabase Scaling Limits and pgvector

### Recommendation

**Supabase Pro ($25/month)** for the 100–500 client range. Upgrade to **Supabase Team ($599/month)** or migrate to **Neon (Postgres 16 + pgvector)** above ~500 clients or when the database approaches the 8 GB storage limit. The hard exit-ramp trigger is 8 GB of data storage, which is reached at approximately 5–10 million vectors (depending on metadata size), or approximately 50–100 clients with heavy image ingestion (100 images/day each, 1-year retention).

### Plan Comparison

| Feature | Supabase Free | Supabase Pro | Supabase Team |
|---|---|---|---|
| **Price** | $0 | $25/mo | $599/mo |
| **Storage** | 8 GB (pauses after 7 days inactive) | 8 GB included | 50 GB included |
| **Database instances** | 1 shared | 2 (1 prod + 1 staging) | 4 (prod + staging + dev + preview) |
| **Compute** | Shared, 200k rows/sec | Dedicated, 750k rows/sec | Dedicated, 1.5M rows/sec |
| **API rate limits** | Conservative | Relaxed | High-volume |
| **Connection pooler** | Included (10K connections) | Included (Supavisor) | Included (Supavisor) |
| **pgvector support** | HNSW + IVFFlat | HNSW + IVFFlat | HNSW + IVFFlat |
| **Max vector dimensions** | 16,000 | 16,000 | 16,000 |
| **Backup** | 7 days | Point-in-time | Point-in-time + exports |

### pgvector Index Strategy

**HNSW (Hierarchical Navigable Small World)** is the recommended index type for this workload. HNSW provides sub-10ms p99 query latency for nearest-neighbor search at up to 10 million vectors with an `ef_search` setting of 128–256 and `m` of 16. The index construction is memory-intensive: approximately 1.5× the raw vector data size for the index overhead. For 10 million 1,024-dimensional float32 vectors (40 GB of raw data), the HNSW index requires approximately 60 GB of memory, which exceeds Supabase Pro's compute limits.

At the 1,000-client scale with 1-year retention (365 days × 100 images/day × 1,000 clients = 36.5 million images), the pgvector dataset alone would be approximately 140 GB (36.5M × 4 KB average per record including metadata), which exceeds every Supabase tier's storage limits. This is the primary exit ramp trigger.

**Recommended exit ramp at scale:** Migrate to **Neon** (serverless Postgres with 10 GB per branch, autoscaling compute) or **AWS RDS pgvector** (db.r7g.2xlarge for 64 GB RAM, handling the HNSW index in-memory). Use Supabase's database migration tooling and the `pg_dump`/`pg_restore` pipeline for the migration, with a dual-write period during which new vectors are written to both Supabase and the target database.

### Connection Pooling

Supabase includes **Supavisor**, a PgBouncer-compatible connection pooler that supports both transaction-mode pooling (for stateless API servers) and session-mode pooling (for tools requiring persistent connections). Configure the FastAPI application with a connection pool of 10–20 connections from the pooler, and set `pool_timeout=5` to prevent hanging queries from consuming all pool connections. The pooler is shared across all Supabase projects, so connection exhaustion is unlikely at the Pro tier.

---

## 6. Health Checks

### Recommendation

Implement a three-tier probe strategy: **startup probes** (initialization verification), **readiness probes** (traffic eligibility), and **liveness probes** (process health). Each tier serves a distinct purpose and has different failure thresholds.

### Probe Configuration Table

| Service | Probe Type | Path / Mechanism | initialDelaySeconds | periodSeconds | failureThreshold | Timeout | Action on Failure |
|---|---|---|---|---|---|---|---|
| **Next.js (web)** | Startup | `GET /api/health/startup` | 10 | 5 | 30 (2.5 min) | 2s | Prevent traffic; crash if persists |
| **Next.js (web)** | Readiness | `GET /api/health/ready` | 5 | 5 | 3 (15s) | 2s | Remove from load balancer |
| **Next.js (web)** | Liveness | `GET /api/health/live` | 15 | 10 | 3 (30s) | 2s | Restart pod |
| **FastAPI (API)** | Startup | `GET /health/startup` (app.startup_event) | 5 | 5 | 30 | 2s | Block traffic until DB + Redis connect |
| **FastAPI (API)** | Readiness | `GET /health/ready` (app.readiness_event) | 5 | 5 | 3 | 2s | Remove from LB; check DB pool + Redis |
| **FastAPI (API)** | Liveness | `GET /health/live` (simple 200 OK) | 10 | 10 | 3 | 2s | Restart pod |
| **Celery discovery worker** | Readiness | Flower API `/api/workers` or Redis ping | 30 | 15 | 3 | 5s | KEDA scales down; drain queue |
| **Celery vectorize worker** | Readiness | Flower API or custom `/health` endpoint | 30 | 15 | 3 | 5s | KEDA scales down |
| **Celery takedown worker** | Readiness | Flower API | 30 | 15 | 3 | 5s | KEDA scales down |
| **Redis** | Dependency | FastAPI readiness probe includes `redis.ping` | — | — | — | — | FastAPI marks unhealthy |
| **HF Inference Endpoint** | Dependency | FastAPI readiness probe includes HF health check | — | — | — | — | FastAPI marks unhealthy |
| **Supabase** | Dependency | FastAPI readiness probe includes `pg.pool.query("SELECT 1")` | — | — | — | — | FastAPI marks unhealthy |

### Next.js Health Endpoints

```typescript
// app/api/health/startup/route.ts — blocks traffic until DB is reachable
export async function GET {
 try {
 await prisma.$queryRaw`SELECT 1`;
 return Response.json({ status: "ready" }, { status: 200 });
 } catch {
 return Response.json({ status: "initializing" }, { status: 503 });
 }
}

// app/api/health/ready/route.ts — removes from load balancer
export async function GET {
 return Response.json({ status: "ok" });
}

// app/api/health/live/route.ts — process liveness
export async function GET {
 return Response.json({ status: "alive" });
}
```

### FastAPI Health Endpoints

```python
from fastapi import FastAPI, Response
from contextlib import asynccontextmanager
import asyncio, redis.asyncio as redis

redis_client: redis.Redis = None

@asynccontextmanager
async def lifespan(app: FastAPI):
 global redis_client
 redis_client = redis.from_url(os.getenv("REDIS_URL"))
 # Verify connections on startup
 await redis_client.ping
 await pool.connect
 yield
 await redis_client.close

app = FastAPI(lifespan=lifespan)

@app.get("/health/startup")
async def startup:
 await redis_client.ping # Verify Redis
 return {"status": "startup_complete"}

@app.get("/health/ready")
async def readiness:
 # Check Redis
 await redis_client.ping
 # Check DB pool
 async with pool.connection as conn:
 await conn.execute("SELECT 1")
 return {"status": "ready"}

@app.get("/health/live")
async def liveness:
 return {"status": "alive"}
```

The readiness probe's dependency checks (Redis ping, DB query) serve as the circuit breaker. If the HF Inference Endpoint is unreachable, the vectorize tasks will queue up in Redis (which is acceptable), but the API's readiness probe should not fail—HF endpoint failures are handled by the Celery retry policy, not by the API readiness probe. Only block the API readiness probe on Supabase and Redis, which are true blocking dependencies.

---

## 7. Zero-Downtime Deploys

### Recommendation

Use **Fly.io blue-green deploys** for the frontend (zero-traffic-cutover window) and **Railway rolling deploys** for the API and workers. Implement Celery worker graceful shutdown with `SIGTERM` handling and a preStop sleep. Use the **expand-contract migration pattern** for all Supabase schema changes.

### Deployment Strategy by Component

**Next.js (Fly.io):** Configure `fly.toml` with `deploy_strategy = "bluegreen"`. This launches the new version, waits for it to pass health checks, then atomically switches all traffic from old to new. Blue-green eliminates the brief 502 window that rolling deploys produce. For Railway, use `railway up --prod` which performs a rolling deploy with a built-in health check window.

**FastAPI (Railway):** Railway's default rolling deploy sends SIGTERM to the old container only after the new container passes its health check. Configure the health check path to `/health/startup` to ensure the database connection pool is fully initialized before traffic is routed. Add a `preStop` hook in the Dockerfile or platform configuration: `CMD ["sh", "-c", "sleep 5 && exec python -m uvicorn"]` to allow in-flight requests to complete before shutdown.

**Celery workers:** Graceful shutdown is critical because in-flight vectorize tasks must not be silently dropped (image would never be indexed). Configure Celery workers with `task_acks_late=True` and `worker_cancel_long_running_tasks_on_connection_loss = True`. On SIGTERM, Celery finishes the current task, acknowledges it, and exits. For long-running tasks (vectorize tasks processing large images), set `task_soft_time_limit = 300` (5 minutes) to prevent a stuck task from blocking graceful shutdown indefinitely.

**Database migrations (Supabase):** Use the expand-contract pattern. Never rename or drop a column in a single deploy. Instead:

1. **Expand:** Add the new column (nullable, with a default) in deploy N. The application code writes to both old and new columns during this window.
2. **Migrate:** Backfill the new column with data from the old column in deploy N+1 (during low-traffic hours using a Celery task).
3. **Contract:** Remove the old column write paths from application code in deploy N+2, then drop the old column in deploy N+3.

Supabase's migration system runs via `supabase db push` and applies migrations before the application starts, which means the database must be backward-compatible with the running application code during the migration. If the migration is non-backward-compatible (e.g., changing a NOT NULL constraint), perform the migration during a maintenance window with the application in read-only mode.

### Rollback Decision Matrix

| Failure Type | Trigger | Rollback Action |
|---|---|---|
| **API code bug** | Error rate > 5% in 2 minutes | Revert to previous Railway/Fly.io deployment (one click) |
| **Frontend code bug** | Error rate > 5% | Revert Fly.io/ Railway deployment |
| **Schema migration** | Migration fails or application error post-migration | Revert migration via `supabase db reset` (last resort; prefer read-only mode) |
| **Celery worker bug** | Task failure rate > 10% | Deploy new worker image; old workers drain naturally via graceful shutdown |
| **Supabase outage** | Connection pool exhausted for > 1 minute | Switch Supabase URL to staging project via feature flag; or migrate to Neon |
| **HF Endpoint degradation** | Embedding latency > 5 seconds | Use HF Inference Provider router (automatic failover to alternative endpoints) |

---

## 8. Secrets Management

### Recommendation

**Doppler** (Starter at $6/seat/month) for teams up to 10 engineers. **HashiCorp Vault (Open Source)** for self-hosted deployments or teams that need fine-grained secret rotation and audit logging without a per-seat subscription. **AWS Secrets Manager** ($0.40/secret/month) only if the entire stack runs on AWS and a platform engineer manages rotation.

### Comparison

| Feature | Doppler | HashiCorp Vault (OSS) | AWS Secrets Manager | K8s Secrets |
|---|---|---|---|---|
| **Cost** | $6/seat/mo | Free (self-hosted) | $0.40/secret/mo | Included (cluster) |
| **Rotation** | Automatic (env sync) | Built-in (dynamic secrets) | Built-in | Manual only |
| **Audit log** | Yes (Starter+) | Yes (enterprise only) | Yes | No |
| **Runtime injection** | Via webhook/sidecar | Via agent sidecar | Via CSI driver | Via env (plaintext at rest) |
| **Team features** | RBAC, SSO, audit | Requires Vault for teams | IAM-based | Namespace RBAC |
| **Setup complexity** | Low | Medium (operational burden) | Low | Low |
| **K8s integration** | Doppler Operator | Vault Agent Sidecar | AWS Secrets Store CSI | Native |

### Doppler Integration

Store all secrets in Doppler with project-scoped config sets (development, staging, production). On Railway, use the Doppler CLI to inject secrets into the deployment: `railway variables set $(cat.env | xargs | tr ' ' '\n' | grep DOPPLER)` or use Railway's native Doppler integration. On Fly.io, use the Doppler CLI in the `fly.toml` `env` section or the `fly secrets import` command.

```bash
# Doppler secret sync to Railway environment
doppler run -- railway up --prod
```

The secrets to store: `DATABASE_URL`, `REDIS_URL`, `SUPABASE_URL`, `SUPABASE_KEY`, `HF_TOKEN`, `DOPPLER_CONFIG` (production), `NEXT_PUBLIC_SUPABASE_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`, and any third-party API keys (registrar APIs, marketplace APIs).

### Fallback

If Doppler becomes cost-prohibitive (>20 engineers), migrate to HashiCorp Vault Open Source deployed on the same Kubernetes cluster using the Vault Agent Injector. The migration involves exporting the current secrets from Doppler, writing them to Vault, and updating the deployment configuration to read from Vault's env template rather than Doppler's webhook.

---

## 9. Cost Estimates

### Assumptions

- 100 clients: 100 images/client/day × 30 days = 300,000 images/month
- 1,000 clients: 100 images/client/day × 30 days = 3,000,000 images/month
- Celery task mix per image: discovery (1 task), vectorize (2 embedding calls: DINOv2 + SigLIP), takedown (0.1 tasks, ~10% trigger)
- Vector retention: 12 months
- Observability: Grafana Cloud free tier (500 series + 10K logs/hour) + Prometheus on Railway
- Secrets: Doppler Starter (5 seats)

### Cost Table: 100 Clients

| Line Item | Unit | Unit Price | Quantity | Monthly Cost | Source |
|---|---|---|---|---|---|
| **Compute: Next.js (Fly.io)** | Shared-cpu-1x, 256 MB VM | ~$2/mo | 2 VMs (replicas) | $4/mo | [4] |
| **Compute: FastAPI (Railway)** | CPU + RAM (0.5 vCPU, 1 GB) | ~$30/mo | 2 replicas | $60/mo | [5] |
| **Compute: Celery discovery (Railway)** | CPU + RAM (1 vCPU, 2 GB) | ~$60/mo | 2 workers | $120/mo | [5] |
| **Compute: Celery vectorize (Railway)** | CPU + RAM (2 vCPU, 4 GB) | ~$120/mo | 2 workers | $240/mo | [5] |
| **Compute: Celery takedown (Railway)** | CPU + RAM (0.5 vCPU, 1 GB) | ~$30/mo | 1 worker | $30/mo | [5] |
| **Redis (Upstash Serverless)** | Commands | $0 | 100K/day (under free tier) | $0/mo | [6] |
| **Redis (Upstash Pro fallback)** | 8 GB fixed | $50/mo | 1 instance | $50/mo | [6] |
| **Supabase Pro** | Fixed | $25/mo | 1 project | $25/mo | [5] |
| **HuggingFace Inference Endpoints (L4)** | GPU-hours | $0.80/hr | ~15 hr/mo | $12/mo | |
| **Egress (Fly.io)** | GB | $0.02/GB | ~50 GB/mo | $1/mo | [4] |
| **Observability (Grafana Cloud)** | Free tier | $0 | — | $0/mo | [7] |
| **Doppler Starter** | 5 seats | $6/seat/mo | 5 | $30/mo | [vendor] |
| **Domain + SSL** | DNSimple/Cloudflare | $20/mo | 1 domain | $20/mo | [vendor] |
| **Total** | | | | **~$592/mo** | |

**At 100 clients, the cost is approximately $592/month or $5.92/client/month.** This is slightly higher than the initial estimate of $483 due to including dedicated Celery workers for each queue (a production-hardened topology).

### Cost Table: 1,000 Clients

| Line Item | Unit | Unit Price | Quantity | Monthly Cost | Source |
|---|---|---|---|---|---|
| **Compute: Next.js (Fly.io)** | Performance-cpu-2x, 1 GB | ~$16/mo | 4 VMs | $64/mo | [4] |
| **Compute: FastAPI (Railway)** | CPU + RAM (1 vCPU, 2 GB) | ~$60/mo | 4 replicas | $240/mo | [5] |
| **Compute: Celery discovery (Railway)** | CPU + RAM (1 vCPU, 2 GB) | ~$60/mo | 4 workers | $240/mo | [5] |
| **Compute: Celery vectorize (Railway)** | CPU + RAM (2 vCPU, 4 GB) | ~$120/mo | 8 workers | $960/mo | [5] |
| **Compute: Celery takedown (Railway)** | CPU + RAM (0.5 vCPU, 1 GB) | ~$30/mo | 2 workers | $60/mo | [5] |
| **Redis (Upstash Pro)** | 8 GB fixed | $50/mo | 1 instance | $50/mo | [6] |
| **Supabase Team** | Fixed | $599/mo | 1 project | $599/mo | [5] |
| **HuggingFace Inference Endpoints (2× L4)** | GPU-hours | $0.80/hr | ~360 hr/mo | $288/mo | |
| **Egress (Fly.io + Railway)** | GB | $0.02–0.10/GB | ~500 GB/mo | $50/mo | [4] |
| **Observability (Grafana Cloud Pro)** | 1K series + 50K logs/hr | $75/mo | 1 | $75/mo | [7] |
| **Doppler Starter** | 5 seats | $6/seat/mo | 5 | $30/mo | [vendor] |
| **Domain + SSL** | DNSimple/Cloudflare | $20/mo | 1 domain | $20/mo | [vendor] |
| **Total** | | | | **~$2,676/mo** | |

**At 1,000 clients, the cost is approximately $2,676/month or $2.68/client/month.** The per-client cost decreases with scale due to fixed-cost components (Supabase, Doppler, domain) being amortized over more clients. The Celery vectorize workers are the dominant cost at scale (36% of the total), driven by the 8× parallelization required to handle 100,000 images/day through the embedding pipeline.

### Cost Reduction Levers

- **Batch embedding calls:** Send 4–8 images per HF Inference Endpoint request to reduce GPU-hours by 30–40%.
- **Spot/preemptible instances:** Railway does not offer spot instances, but Fly.io Machine autoscaling can scale to zero during off-hours, reducing compute costs by 20–30%.
- **Redis optimization:** At 1,000 clients, the Upstash Pro 8 GB plan is oversized for actual usage (estimated 4 GB). Negotiate a custom plan or switch to Redis Cloud Essentials 4 GB at lower cost.
- **Celery worker rightsizing:** Monitor actual CPU utilization. If vectorize workers are at <50% CPU, reduce from 8 workers × 2 vCPU to 6 workers × 2 vCPU, saving $240/month.
- **Supabase exit ramp:** At 1,000 clients, Supabase Team at $599/month is expensive. Migrate to Neon (~$200/month for 50 GB storage + production compute) once the migration tooling is validated, saving ~$400/month.

---

## 10. Reference Architecture Diagram

```
 ┌──────────────────────────────────────────────────────┐
 │ Client Browser │
 └──────────────────────────┬────────────────────────────┘
 │ HTTPS
 ┌──────────────────────────▼────────────────────────────┐
 │ Fly.io (Next.js Standalone) │
 │ 4× Performance VMs │
 │ blue-green deploys │
 └──────────────────────────┬────────────────────────────┘
 │ REST / WebSocket
 ┌──────────────────────────▼────────────────────────────┐
 │ Railway Pro (FastAPI + Uvicorn) │
 │ 4× API replicas (1 vCPU, 2 GB) │
 │ rolling deploys + health probes │
 └────┬──────────────┬────────────────┬───────────────────┘
 │ │ │
 ┌──────────────────▼──┐ ┌───────▼──────┐ ┌────▼──────────────────┐
 │ Railway Pro │ │ Railway Pro │ │ Railway Pro │
 │ Celery discovery │ │ Celery vectorize│ │ Celery takedown │
 │ (2× gevent/50) │ │ (8× prefork/8) │ │ (2× solo/1) │
 │ HTTP scraping │ │ HF Endpoints │ │ DMCA API calls │
 │ Queue: discovery │ │ Queue: vectorize│ │ Queue: takedown │
 └──────────┬──────────┘ └───────┬────────┘ └───────▲───────────────┘
 │ │ │
 ┌────────────▼────────────┐ ┌──────▼──────────────────────┘
 │ Upstash Redis │ │ HuggingFace Inference Endpoints
 │ Pro 8 GB │ │ 2× L4 GPU (Dedicated)
 │ AOF+RDB │ │ DINOv2 ViT-L/14 + SigLIP
 │ DB0: Celery broker │ │ Autoscaling (80% GPU util)
 │ DB1: Celery backend │ └────────────────────────────────┐
 └─────────────────────────┘ │
 │ │
 ┌────────────▼────────────────────────────────────────────────▼──┐
 │ Supabase Pro ($25/mo) │
 │ Postgres 16 + pgvector 0.7 │
 │ HNSW index (ef_search=128) │
 │ Supavisor (connection pooler, 10K connections) │
 │ Exit ramp: Neon at 500+ clients or 10M+ vectors │
 └────────────────────────────────────────────────────────────────┘

 ─── Secrets flow: Doppler ─────────────────────────────────────►
 (HF_TOKEN, DATABASE_URL, REDIS_URL, SUPABASE_KEY) │
 All services
```

---

## 11. Migration and Rollback Runbook

### Initial Deployment Checklist

1. Provision Supabase Pro project; run initial migration with `supabase db push`
2. Create Doppler project with `development`, `staging`, `production` config sets
3. Deploy FastAPI to Railway Pro; verify health probes at `/health/ready`
4. Deploy Celery workers (one per queue) to Railway; verify via Flower
5. Deploy HuggingFace Inference Endpoint (Dedicated L4); test embedding latency
6. Deploy Next.js to Fly.io with blue-green strategy; verify zero-downtime
7. Configure Doppler secret sync on all services
8. Set up Grafana Cloud dashboards for Redis memory, Celery queue depth, API latency, Supabase connection pool utilization
9. Configure alerting: Redis memory > 80%, Celery DLQ depth > 100, API error rate > 1%, HF endpoint latency > 5 seconds

### Rollback Procedure

**FastAPI (Railway):** `railway rollback` — reverts to the previous successful deployment in under 30 seconds.

**Next.js (Fly.io):** `fly deploy --image-label <previous-image-tag>` — Fly.io keeps the last 5 deployments available for instant rollback.

**Celery workers:** No explicit rollback needed for code-only changes (workers pick up new code on next deploy). For breaking changes (e.g., changed task signature), drain the worker: send SIGTERM, wait for in-flight tasks to complete (up to `task_soft_time_limit`), then deploy the new image.

**Database migration:** If a migration causes errors, set the Supabase project to read-only mode via feature flag, then run `supabase db reset --db-url $STAGING_DB_URL` from the last known good migration. Never run `db reset` on production without a confirmed backup.

---

## References
[1] Fly.io vs Railway in 2026: Which PaaS Wins? [content_marketing]: https://www.kunalganglani.com/blog/fly-io-vs-railway
[2] KEDA vs HPA: Kubernetes Autoscaling Compared (2026 Guide) [content_marketing]: https://lucaberton.com/blog/keda-vs-hpa-kubernetes-autoscaling-2026/
[3] Effortless Auto-Scaling of Celery Workers with KEDA and Redis on...: https://thinhdanggroup.github.io/blog-on-auto-scaling-celery-tasks/
[4] <span class="highlight">Fly.io</span> Resource <span class="highlight">Pricing</span> [first_party]: https://fly.io/docs/about/pricing/
[5] Use volumes on Railway to securely store and persist your data... [first_party]: https://docs.railway.com/volumes
[6] Smarter memory management for AI agents with Mem0 and Redis | Redis [content_marketing]: https://redis.io/blog/smarter-memory-management-for-ai-agents-with-mem0-and-redis/
[7] <span class="highlight">Configuration</span> and defaults — <span class="highlight">Celery</span> 5.6.3 documentation [first_party]: https://docs.celeryq.dev/en/stable/userguide/configuration.html

## Source Accuracy Notes

Some high-precision claims could not be fully reconciled against the captured source extracts. The report preserves the best available synthesis, but the following items should be treated with caution:
- High-precision numeric claim lacks captured cited-source extract support citations [4, 5, 5, 5, 5, 6, 6, 5, 4, 7].
- High-precision numeric claim lacks captured cited-source extract support citations [4, 5, 5, 5, 5, 6, 5, 4, 7].
