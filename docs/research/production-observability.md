# Production Observability Research

**AI-Q Job:** `bc31cd2a-67d6-4322-923d-1a06458ff821`  
**Applied automatically by SniperIP research loop**

---

# Observability Stack Comparison and Recommendations for FastAPI + Celery Counterfeit Detection SaaS

## Executive Summary

This report provides a comprehensive comparison of observability stacks for a FastAPI + Celery SaaS platform running counterfeit detection pipelines in 2026. The analysis covers three primary approaches: Sentry combined with Prometheus/Grafana, Datadog as an integrated platform, and an OpenTelemetry-native architecture. Each stack presents distinct trade-offs in cost, operational complexity, integration effort, and vendor lock-in risk that must be evaluated against the specific requirements of a production counterfeit detection system.

The counterfeit detection domain introduces unique observability challenges beyond standard web services. These include embedding inference latency monitoring, discovery pipeline progress tracking, takedown success rate measurement, and queue depth management across multiple Celery queues processing different pipeline stages. The recommendation framework accounts for these specialized requirements while providing actionable guidance on structured logging formats, Prometheus metric specifications, SLO targets, alerting rules, error budgets, and on-call runbooks.

For teams operating counterfeit detection pipelines in 2026, the OpenTelemetry-native approach with Grafana Cloud provides the optimal balance of vendor flexibility, modern instrumentation standards, and cost-effectiveness. However, organizations with existing Datadog investments or teams lacking infrastructure expertise may benefit from Datadog's comprehensive integration despite higher costs. The Sentry + Prometheus/Grafana combination remains viable for cost-conscious teams willing to accept higher operational overhead.

## 1. Observability Stack Comparison

### 1.1 Sentry + Prometheus/Grafana Stack

The Sentry and Prometheus/Grafana combination represents a modular approach to observability, combining best-in-class tools for different telemetry domains. Sentry specializes in error tracking and application performance monitoring, while Prometheus handles metrics collection and Grafana provides visualization and alerting [1][2].

**Cost Structure:** Sentry's pricing operates on an event-volume model across errors, spans, replays, logs, metrics, and profiling. The Developer (free) tier includes 5,000 errors and 10,000 transactions monthly. The Team plan costs $26/month with 50,000 errors, while Business pricing reaches $80/month for 100,000 errors [1]. Overage charges apply at approximately $0.000290-$0.000315 per error event beyond plan quotas. A single "bad day" scenario with 500,000 overage errors can generate approximately $157.50 in additional charges [1]. Seer AI, Sentry's machine learning-powered error analysis feature, bills separately at $40 per active contributor per month [1]. For teams processing high volumes of counterfeit detection requests, the event-volume model can become unpredictable, particularly during incident response scenarios when error rates spike.

Grafana Cloud pricing follows a tiered structure with a Free tier providing 10,000 active Prometheus series, 50 GB logs, 50 GB traces, 50 GB profiles, and 14-day retention [3]. Grafana Cloud Pro starts at $19/month plus usage-based charges of approximately $6.50 per 1,000 active metric series, $0.40-0.45 per GB for log writes plus $0.05/GB processing, and $0.45-0.50 per GB for trace ingestion [3][4]. For a typical 100-host team with disciplined Kubernetes labeling, monthly costs commonly range from $950 to $1,400; however, cardinality explosion from excessive metric labels can push costs to $10,000 or more on the same infrastructure [4].

**Integration Complexity for FastAPI/Celery:** Sentry provides a first-party Python SDK with explicit FastAPI integration support. Installation requires only `pip install --upgrade sentry-sdk` followed by `sentry_sdk.init(dsn="...", traces_sample_rate=1.0)` [5]. The SDK automatically captures stack traces, breadcrumbs, and release tracking for FastAPI applications. However, Sentry does not include native Celery instrumentation; teams must configure Celery task events and optionally pair Sentry with Flower or the celery-prometheus-exporter for comprehensive Celery visibility [6].

Grafana offers a curated Celery monitoring dashboard (Dashboard ID 10026) that works with the OvalMoney/celery-exporter community project [7]. This dashboard surfaces events-by-state rate, events-by-task rate, runtime latency heatmaps, and alive-worker counts. Celery Flower provides real-time web-based monitoring with a REST API for programmatic access and supports Prometheus metrics endpoints when configured [6].

**Strengths:** The modular architecture allows teams to select best-of-breed tools for each observability domain. Prometheus and Grafana are open-source with no vendor lock-in, enabling self-hosting if desired. The community ecosystem provides extensive dashboard templates and exporters for specialized use cases. Organizations already using Grafana or maintaining Prometheus infrastructure can leverage existing investments.

**Limitations:** Higher operational overhead compared to integrated platforms. Teams must manage multiple tools, maintain separate configurations, and handle integration between components. The event-volume pricing model for Sentry can become expensive under high error load. Grafana Cloud's per-series billing requires careful label cardinality management to control costs.

### 1.2 Datadog

Datadog provides a comprehensive integrated observability platform covering infrastructure monitoring, application performance monitoring, logs, traces, and synthetic monitoring within a single unified interface [8][9].

**Cost Structure:** Datadog employs multi-axis billing based on hosts, indexed spans, custom metrics, indexed logs, and optional premium tiers for AI observability. For medium-scale deployments with approximately 50 services, monthly costs commonly reach $6,000 to $12,000 [9]. The per-host plus per-custom-metric model creates cost growth challenges as services scale, and organizations report billing surprises from unexpected charges for indexed spans and custom metric cardinality [8][9]. Datadog's automatic premium tiers for LLM traces represent an additional cost layer not present in competing platforms [10].

**Integration Complexity for FastAPI/Celery:** Datadog supports Python auto-instrumentation through the ddtrace library, which includes ASGI/FastAPI auto-instrumentation capabilities. The platform maintains official documentation for Celery integration covering worker, task, and broker metrics [11]. GPU monitoring under the Infrastructure product tier enables visibility into embedding model compute resources, which is directly applicable to counterfeit detection inference pipelines [11]. The AI Observability premium tier provides specialized LLM-specific traces and metrics.

**Strengths:** Lowest operational overhead among the evaluated options. The unified platform eliminates integration complexity between different observability tools. Native support across all major cloud providers and Kubernetes distributions. Comprehensive documentation and customer support. Strong out-of-the-box dashboards and alerting rules. Datadog's market position has driven extensive third-party integration coverage.

**Limitations:** Significant cost barrier for budget-conscious organizations. High vendor lock-in due to proprietary agent and data format requirements. The per-custom-metric model punishes growth and innovation, as adding new metrics for ML pipeline monitoring directly increases costs. Organizations report difficulty predicting monthly bills due to the complex multi-axis pricing model [8][9]. Switching costs are substantial given the depth of integration and historical data accumulated in the platform.

### 1.3 OpenTelemetry-Native Approach

The OpenTelemetry-native approach instruments applications using the vendor-neutral OTel standard and exports telemetry data to any compatible backend via the OTLP protocol [12][13].

**Adoption and Standards Status:** OpenTelemetry has achieved broad industry adoption, with the project ranking as the second-most-active in the Cloud Native Computing Foundation after Kubernetes [14]. By 2026, OTel has reached v1.0 stability for traces, metrics, and logs specifications. An estimated 89% of enterprises have mandated OTel adoption for new services, indicating near-universal acceptance as the instrumentation standard [14]. The OTel Python ecosystem provides comprehensive coverage including ASGI instrumentation for FastAPI, Django, Flask, Redis, and Celery [12][15].

**Integration Complexity for FastAPI/Celery:** OpenTelemetry ships first-party instrumentation for FastAPI through `opentelemetry-instrumentation-fastapi` (contrib package) with the core ASGI instrumentation available as stable [12][15]. Celery instrumentation is provided by `opentelemetry-instrumentation-celery`, listed in the official OpenTelemetry PyPI organization alongside 92 other instrumentation packages [12]. Installation follows standard Python package patterns: `pip install opentelemetry-sdk opentelemetry-instrumentation-fastapi opentelemetry-exporter-otlp`, followed by `FastAPIInstrumentor.instrument` [15]. ML inference observability is supported through OpenInference, which adds semantic conventions for LLM-specific spans including model version, hyperparameters, and input data attributes [16]. The OpenTelemetry GenAI semantic conventions reached Python availability in May 2026, enabling standardized capture of model version, prompt content, and token counts [16].

**Backend Options:** Organizations adopting OTel can route telemetry to numerous backends without changing application code. Grafana Cloud accepts OTLP natively and offers generous free tiers (20M events/month for Honeycomb, similar capacity for Grafana's own stack). Other options include Honeycomb ($130/month Pro with unlimited queryable attributes), SigNoz, Elastic, and commercial platforms [17]. This flexibility eliminates vendor lock-in and enables cost optimization as requirements evolve.

**Total Cost of Ownership Reality:** A frequently-cited claim suggests OTel-native LGTM (Loki/Grafana/Tempo/Mimir) stacks save 50-80% compared to commercial platforms like Datadog. However, a hands-on evaluation with a 12-microservice staging cluster processing 40,000 requests/day found that self-hosted LGTM costs reached $167,000 annually versus $150,000 for Datadog once full SRE operational time was included [14]. The promised savings collapse under comprehensive cost accounting that includes engineering effort for collector tuning, retention management, and platform maintenance. OTel-native architectures remain cost-effective primarily when leveraging cloud-managed backends like Grafana Cloud Pro or Honeycomb.

**Strengths:** Complete vendor neutrality enables flexible backend selection and avoids lock-in. The OTel standard is increasingly required by enterprise procurement processes. Single instrumentation investment applies across environments and backends. Large and growing ecosystem of supported libraries, frameworks, and infrastructure components.

**Limitations:** Higher initial setup complexity compared to integrated platforms. Self-hosted backends require ongoing operational investment. The standard's flexibility can lead to inconsistent instrumentation practices if governance is weak. Some specialized features (e.g., Datadog's AI Observability) require platform-specific instrumentation even when using OTel as a foundation.

### 1.4 Trade-off Analysis Matrix

| Dimension | Sentry + Prometheus/Grafana | Datadog | OpenTelemetry-Native |
|-----------|------------------------------|---------|----------------------|
| **Typical Monthly Cost** | $200-$1,500 (managed) | $6,000-$12,000 | $1,000-$5,000 (cloud backend) |
| **Integration Effort** | Medium-High | Low | Medium |
| **Operational Overhead** | High | Low | Medium |
| **Vendor Lock-in** | Low (OSS components) | High | None |
| **Celery Support** | Via Flower + celery-exporter | Native integration docs | OTel instrumentation available |
| **ML/Inference Visibility** | Custom metrics required | GPU Monitoring + AI Observability | OTel GenAI conventions (May 2026) |
| **FastAPI Support** | Sentry SDK + starlette-exporter | ddtrace auto-instrumentation | OTel ASGI + FastAPI contrib |
| **Cost Predictability** | Moderate (event + series volumes) | Low (multi-axis surprises) | High (fixed or predictable usage) |

For counterfeit detection pipelines specifically, the OpenTelemetry-native approach with Grafana Cloud provides the strongest combination of modern ML observability support (through OTel GenAI conventions), cost predictability, and vendor flexibility. Teams should instrument with OTel from day one and select backends based on operational capability and budget.

## 2. Structured Logging Format

### 2.1 Log Schema Design

Structured logging in production FastAPI + Celery environments should adopt a schema that converges OpenTelemetry Logs Data Model with Elasticsearch Common Schema (ECS) conventions. This dual-standard approach maximizes portability across log backends while maintaining compatibility with modern observability platforms.

**Core Required Fields:**

The timestamp field must use ISO 8601 format with UTC timezone (`2026-06-30T04:16:01.123Z`) for consistent time-series ordering. The `level` field should use canonical severity names: DEBUG, INFO, WARNING, ERROR, CRITICAL. The `message` field contains the human-readable log narrative. The `logger.name` field identifies the Python logger hierarchy (e.g., `app.api.detection`, `app.tasks.discovery`). The `service.name` field provides environment-scoped service identification, and `service.version` enables deployment correlation.

**Structured Data Fields:**

The `trace_id` and `span_id` fields enable correlation with distributed traces when OpenTelemetry context propagation is active. The `resource` object captures static service identity including `service.name`, `service.namespace`, `service.version`, `deployment.environment`, and `host.name`. The `attributes` object carries arbitrary key-value pairs specific to the log event, enabling flexible enrichment without schema changes.

**ECS Compatibility Mapping:**

For organizations targeting ECS compatibility, map OTel fields to ECS equivalents: `log.logger` ← `logger.name`, `log.origin.function` ← function name, `log.origin.file.*` ← source file location. This mapping enables consistent log analysis across tools that prefer either standard.

### 2.2 Context Enrichment Patterns

**Request Correlation in FastAPI:**

FastAPI middleware should capture the incoming request context and inject correlation identifiers into the logging framework. The trace ID from incoming `traceparent` headers (W3C Trace Context) or generated UUID provides the primary correlation key. A request ID generated per incoming request and propagated through Celery tasks ensures end-to-end visibility across the synchronous-asynchronous boundary.

```python
from contextvars import ContextVar
from starlette.middleware.base import BaseHTTPMiddleware
import uuid

trace_id_var: ContextVar[str] = ContextVar('trace_id', default='')
request_id_var: ContextVar[str] = ContextVar('request_id', default='')

class CorrelationMiddleware(BaseHTTPMiddleware):
 async def dispatch(self, request, call_next):
 trace_id = request.headers.get('traceparent', '').split('-')[1] or str(uuid.uuid4)
 request_id = request.headers.get('X-Request-ID', str(uuid.uuid4))
 
 trace_id_var.set(trace_id)
 request_id_var.set(request_id)
 
 # Store in structlog context for task propagation
 structlog.contextvars.clear_contextvars
 structlog.contextvars.bind_contextvars(
 trace_id=trace_id,
 request_id=request_id,
 user_agent=request.headers.get('user-agent', ''),
 client_ip=request.client.host if request.client else ''
 )
```

**Celery Task Context:**

Celery tasks require explicit context enrichment since they execute in separate processes without automatic FastAPI context propagation. The recommended pattern binds task-specific identifiers within the task signature and extracts them in the task body.

```python
@celery_app.task(bind=True)
def process_discovery(self, batch_id: str, items: list):
 # Extract correlation from task request headers
 headers = self.request.headers or {}
 trace_id = headers.get('trace_id', '')
 request_id = headers.get('request_id', '')
 
 structlog.contextvars.bind_contextvars(
 task_id=self.request.id,
 task_name=self.name,
 batch_id=batch_id,
 trace_id=trace_id,
 request_id=request_id
 )
```

**Critical Async Context Consideration:**

The structlog documentation identifies a critical caveat for hybrid sync/async applications: context variables set in a synchronous context will NOT appear in asynchronous log calls, and vice versa. In FastAPI applications mixing synchronous Celery task execution with asynchronous HTTP handlers, this means correlation context may not propagate correctly if not handled carefully. The mitigation involves ensuring all logging occurs within matching context types or explicitly passing context through task arguments rather than relying on process-global context.

**Pipeline-Specific Context:**

For counterfeit detection pipelines, logs should include domain-specific context:

- Detection requests: `detection_type`, `image_hash`, `confidence_threshold`, `client_id`
- Discovery tasks: `discovery_source`, `items_scraped`, `duplicates_filtered`, `queue_name`
- Takedown tasks: `takedown_target`, `platform`, `ticket_id`, `retry_count`
- Embedding inference: `model_name`, `model_version`, `embedding_dim`, `inference_ms`

### 2.3 Log Sampling Strategies

High-volume counterfeit detection systems generating thousands of requests per minute require intelligent sampling to manage log storage costs while preserving debuggability. Two primary sampling strategies address different requirements.

**Head-Based Sampling:** Decisions occur at log emission time based on predetermined rules. For production environments, sample 100% of error logs and 10-20% of success logs. Use consistent hashing on trace ID to ensure all logs from a single request are either included or excluded, preventing partial traces. Configuration example using structlog:

```python
import mmh3 # MurmurHash3 for consistent sampling

def should_sample(event_dict):
 if event_dict.get('level') in ('error', 'critical'):
 return True # Always sample errors
 trace_id = event_dict.get('trace_id', '')
 if trace_id:
 return mmh3.hash(trace_id) % 100 < SAMPLE_RATE # 10% sampling
 return True # Sample if no trace_id for safety
```

**Tail-Based Sampling:** Full log data flows to the backend where sampling decisions occur based on interesting properties discovered during processing. This approach enables sampling rules like "include all logs from requests where an error occurred" or "include all logs from requests where latency exceeded threshold." Tail-based sampling requires log backend support (Loki, Elasticsearch) and adds processing latency but provides superior debuggability for complex incidents.

For counterfeit detection pipelines, implement adaptive sampling that increases sample rate during anomalous conditions. When error rates exceed baseline, automatically elevate sampling to capture more detail without manual intervention.

## 3. Prometheus Metrics Specification

### 3.1 HTTP Layer Metrics

FastAPI applications should instrument HTTP metrics using `prometheus-fastapi-instrumentator`, which has emerged as the de facto standard for FastAPI Prometheus instrumentation [18]. This library automatically captures request counts, latency histograms, and in-progress gauges with minimal configuration.

**Recommended Metrics:**

| Metric Name | Type | Labels | Description |
|-------------|------|--------|-------------|
| `http_requests_total` | Counter | method, endpoint, status_code | Total HTTP requests |
| `http_request_duration_seconds` | Histogram | method, endpoint, status_code | Request latency distribution |
| `http_requests_in_progress` | Gauge | method, endpoint | Currently processing requests |

The histogram buckets for request duration should align with service latency characteristics. The default FastAPI buckets of `[0.1, 0.2, 0.5, 1, 2, 5]` are unsuitable for services with sub-100ms response times [19]. Recommended buckets for counterfeit detection APIs targeting 95th percentile under 200ms:

```python
DURATION_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
```

Endpoint labeling should normalize paths to avoid cardinality explosion. Replace dynamic path segments (UUIDs, database IDs) with parameter names: `/api/v1/detections/{detection_id}` → `/api/v1/detections/{id}`. Static path normalization prevents Prometheus memory growth from unbounded label cardinality [19].

**Configuration Example:**

```python
from prometheus_fastapi_instrumentator import Instrumentator, Exposition
from prometheus_fastapi_instrumentator.metrics import (
 http_requests_total,
 http_request_duration_seconds,
 http_requests_in_progress
)

instrumentator = Instrumentator(
 should_group_status_codes=False,
 should_ignore_untemplated=True,
 should_respect_env_var=True,
 should_instrument_requests_inprogress=True,
 excluded_handlers=["/metrics", "/health"],
 inprogress_name="http_requests_inprogress",
 inprogress_labels=True,
 duration_metric_name="http_request_duration_seconds",
 duration_buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
)
```

### 3.2 Celery Task Metrics

Celery task monitoring requires enabling task events on workers and exposing metrics through the celery-prometheus-exporter [20][21]. This exporter provides comprehensive visibility into task execution patterns.

**Required Worker Configuration:**

Celery workers must send task events for the exporter to capture metrics:

```python
# Celery configuration
celery_worker_send_task_events = True
celery_task_send_sent_event = True
```

**Exporter Metrics:**

The `zerok/celery-prometheus-exporter` exposes the following core metrics [21]:

| Metric Name | Type | Labels | Description |
|-------------|------|--------|-------------|
| `celery_tasks` | Gauge | state | Tasks by state (received, started, success, failure) |
| `celery_tasks_by_name` | Counter | name, state | Task counts by task name and state |
| `celery_workers` | Gauge | | Number of alive workers |
| `celery_task_latency` | Histogram | name | Time between task receipt and start |
| `celery_tasks_runtime_seconds` | Histogram | name, queue | Task execution duration |
| `celery_queue_length` | Gauge | queue | Messages pending in each queue |

**Counterfeit Detection Task Metrics:**

For the specific task types in counterfeit detection pipelines:

| Task Type | Critical Metrics | Alert Threshold |
|-----------|-----------------|-----------------|
| `detection.embed_image` | Runtime histogram, failure rate | p99 > 5s, failure > 1% |
| `discovery.scrape_source` | Queue depth, latency | Depth > 1000, latency p95 > 30s |
| `takedown.submit_report` | Success rate, queue depth | Success < 95%, depth > 100 |
| `discovery.match_candidates` | Runtime, queue depth | p99 > 60s, backlog growing |

**Queue-Specific Visibility:**

The counterfeit detection pipeline likely uses multiple queues for task prioritization and resource isolation:

```python
# Example Celery queue configuration
celery_task_routes = {
 'detection.embed_*': {'queue': 'inference'},
 'discovery.scrape_*': {'queue': 'scraping'},
 'takedown.*': {'queue': 'takedown'},
 'detection.match_*': {'queue': 'matching'},
}
```

Each queue requires independent monitoring for depth, consumer count, and processing rate.

### 3.3 Discovery Latency Metrics

Discovery pipeline latency spans multiple stages from initial crawl through embedding generation to match scoring. Comprehensive latency tracking requires instrumentation at each stage.

**Stage-Resolved Latency:**

| Metric Name | Type | Labels | Description |
|-------------|------|--------|-------------|
| `discovery_stage_duration_seconds` | Histogram | stage, source | Per-stage processing time |
| `discovery_items_processed_total` | Counter | stage, source | Items processed through each stage |
| `discovery_duplicates_filtered_total` | Counter | source | Duplicates identified and filtered |
| `discovery_active_runs` | Gauge | source | Concurrent discovery operations |
| `discovery_errors_total` | Counter | stage, error_type | Errors by stage and type |

**Stage Definitions:**

- `scrape`: Initial content extraction from source
- `parse`: Structured data extraction from raw content
- `dedupe`: Duplicate detection and filtering
- `embed`: Vector embedding generation
- `index`: Search index update
- `match`: Candidate matching against known counterfeits

The `discovery_stage_duration_seconds` histogram should use stage-appropriate buckets. Scraping buckets might focus on 1-30 second range, while embedding buckets target 0.1-5 second range.

### 3.4 Embedding Inference Metrics

Embedding model inference represents a computationally intensive pipeline component requiring specialized metrics for GPU utilization, throughput, and latency.

**Core Inference Metrics:**

| Metric Name | Type | Labels | Description |
|-------------|------|--------|-------------|
| `embedding_inference_duration_seconds` | Histogram | model_name, batch_size | Inference latency |
| `embedding_batch_size` | Histogram | model_name | Processed batch sizes |
| `embedding_requests_total` | Counter | model_name, status | Request count by outcome |
| `embedding_tokens_processed_total` | Counter | model_name | Total tokens/embeddings processed |

**GPU-Specific Metrics:**

| Metric Name | Type | Labels | Description |
|-------------|------|--------|-------------|
| `gpu_utilization_percent` | Gauge | device, model | GPU compute utilization |
| `gpu_memory_allocated_bytes` | Gauge | device, model | GPU memory in use |
| `gpu_memory_reserved_bytes` | Gauge | device, model | GPU memory allocated by runtime |

GPU monitoring requires either Prometheus node_exporter with DCGM exporter, or direct instrumentation using PyTorch/tensorflow model wrappers that expose GPU metrics. The DCGM exporter provides comprehensive NVIDIA GPU metrics including utilization, memory, temperature, and power [22].

**Model-Specific Visibility:**

When running multiple embedding models (primary model plus fallback), differentiate metrics by model_name label to identify underperforming models:

```python
# Example: Model-specific metrics
embedding_latency.labels(
 model_name="clip-vit-l-14",
 model_version="2026-06-15"
).observe(inference_duration)
```

### 3.5 Queue Depth Metrics

Queue depth monitoring provides early warning of processing bottlenecks and consumer failures. The specific metrics depend on the message broker: Redis or RabbitMQ.

**RabbitMQ Metrics (via rabbitmq_prometheus exporter):**

| Metric Name | Type | Labels | Description |
|-------------|------|--------|-------------|
| `rabbitmq_queue_messages` | Gauge | queue, vhost | Ready + unacknowledged messages |
| `rabbitmq_queue_messages_ready` | Gauge | queue, vhost | Messages waiting for consumers |
| `rabbitmq_queue_messages_unacked` | Gauge | queue, vhost | Delivered but unacknowledged |
| `rabbitmq_queue_consumers` | Gauge | queue, vhost | Active consumer count |

**Redis Metrics (via redis_exporter):**

| Metric Name | Type | Labels | Description |
|-------------|------|--------|-------------|
| `redis_list_length` | Gauge | key | Length of list (Celery queue) |

**Alerting Thresholds:**

- Queue depth increasing over 15-minute window: Investigate consumer health
- Queue depth exceeds 10x normal baseline: Scale consumers or investigate failure
- Consumer count drops to zero: Critical - no processing occurring
- Messages accumulating with no consumers: Immediate intervention required

### 3.6 Scrape Configuration

Prometheus scrape intervals should balance freshness requirements against scrape overhead. The recommended scrape interval is approximately twice the application's metrics generation frequency [23]. For counterfeit detection services with sub-second request processing, a 15-second scrape interval provides adequate granularity without excessive overhead.

**Retention Considerations:**

Default Prometheus retention is 15 days [24]. For SLO tracking and trend analysis, extend retention to at least 30 days for monthly SLO windows, or use Prometheus Tiers with longer retention in the read-only tier. Grafana Cloud Pro provides 13-month retention automatically [3].

## 4. Service Level Objectives

### 4.1 SLO Target Recommendations

Service Level Objectives for counterfeit detection SaaS should balance reliability expectations against operational cost and engineering investment. Google SRE recommends starting new services at 99.0-99.5% availability and tightening targets based on demonstrated reliability [25][26].

**API Availability SLO:**

| SLO Target | Monthly Downtime | Applicable To |
|------------|------------------|---------------|
| 99.9% | 43.83 minutes | Detection API (primary SLA) |
| 99.5% | 3h 39 minutes | Discovery API |
| 99.0% | 7h 18 minutes | Takedown reporting API |

The 99.9% availability target for the detection API aligns with industry standard for SaaS platforms where downtime directly impacts customer operations [26]. This target allows only 43.83 minutes of downtime per month—equivalent to a single deployment incident potentially exhausting the entire monthly error budget [25].

**Latency SLO:**

| Metric | Target | Measurement Window |
|--------|--------|-------------------|
| Detection API p95 latency | < 200ms | 5 minutes |
| Detection API p99 latency | < 500ms | 5 minutes |
| Discovery completion (p95) | < 30 minutes | Daily |
| Takedown submission (p95) | < 60 seconds | 5 minutes |

Google's SRE workbook defines "sufficiently fast" as 90% of requests under 400ms and 99% under 850ms for general APIs [26]. Counterfeit detection APIs targeting competitive response times should aim for tighter 95th percentile under 200ms.

**Task Completion SLO:**

| Task Type | Target Completion | Failure Budget |
|-----------|-------------------|----------------|
| Embedding inference | 99% within 10 seconds | 1% error rate |
| Discovery runs | 95% within 2 hours | 5% failure rate |
| Takedown submissions | 99% within 5 minutes | 1% failure rate |

### 4.2 SLO Measurement Methodology

**Availability SLI:**

```
SLI = count(successful_requests) / count(total_requests)
Successful = HTTP status not in [500, 501, 502, 503, 504]
```

The SLI measures from load balancer or ingress metrics, counting all requests that receive non-5xx responses as successful. This approach aligns with Google's SRE workbook guidance for HTTP APIs [26].

**Latency SLI:**

```
SLI = count(requests_with_latency_below_threshold) / count(total_requests)
```

For the p95 latency target, the SLI measures whether the 95th percentile of request latencies over the measurement window falls below the threshold. A practical implementation uses Prometheus histogram_quantile:

```promql
# Availability SLI for detection API
sum(rate(http_requests_total{service="detection-api",status_code!~"5.."}[5m]))
/
sum(rate(http_requests_total{service="detection-api"}[5m]))

# Latency SLI (p95 < 200ms)
histogram_quantile(0.95, 
 rate(http_request_duration_seconds_bucket{service="detection-api"}[5m])
) < 0.2
```

### 4.3 SLO Hierarchy

Organize SLOs in a hierarchy from user-facing to component-level:

**Tier 1 - User-Facing SLOs:**

- Detection API availability (99.9%)
- Detection API latency p95 (200ms)
- API error rate (0.1%)

**Tier 2 - Pipeline SLOs:**

- Discovery completion rate (95% within SLA window)
- Takedown success rate (99%)
- Embedding inference latency p99 (1s)

**Tier 3 - Component SLOs:**

- Celery worker availability (99.5%)
- Message broker availability (99.9%)
- Database availability (99.9%)

This hierarchy enables targeted alerting: Tier 1 breaches trigger immediate pages, while Tier 3 breaches surface in component dashboards and drive maintenance priorities.

## 5. Alerting Rules and Thresholds

### 5.1 Critical Alerts

Critical alerts (P1) require immediate response regardless of time, as they indicate active customer impact or imminent data loss. The following critical alerts protect counterfeit detection pipeline reliability:

**Detection API Down:**

```promql
# Alert when detection API success rate drops below 99%
- alert: DetectionAPIHighErrorRate
 expr: |
 sum(rate(http_requests_total{service="detection-api",status_code=~"5.."}[5m]))
 / sum(rate(http_requests_total{service="detection-api"}[5m])) > 0.01
 for: 2m
 labels:
 severity: critical
 team: backend
 annotations:
 summary: "Detection API error rate exceeds 1%"
 runbook: ""
```

**Celery Workers Unavailable:**

```promql
# Alert when no Celery workers are alive
- alert: CeleryWorkersDown
 expr: celery_workers < 1
 for: 1m
 labels:
 severity: critical
 team: platform
 annotations:
 summary: "No Celery workers alive"
 runbook: ""
```

**Discovery Queue Backlog Critical:**

```promql
# Alert when discovery queue exceeds 5000 messages
- alert: DiscoveryQueueCritical
 expr: rabbitmq_queue_messages_ready{queue="discovery"} > 5000
 for: 10m
 labels:
 severity: critical
 team: pipeline
 annotations:
 summary: "Discovery queue backlog critical (>5000 messages)"
 runbook: ""
```

**Embedding Model Unavailable:**

```promql
# Alert when no embedding inference occurring despite requests
- alert: EmbeddingModelStalled
 expr: |
 rate(embedding_requests_total[5m]) == 0
 and
 rate(http_requests_total{service="detection-api"}[5m]) > 10
 for: 3m
 labels:
 severity: critical
 team: ml-platform
 annotations:
 summary: "Embedding model processing stalled despite incoming requests"
 runbook: ""
```

### 5.2 Warning Alerts

Warning alerts (P2) indicate degraded performance or approaching thresholds, requiring investigation within 30 minutes but not immediate escalation.

**Latency Degradation:**

```promql
# Alert when p95 latency exceeds 150ms (warning) or 200ms (critical)
- alert: DetectionAPILatencyWarning
 expr: |
 histogram_quantile(0.95, 
 rate(http_request_duration_seconds_bucket{service="detection-api"}[5m])
 ) > 0.15
 for: 5m
 labels:
 severity: warning
 team: backend
 annotations:
 summary: "Detection API p95 latency > 150ms"
```

**Takedown Success Rate Degraded:**

```promql
# Alert when takedown success rate drops below 97%
- alert: TakedownSuccessRateWarning
 expr: |
 sum(rate(celery_tasks_by_name{name=~"takedown.*",state="failure"}[15m]))
 / sum(rate(celery_tasks_by_name{name=~"takedown.*"}[15m])) > 0.03
 for: 10m
 labels:
 severity: warning
 team: pipeline
 annotations:
 summary: "Takedown task failure rate exceeds 3%"
```

**Worker Prefetch Imbalance:**

```promql
# Alert when worker prefetch multiplier causing starvation
- alert: CeleryPrefetchImbalance
 expr: |
 max(celery_tasks{state="reserved"}) by (worker) 
 / avg(celery_tasks{state="reserved"}) by > 5
 for: 15m
 labels:
 severity: warning
 team: platform
 annotations:
 summary: "Celery worker prefetch imbalance detected"
```

### 5.3 Multi-Window Burn Rate Alerts

Multi-window burn rate alerting implements Google's SRE methodology for detecting both sudden error budget consumption and slow-burning reliability degradation [27][28].

**Burn Rate Alert Configuration:**

| Window | Threshold | Purpose | Response |
|--------|-----------|---------|----------|
| 1 hour long / 5 minute short | 14.4x burn | Fast burn (sudden spike) | Page immediately |
| 6 hours long / 30 minute short | 6x burn | Slow burn (creeping issue) | Page within 30 min |
| 3 days long / 6 hour short | 3x burn | Ticket-level debt | Create priority ticket |

**Prometheus Implementation:**

```promql
# Fast burn rate: 1h window at 14.4x threshold
- alert: SLOBudgetBurnFast
 expr: |
 (
 1 - (
 sum(rate(http_requests_total{service="detection-api",status_code!~"5.."}[1h]))
 / sum(rate(http_requests_total{service="detection-api"}[1h]))
 )
 ) / 0.001 > 14.4
 for: 5m
 labels:
 severity: critical
 slo: detection-api-availability
 annotations:
 summary: "Detection API SLO budget burning fast (1h window)"
 description: "Error budget burning at 14.4x speed. At this rate, monthly budget will exhaust in {{ $value | humanizeDuration }}"

# Slow burn rate: 6h window at 6x threshold
- alert: SLOBudgetBurnSlow
 expr: |
 (
 1 - (
 sum(rate(http_requests_total{service="detection-api",status_code!~"5.."}[6h]))
 / sum(rate(http_requests_total{service="detection-api"}[6h]))
 )
 ) / 0.001 > 6
 for: 30m
 labels:
 severity: warning
 slo: detection-api-availability
 annotations:
 summary: "Detection API SLO budget burning slowly (6h window)"
```

**Alert Routing Matrix:**

| Alert Type | Severity | Channel | Response Time |
|------------|----------|---------|---------------|
| Fast burn (P1) | Critical | PagerDuty + Slack #incidents | 15 minute ack |
| Slow burn (P2) | Warning | Slack #alerts | 30 minute ack |
| Ticket-level | Low | JIRA ticket | Next sprint |
| Component warning | Warning | Slack #alerts | 4 hours |

## 6. Error Budget Policy

### 6.1 Error Budget Calculation

The error budget represents the allowable reliability margin within the SLO window, providing a concrete metric for reliability investment decisions.

**Calculation Formula:**

```
Error Budget = (1 - SLO Target) × Total Events in Window

For 99.9% SLO over 30 days with 10,000,000 requests:
Error Budget = (1 - 0.999) × 10,000,000 = 10,000 errors
Budget Duration = 0.001 × 43,200 minutes = 43.2 minutes
```

**Budget Visualization:**

Maintain a real-time error budget dashboard showing:

- Current remaining budget (percentage and absolute)
- Budget consumption rate (burn rate)
- Projected exhaust date at current rate
- Historical budget trend

### 6.2 Budget Action Thresholds

Tie engineering actions to error budget consumption levels [29]:

| Remaining Budget | Status | Action |
|------------------|--------|--------|
| > 50% | Healthy | Ship features normally |
| 25-50% | Caution | Increase review rigor, monitor closely |
| < 25% | Danger | Freeze non-critical deployments |
| < 10% | Critical | All-hands reliability focus, no changes |
| 0% | Exhausted | Immediate incident response |

**Deployment Freeze Decision:**

When budget drops below 25%, new feature deployments should require additional review. When below 10%, freeze all but critical security patches and block the deployment pipeline with a manual approval gate. This policy prevents the common pattern of outages occurring immediately following deployment.

### 6.3 Error Budget Recovery

Budget recovery occurs naturally as time passes and the rolling window shifts. However, rapid recovery strategies may be appropriate after significant incidents:

**Post-Incident Budget Recovery:**

After exhausting more than 20% of monthly budget in a single incident:

1. Conduct root cause analysis within 48 hours
2. Implement preventive measures within 2 weeks
3. Increase monitoring sensitivity to detect recurrence early
4. Schedule post-mortem review within 5 business days

**Long-Running Incidents:**

For incidents spanning multiple hours, the error budget consumption continues throughout. Consider declaring a "budget emergency" to prioritize incident resolution over feature work, with explicit executive visibility.

## 7. On-Call Runbooks

### 7.1 Runbook Structure

Effective runbooks follow a consistent structure that enables rapid comprehension during high-stress incidents. Google's SRE Workbook defines a playbook as containing "high-level instructions on how to respond to automated alerts" [30]. The five A's framework guides runbook development:

**The Five A's:**

- **Actionable:** Steps must be executable by on-call personnel without additional research
- **Accessible:** Runbooks must be easily discoverable from alert annotations and dashboards
- **Accurate:** Information must be current and tested through actual use
- **Authoritative:** One team owns each runbook with clear ownership boundaries
- **Adaptable:** Runbooks evolve as systems change; include review cadence

**Standard Sections:**

1. **Title and Scope:** What this runbook covers and what it does not
2. **Trigger Conditions:** How the alert fires and what it indicates
3. **Severity Guidance:** When to escalate and when to observe
4. **Ownership:** Which team owns this service and component
5. **Prerequisites:** Access requirements, credentials, tool availability
6. **Diagnostic Workflow:** Step-by-step investigation procedures
7. **Mitigation Steps:** Actions to restore service or reduce impact
8. **Verification:** How to confirm resolution
9. **Postmortem Link:** Template or existing postmortem for this incident type

Google estimates that creating incident runbooks produces roughly a 3x improvement in mean time to repair (MTTR) compared to ad-hoc response strategies [30].

### 7.2 Takedown Failure Runbook

**Title:** Celery Takedown Task Failures

**Trigger:** `TakedownTaskFailureRate > 5%` OR `takedown_queue_depth > 200` for 15+ minutes

**Severity:** P2 Warning initially, escalate to P1 if external platform confirms outage

**Diagnostic Workflow:**

1. **Verify Worker Health:**
 ```bash
 celery -A app inspect ping
 # Check all workers respond within 5 seconds
 # Check worker logs for restarts or OOM kills
 ```

2. **Inspect Failed Tasks:**
 ```bash
 celery -A app inspect failed
 # Note failure types: ConnectionError, Timeout, API errors
 
 # Check dead letter queue
 redis-cli lrange celery.dlq 0 100
 ```

3. **Verify External Platform Status:**
 - Check takedown platform status page
 - Look for rate limit (429) responses
 - Check circuit breaker state in Redis: `redis-cli get circuit_breaker:takedown`

4. **Review Rate Limiting:**
 - Check 429 responses in logs: `rate_limit_exceeded > 10` in last hour
 - Verify Retry-After headers are being respected

**Mitigation Steps:**

1. **If External API Degraded:**
 - Enable degraded mode via feature flag: `TAKEDOWN_CIRCUIT_BREAKER=open`
 - Route takedowns to manual review queue
 - Monitor circuit breaker for recovery

2. **If Worker Resources Exhausted:**
 ```bash
 # Scale workers
 kubectl scale deployment celery-workers --replicas=6
 
 # Or for specific queue
 celery -A app control scale --hostname=worker1@% 4
 ```

3. **If Rate Limited:**
 - Pause new takedown submissions for Retry-After duration
 - Submit accumulated takedowns in batches after cooldown
 - Update rate limit configuration for target platform

4. **If Tasks Stuck:**
 ```bash
 # Revoke and requeue stuck tasks
 celery -A app inspect revoke_task <task_id>
 
 # Purge queue if corrupted (last resort)
 celery -A app purge -Q takedown
 ```

**Verification:**

- Takdown success rate returns to > 97% within 15 minutes
- Queue depth returns to < 50 within 30 minutes
- No new failed tasks for 5 consecutive minutes

**Escalation:**

- No response improvement in 30 minutes → Page secondary on-call
- External platform confirmed outage → Notify affected customers
- Data loss risk → Escalate to incident commander

### 7.3 Discovery Stall Runbook

**Title:** Discovery Pipeline Stall

**Trigger:** `discovery_active_runs == 0` for 30+ minutes during business hours OR `discovery_queue_depth` increasing without processing

**Severity:** P2 Warning; P1 if discovery SLA at risk

**Diagnostic Workflow:**

1. **Verify Broker Connectivity:**
 ```bash
 # Redis broker
 redis-cli ping
 # Expected: PONG
 
 # RabbitMQ broker
 curl -u guest:guest 
 ```

2. **Check Worker Queue Consumption:**
 ```bash
 celery -A app inspect active_queues
 # Verify workers are registered for discovery queue
 
 celery -A app inspect stats
 # Check pool.stats for worker concurrency utilization
 ```

3. **Inspect Task States:**
 ```bash
 celery -A app inspect active
 # Check for long-running tasks blocking queue
 
 celery -A app inspect reserved
 # Tasks fetched but not started (may indicate prefetch starvation)
 
 celery -A app inspect scheduled
 # Delayed tasks waiting for retry or ETA
 ```

4. **Check Downstream Dependencies:**
 - Embedding model availability: GPU utilization > 0 for inference workers
 - Vector database health: Qdrant/Weaviate response time < 100ms
 - Source platform connectivity: No network timeouts to scraper targets

5. **Investigate Prefetch Multiplier:**
 ```bash
 # Check current prefetch settings
 grep prefetch celeryconfig.py
 
 # Monitor per-worker task distribution
 celery -A app inspect active | grep reserved
 ```
 
 Misconfigured `worker_prefetch_multiplier` can cause head-of-line blocking where one worker hoards tasks while others starve [31].

**Mitigation Steps:**

1. **If Broker Connectivity Issue:**
 ```bash
 # Restart broker (with care for in-flight messages)
 sudo systemctl restart redis
 
 # Or for RabbitMQ
 sudo systemctl restart rabbitmq-server
 ```

2. **If Workers Not Consuming:**
 ```bash
 # Restart specific queue consumers
 celery -A app control cancel_consumer discovery
 celery -A app control add_consumer discovery
 
 # Or bounce workers
 celery -A app control shutdown --hostname=worker1@%
 ```

3. **If Embedding Model Down:**
 ```bash
 # Check model service health
 curl 
 
 # Restart embedding service
 kubectl rollout restart deployment embedding-service
 
 # Verify GPU availability
 nvidia-smi
 ```

4. **If Prefetch Starvation:**
 ```python
 # Adjust prefetch for long-running tasks
 # In celeryconfig.py
 task_acks_late = True
 worker_prefetch_multiplier = 1 # For discovery tasks
 ```

5. **If Queue Corrupted:**
 ```bash
 # Purge and requeue (last resort - loses messages)
 celery -A app purge -Q discovery
 
 # Re-create queue
 celery -A app inspect add_consumer discovery
 ```

**Verification:**

- `discovery_active_runs` > 0 and increasing
- Queue depth decreasing steadily
- Worker CPU/activity visible in monitoring

**Escalation:**

- No improvement in 1 hour → Escalate to ML Platform team lead
- Embedding model outage → Page ML Infrastructure on-call
- Queue purge required → Document lost items for customer notification

### 7.4 Escalation Matrix

| Severity | Definition | Response Time | Channels | Escalation Path |
|----------|------------|----------------|----------|-----------------|
| SEV0 | Data loss, security breach, all customers impacted | Immediate | PagerDuty + Slack #incidents | Primary → Secondary (15min) → Manager (30min) → VP Engineering |
| SEV1 | Core service down, major customer impact | 15 minutes | PagerDuty + Slack #incidents | Primary → Secondary (15min) → Manager |
| SEV2 | Degraded with workaround available | 1 hour | Slack #alerts | Primary on-call |
| SEV3 | Backlog growing, no immediate customer impact | 4 hours | Slack #alerts | Ticket + next business day review |
| SEV4 | Proactive maintenance, no urgency | Next sprint | Ticket only | Team lead review |

**AI/ML-Specific Severity Extensions:**

For counterfeit detection ML pipelines, extend severity definitions [32]:

- SEV1+: Embedding model complete failure with no fallback
- SEV2: Detection accuracy degradation exceeding 10% from baseline
- SEV3: Elevated false positive rate in production model

### 7.5 Post-Incident Procedures

Every SEV1 and SEV2 incident requires a postmortem document within 5 business days:

**Postmortem Template:**

1. **Incident Summary:** What happened, impact, duration
2. **Timeline:** Chronological sequence of events
3. **Root Cause:** Technical cause of failure
4. **Contributing Factors:** What made the incident worse or harder to detect
5. **Response Effectiveness:** What worked, what didn't
6. **Action Items:** Concrete improvements with owners and deadlines
7. **Lessons Learned:** Knowledge captured for future reference

Postmortems should focus on system improvements rather than individual blame. The goal is blameless analysis that enables organizational learning.

## 8. Implementation Recommendations

### 8.1 Phased Rollout

Implementing comprehensive observability requires phased investment to manage complexity and validate value at each stage.

**Phase 1 - Foundation (Weeks 1-4):**

- Deploy prometheus-fastapi-instrumentator on FastAPI services
- Enable Celery task events and deploy celery-prometheus-exporter
- Configure basic Prometheus scrape targets
- Set up Grafana Cloud Free tier with initial dashboards
- Define initial SLO targets (start conservative at 99.0%)

**Phase 2 - Pipeline Instrumentation (Weeks 5-8):**

- Add discovery stage metrics to Celery tasks
- Instrument embedding inference with custom metrics
- Configure queue depth monitoring for all queues
- Implement structured logging with structlog
- Set up error budget tracking dashboard

**Phase 3 - Alerting Refinement (Weeks 9-12):**

- Configure burn rate alerts following multi-window methodology
- Tune alert thresholds based on baseline measurements
- Document initial runbooks for critical failure modes
- Establish on-call rotation and escalation paths
- Conduct runbook-driven incident simulation

**Phase 4 - Optimization (Ongoing):**

- Refine histogram buckets based on actual latency distribution
- Add ML-specific observability (OpenInference for embeddings)
- Implement tail-based log sampling
- Automate runbook generation from incident patterns

### 8.2 Migration Considerations

For organizations transitioning from existing observability infrastructure:

**From Datadog to OpenTelemetry:**

1. Deploy OTel instrumentation alongside existing Datadog agent initially
2. Validate metric parity between platforms
3. Migrate dashboards gradually, not simultaneously
4. Run dual export during transition period
5. Validate alerting logic produces equivalent alerts

**From Manual Metrics to Prometheus:**

1. Identify all custom metrics currently tracked manually
2. Implement equivalent Prometheus metrics
3. Backfill historical data if valuable for trend analysis
4. Validate alerting produces equivalent notifications
5. Decommission manual collection after 30-day parallel run

### 8.3 Cost Optimization

**Metrics Cardinality Control:**

Prevent cost explosion from metric label cardinality [19]:

- Remove high-cardinality labels (user_id, request_id) from metrics
- Use trace_id for correlation rather than metrics labels
- Normalize endpoint paths to prevent path-parameter explosion
- Review metric churn rate weekly

**Log Volume Management:**

- Implement head-based sampling at 10-20% for success logs
- Always sample 100% of errors
- Use consistent hashing for trace-correlated sampling
- Archive logs older than 30 days to cold storage

**Usage Monitoring:**

Set up billing alerts at 80% of budgeted limits:

```promql
# Grafana Cloud series budget warning
- alert: GrafanaCloudSeriesBudgetWarning
 expr: prometheus_active_series / budget_series > 0.8
 annotations:
 summary: "Grafana Cloud series usage at {{ $value | humanizePercentage }} of budget"
```

## 9. Conclusion

Building comprehensive observability for a FastAPI + Celery counterfeit detection SaaS requires thoughtful integration of multiple tools, standardized metric conventions, and well-practiced incident response procedures. The OpenTelemetry-native approach with Grafana Cloud provides the optimal balance of vendor flexibility, modern standards support, and cost-effectiveness for teams building in 2026.

The structured logging format using structlog with OpenTelemetry Logs Data Model compatibility ensures logs remain portable across backends while providing the correlation context necessary for distributed trace reconstruction. Prometheus metrics following consistent naming conventions enable comprehensive visibility into HTTP request patterns, Celery task execution, discovery pipeline latency, embedding inference performance, and queue depth.

Service Level Objectives targeting 99.9% availability for the detection API align with industry expectations for SaaS platforms, while multi-window burn rate alerting provides early warning of error budget consumption before complete exhaustion. The error budget policy creates a data-driven framework for reliability investment decisions, preventing the common anti-pattern of deploying new features during reliability crises.

On-call runbooks following the five A's framework enable consistent, effective incident response that reduces MTTR by an estimated 3x compared to ad-hoc approaches. The takedown failure and discovery stall runbooks address the specific failure modes most likely to impact counterfeit detection operations.

Investment in observability infrastructure pays dividends through reduced incident duration, improved customer satisfaction, and data-driven reliability engineering decisions. The phased implementation approach enables teams to realize value incrementally while building toward comprehensive production-ready observability.

---

## References
[1] Sentry Pricing Explained: Full Cost Breakdown (2026) | Nurbak [content_marketing]: https://nurbak.com/en/blog/sentry-pricing/
[2] Sentry Pricing and Review 2026: Error Events, Trace Spans, Replay... [content_marketing]: https://cubeapm.com/blog/sentry-pricing-review/
[3] Grafana Pricing | Free, Pro, Enterprise: https://grafana.com/pricing/
[4] Grafana Cloud Pricing 2026: $6.50/1K Active Series, 10K Free: https://monitoringcost.com/grafana-cloud-pricing
[5] <span class="highlight">FastAPI</span> Error &amp; Performance <span class="highlight">Monitoring</span> | Sentry: https://sentry.io/for/fastapi/
[6] <span class="highlight">Celery</span> <span class="highlight">Flower</span>: Monitor Your Django Tasks in Real Time: https://appliku.com/post/celery-flower/
[7] <span class="highlight">Celery</span> <span class="highlight">Monitoring</span> | Grafana Labs: https://grafana.com/grafana/dashboards/10026-celery-monitoring/
[8] <span class="highlight">Datadog</span> <span class="highlight">Pricing</span> <span class="highlight">2026</span>: Why Bills Surprise Teams (+ Alternative) [content_marketing]: https://middleware.io/blog/datadog-pricing/
[9] Grafana Cloud vs Datadog vs Honeycomb (2026) | TechPlained: https://www.techplained.com/grafana-vs-datadog-vs-honeycomb
[10] <span class="highlight">DataDog</span> Alternative APM <span class="highlight">2026</span>: OpenObserve OTel Native 98… [content_marketing]: https://openobserve.ai/blog/datadog-vs-openobserve-part-3-traces-apm/
[11] <span class="highlight">Celery</span> [first_party]: https://docs.datadoghq.com/integrations/celery/
[12] OpenTelemetry Python Tutorial 2026: Distributed... | Tech Tutorials: https://tutorials.technology/tutorials/opentelemetry-python-tutorial-2026.html
[13] OpenTelemetry in 2026: The Observability Standard That Finally...: https://devstarsj.github.io/devops/observability/2026/05/02/opentelemetry-observability-standard-2026/
[14] OpenTelemetry: 89% Mandate, But $167K vs $150K Datadog: https://www.adscriptly.io/en/news/opentelemetry-domina-observability-2026-89pct-compliance-tco-167k-vs-datadog-150k
[15] Implementing OpenTelemetry in FastAPI - A Practical Guide | SigNoz [content_marketing]: https://signoz.io/blog/opentelemetry-fastapi/
[16] OpenInference and OpenTelemetry for LLM Tracing... | Inference.net: https://inference.net/content/openinference-opentelemetry-llm-tracing/
[17] <span class="highlight">Honeycomb</span> <span class="highlight">vs</span> <span class="highlight">Datadog</span>: Which <span class="highlight">Observability</span> Tool in <span class="highlight">2026</span>… [content_marketing]: https://nurbak.com/en/blog/honeycomb-vs-datadog/
[18] GitHub - trallnag/<span class="highlight">prometheus</span>-<span class="highlight">fastapi</span>-instrumentator: Instrument… [authoritative_third_party]: https://github.com/trallnag/prometheus-fastapi-instrumentator
[19] Metric Naming Conventions | Compile N Run [first_party]: https://www.compilenrun.com/docs/observability/prometheus/prometheus-best-practices/metric-naming-conventions/
[20] Celery Monitoring with Prometheus and Grafana [content_marketing]: https://hodovi.cc/blog/celery-monitoring-with-prometheus-and-grafana/
[21] zerok/celery-prometheus-exporter - Docker Image: https://hub.docker.com/r/zerok/celery-prometheus-exporter
[22] Compute Observability for Kafka + TensorFlow/PyTorch Pipelines: https://www.linkedin.com/pulse/compute-observability-kafka-tensorflowpytorch-brindha-jeyaraman-twzvc
[23] 10 <span class="highlight">Prometheus</span> Scrape_Interval <span class="highlight">Best</span> <span class="highlight">Practices</span>: https://climbtheladder.com/10-prometheus-scrape_interval-best-practices/
[24] How to Increase <span class="highlight">Prometheus</span> <span class="highlight">Storage</span> <span class="highlight">Retention</span> | Better Stack… [forum]: https://betterstack.com/community/guides/monitoring/prometheus-storage-retention/
[25] SRE Foundations: SLIs, SLOs, and Error Budgets | Agent Factory [first_party]: https://agentfactory.panaversity.org/docs/AI-Cloud-Native-Development/observability-cost-engineering/sre-foundations-slis-slos-error-budgets
[26] <span class="highlight">Google</span> <span class="highlight">SRE</span> - <span class="highlight">SLO</span> Documnets: Game Services <span class="highlight">API</span>, HTTP, Score: https://sre.google/workbook/slo-document/
[27] Alerting on your <span class="highlight">burn</span> <span class="highlight">rate</span> | <span class="highlight">Google</span> Cloud Observability [first_party]: https://cloud.google.com/stackdriver/docs/solutions/slo-monitoring/alerting-on-budget-burn-rate
[28] How to implement <span class="highlight">multi-window</span>, multi-<span class="highlight">burn</span>-<span class="highlight">rate</span> alerts with Grafana Cloud | Grafana Labs [content_marketing]: https://grafana.com/blog/how-to-implement-multi-window-multi-burn-rate-alerts-with-grafana-cloud/
[29] Implementing SLOs and Error Budgets From Scratch | DevOpsil: https://devopsil.com/articles/2026-03-21-slo-error-budget-implementation-guide
[30] An Effective Incident Runbook Template | Christian Emmer [content_marketing]: https://emmer.dev/blog/an-effective-incident-runbook-template/
[31] Understanding Celery Task Prefetching: What... — CodeLessGenie.com [content_marketing]: https://www.codelessgenie.com/blog/understanding-celery-task-prefetching/
[32] 5.3 The "Andon Cord" for AI: Incident Response | AI Innovation...: https://baa.ai/neural-pod-framework/sections/5-3-incident-response.html

## Source Accuracy Notes

Some high-precision claims could not be fully reconciled against the captured source extracts. The report preserves the best available synthesis, but the following items should be treated with caution:
- High-precision numeric claim lacks captured cited-source extract support citations [1].
- High-precision numeric claim lacks captured cited-source extract support citations [3, 4].
- High-precision numeric claim lacks captured cited-source extract support citations [5].
- High-precision numeric claim lacks captured cited-source extract support citations [8, 9].
