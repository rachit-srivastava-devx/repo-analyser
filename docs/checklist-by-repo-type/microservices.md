# Microservices

Many small, independently deployable services talking over a network — layered on top of either a monorepo or a polyrepo. These criteria exist only because a call can now fail, be slow, or arrive twice.

## How to Detect This Repo Type

| Signal | How to Check |
|---|---|
| **Multiple Dockerfiles, or docker-compose.yml/k8s manifests declaring 2+ Deployments** | find . -iname Dockerfile \| wc -l, `docker-compose config --services` |
| **Istio/Linkerd CRDs (VirtualService, DestinationRule) or sidecar-injection annotations in YAML** | `kubectl get virtualservices,destinationrules -A` |

## Audit Checklist

### Service Boundary & Domain Alignment

| Criterion | What It Checks | Tools (keyless-first) |
|---|---|---|
| **Bounded-context alignment** | each service maps to one DDD bounded context/business capability, not a technical layer sliced across services. | `Context Mapper`, `Service Cutter`, `EventStorming` |
| **Distributed-monolith detection** | flag services that must be deployed together or version in lockstep; if one can't ship without coordinating others, it isn't independently deployable. | `Backstage catalog`, `custom CI/CD coupling-audit script`, `MSANose` |
| **Shared-database smell** | multiple services reading/writing the same tables directly instead of going through an owning service's API. | `MSANose`, `pgAudit`, `custom FK-scan script` |
| **God-service / hub-service smell** | one service with disproportionate fan-in or fan-out becomes a coordination bottleneck and single point of failure. | `Jaeger service graph`, `Kiali`, `MSANose` |
| **Chatty-service smell** | a single business operation requiring an excessive number of synchronous cross-service calls signals a wrong cut. | `OpenTelemetry`, `Jaeger`, `MSANose` |
| **Cyclic service dependencies** | A→B→C→A cycles create deployment-ordering deadlocks and let failures propagate in a loop. | `MSANose`, `Kiali`, `NetworkX cycle-detection script` |
| **Data-ownership violation** | each entity/table has exactly one owning service; all other access goes through its API or published events. | `Backstage catalog`, `custom schema-ownership script` |
| **Team/Conway's-Law alignment** | service boundaries roughly track team ownership so a routine change doesn't require cross-team coordination. | `Backstage catalog`, `custom CODEOWNERS-to-service script` |

### Inter-Service Communication Resilience

| Criterion | What It Checks | Tools (keyless-first) |
|---|---|---|
| **Sync-vs-async coupling audit** | identify synchronous call chains that should be event/queue-based given latency and availability needs. | `OpenTelemetry`, `Jaeger`, `Grafana Tempo` |
| **Timeout configuration correctness** | every outbound call has an explicit timeout strictly less than the caller's own SLA budget, propagated consistently down the chain. | `Istio DestinationRule`, `cockatiel Timeout (JS/TS)`, `context.WithTimeout (Go)`, `tower TimeoutLayer (Rust)`, `asyncio.wait_for (Python)` |
| **Retry policy correctness** | bounded attempts, exponential backoff with jitter, no retrying of non-idempotent operations. | `Envoy retry policy`, `cockatiel Retry (JS/TS)`, `avast/retry-go (Go)`, `tower Retry layer (Rust)`, `tenacity (Python)` |
| **Circuit-breaker coverage & tuning** | every external dependency call wrapped with sane failure-rate thresholds and a verified half-open probe path. | `Istio outlier detection`, `cockatiel CircuitBreaker (JS/TS)`, `sony/gobreaker (Go)`, `failsafe-rs (Rust)`, `pybreaker (Python)` |
| **Cascading-failure risk** | no unbounded retry-on-retry across hops; a slow dependency degrades locally instead of propagating latency upstream. | `Chaos Mesh`, `LitmusChaos`, `k6` |
| **Bulkhead isolation** | per-dependency thread/connection pools so one slow dependency can't exhaust shared resources. | `Envoy per-cluster pool limits`, `cockatiel Bulkhead (JS/TS)`, `golang.org/x/sync/semaphore (Go)`, `tower ConcurrencyLimitLayer (Rust)`, `asyncio.Semaphore (Python)` |
| **Backpressure & load shedding** | producers/consumers signal and respect capacity limits instead of buffering unbounded. | `Envoy adaptive concurrency`, `Burrow` |
| **Idempotency verification** | retried or duplicated requests must not double-apply side effects. | `Newman replay scripts`, `Toxiproxy` |
| **Delivery-semantics audit** | confirm each topic/queue's actual guarantee (at-least-once, at-most-once, effectively-once) matches what producers/consumers assume. | `rabbitmqadmin`, `kafka-consumer-groups.sh` |

### Data Consistency & Distributed Transactions

| Criterion | What It Checks | Tools (keyless-first) |
|---|---|---|
| **Distributed-transaction (2PC/XA) usage audit** | flag any two-phase-commit spanning services; a red flag for availability and scalability. | `Semgrep`, `ast-grep` |
| **Saga pattern implementation correctness** | every saga step has a compensating action, steps are idempotent and resumable after a crash. | `Temporal — TS SDK`, `Temporal — Go SDK`, `Temporal — Rust SDK (preview)`, `Temporal — Python SDK` |
| **Dual-write problem detection** | flag code paths writing to a DB and separately publishing to a broker without atomicity. | `Semgrep custom rule`, `ast-grep` |
| **Transactional outbox verification** | state change and its event committed in one local transaction, then relayed via CDC, wired end-to-end. | `Debezium`, `Kafka Connect`, `Testcontainers` |
| **Eventual-consistency window correctness** | document and test max staleness per read path, including read-your-own-writes cases. | `Toxiproxy`, `Chaos Mesh` |
| **Idempotent consumers** | message consumers dedupe on a business key so redelivery can't corrupt state. | `kafka-consumer-groups.sh`, `dedup-table audit script` |
| **Compensating-transaction coverage** | for every forward saga step, a tested rollback exists. | `Chaos Mesh (mid-saga kill)`, `Temporal test framework` |
| **CQRS read-model lag monitoring** | lag between write model and read projections measured and alerted against an explicit SLA. | `Debezium`, `KMinion`, `Prometheus + Grafana` |
| **Cross-service referential integrity** | no service assumes synchronous FK-style integrity against another service's data without handling race conditions. | `Pact contract tests`, `ArchUnitTS (JS/TS)`, `arch-go (Go)`, `cargo-modules (Rust)`, `import-linter (Python)` |

### Observability & Monitoring

| Criterion | What It Checks | Tools (keyless-first) |
|---|---|---|
| **Distributed tracing coverage** | % of service-to-service calls emitting spans; audit gaps at async hops and message consumers that drop trace context. | `OpenTelemetry Collector`, `Jaeger`, `Grafana Tempo` |
| **Correlation-ID / trace-context propagation** | W3C traceparent propagated across every hop, including message headers, not just HTTP. | `OpenTelemetry context propagation` |
| **Log-trace-metric correlation** | logs and metrics tagged with trace_id/span_id so an incident pivots without manual correlation. | `Grafana Loki`, `Grafana Tempo`, `Grafana Mimir` |
| **Per-service SLOs & error budgets** | each service has an explicit SLO tied to a budget that gates releases when burned. | `Sloth`, `Prometheus recording rules` |
| **Four golden signals per service** | latency, traffic, errors, saturation dashboards exist per service, not only system-wide. | `Prometheus`, `Grafana (RED dashboards)` |
| **USE-method saturation tracking** | utilization/saturation/errors tracked per-service resource to catch saturation before it manifests as latency. | `node_exporter`, `cAdvisor` |
| **Symptom-based alerting** | alerts fire on user-facing SLO burn rate, routed to the owning service's on-call. | `Alertmanager`, `Prometheus burn-rate rules` |
| **Service dependency map freshness** | auto-generated service graph from live traces, kept current and used during incidents to bound blast radius. | `Kiali`, `Cilium Hubble` |

### Resilience & Chaos Testing

| Criterion | What It Checks | Tools (keyless-first) |
|---|---|---|
| **Chaos engineering coverage** | % of critical services with a scheduled or triggered fault-injection experiment. | `LitmusChaos`, `Chaos Mesh`, `Gremlin` *(keyed)*, `AWS FIS` *(keyed)* |
| **Game days / failure drills** | recurring exercises simulating real outages with defined success criteria and a blameless retro. | `Chaos Mesh workflows`, `LitmusChaos workflows`, `Gremlin scenarios` *(keyed)* |
| **Dependency failure simulation** | verify graceful degradation when each downstream is slow or fully down, not just fully available. | `Toxiproxy`, `Chaos Mesh`, `LitmusChaos` |
| **Per-service load & stress testing** | each service load-tested in isolation to find its own breaking point apart from end-to-end tests. | `k6`, `Gatling`, `Locust` |
| **System-wide load testing** | full request-path load test through the real service graph to surface emergent bottlenecks. | `k6 Operator`, `distributed JMeter` |
| **Soak/endurance testing** | extended-duration runs catch memory/connection leaks short load tests miss. | `k6 (soak scenarios)`, `Gatling (long-duration)` |
| **Chaos-as-a-release-gate** | fault-injection experiments run automatically in CI/pre-prod, not only reactively in production. | `LitmusChaos GitOps CRDs`, `Chaos Mesh Workflow CRDs` |
| **Recovery-time verification** | measure actual MTTR against target after each induced failure. | `Chaos Mesh (kill experiments)`, `Prometheus recovery-time queries`, `Gremlin` *(keyed)* |

### API Contract Management

| Criterion | What It Checks | Tools (keyless-first) |
|---|---|---|
| **Consumer-driven contract testing** | each consumer's expectations captured as contracts and verified against the real provider in CI. | `Pact`, `Pact Broker (self-hosted)` |
| **Schema versioning discipline** | APIs and event schemas versioned explicitly with a documented deprecation policy. | `Apicurio Registry`, `buf` |
| **Backward-compatibility verification** | automated check that a new schema/API version is a compatible superset before merge. | `buf breaking`, `oasdiff` |
| **Event schema governance** | event payloads validated against a registered schema at publish time so a producer can't silently corrupt every consumer. | `Apicurio Registry`, `Karapace` |
| **API gateway configuration correctness** | routing, auth policy, rate-limit config audited against the actual service inventory. | `Kong Gateway (OSS)`, `Envoy Gateway`, `Apache APISIX` |
| **Rate limiting & quota enforcement** | per-consumer/per-route limits enforced consistently at the gateway/mesh layer. | `Kong rate-limiting plugin (OSS)`, `Envoy rate limit service` |
| **Deprecation & sunset tracking** | old API/schema versions have a tracked sunset date and telemetry on remaining callers before removal. | `Sunset header audit script`, `Apicurio lifecycle states` |
| **Contract-first mocking** | provider stubs generated from the contract so consumers can build against a not-yet-built service without drift. | `Microcks`, `Pact stub server`, `Prism` |

### Service Mesh & Networking

| Criterion | What It Checks | Tools (keyless-first) |
|---|---|---|
| **mTLS coverage** | % of service-to-service traffic mutually authenticated and encrypted end-to-end, with plaintext explicitly disallowed. | `Istio PeerAuthentication`, `Linkerd auto-mTLS`, `Cilium mTLS` |
| **Certificate rotation & trust-domain audit** | workload certs auto-rotate before expiry and trust bundles stay consistent across clusters. | `SPIFFE/SPIRE`, `cert-manager` |
| **Service discovery health** | registry entries reflect actually-healthy instances, no stale/zombie endpoints. | `Kubernetes EndpointSlices`, `Consul (OSS)` |
| **Sidecar/proxy config drift** | deployed proxy config actually matches the declared CRDs, with no orphaned config surviving a rollout. | `istioctl analyze/proxy-status`, `Linkerd check` |
| **Network policy correctness (default-deny)** | namespace/service policies default-deny with explicit allows matched to observed real traffic. | `Cilium NetworkPolicy`, `Calico` |
| **East-west traffic visibility** | mesh telemetry captures pod-to-pod traffic, not just ingress, for audit and anomaly detection. | `Cilium Hubble`, `Istio + Kiali` |
| **Sidecar resource overhead** | proxy CPU/memory tax per pod measured and weighed against sidecar-less alternatives. | `Istio Ambient mode/ztunnel`, `Cilium eBPF mesh` |
| **Egress control** | outbound traffic restricted to an explicit allowlist rather than arbitrary internet access from any workload. | `Cilium egress policies`, `Istio Egress Gateway` |
| **Multi-cluster discovery consistency** | cross-cluster service identity and routing verified consistent, with failover behavior actually tested. | `Istio multi-cluster mesh`, `Cilium Cluster Mesh` |
| **Mesh control-plane/data-plane version-skew management** | the mesh's own control-plane upgrades are canaried and proxy/control-plane version skew stays within the vendor-supported window, distinct from checking deployed config against declared CRDs. | `Istio canary control-plane upgrades`, `istioctl precheck` |
| **Hard-coded service endpoints** | static-analysis check for literal IPs/hostnames bypassing service discovery entirely, still rated the single most harmful microservices anti-pattern in practitioner surveys. | `Semgrep custom rule`, `grep/regex CI gate` |

### Deployment Safety & Release Management

| Criterion | What It Checks | Tools (keyless-first) |
|---|---|---|
| **Independent deployability verification** | prove a single service ships to prod without a coordinated multi-service release train. | `Argo CD`, `Backstage`, `pipeline-coupling audit script` |
| **Blast-radius containment** | a bad deploy is scoped via routing/flags/bulkheads so it can't take down unrelated services. | `Istio traffic shifting`, `Flagger/Argo Rollouts` |
| **Canary / progressive rollout configuration** | new versions get a small traffic percentage with automated metric analysis before promotion. | `Argo Rollouts`, `Flagger` |
| **Automated rollback triggers** | rollout analysis tied to real SLO/golden-signal metrics with automatic abort-and-rollback, not manual-only. | `Argo Rollouts AnalysisTemplate + Prometheus`, `Flagger + Prometheus` |
| **N/N-1 compatibility during rollout** | rolling deploys tested for old-and-new-version coexistence on both API and event schema. | `Pact Broker can-i-deploy`, `buf breaking vs. N-1` |
| **Database migration safety** | schema migrations backward/forward compatible with the prior service version (expand/contract). | `gh-ost`, `pt-online-schema-change`, `Liquibase/Flyway Community` |
| **Deploy/release decoupling via feature flags** | risky changes ship dark behind flags so "deployed" and "released" are separate events. | `Unleash`, `Flagsmith`, `OpenFeature` |
| **Dependency-aware rollout gating** | canary promotion considers downstream/upstream service health, not just the deployed service's own metrics. | `Flagger webhooks`, `Argo Rollouts AnalysisTemplate` |
| **Per-service DORA metrics** | deployment frequency and change-failure-rate tracked per service to catch ones de facto coupled to another's release cadence. | `Apache DevLake`, `Prometheus + Grafana deploy-event pipeline` |
| **Config-push canary/rollback parity** | configuration-only changes (feature flags, routing tables, ACLs, rate limits) go through the same staged-rollout and automated-rollback discipline as code deploys, since config causes most severe outages. | `Argo CD GitOps`, `OPA/Gatekeeper config gate` |
| **Deployment rework rate** | the share of deployments that are unplanned, reactive redeployments triggered by a production incident, tracked separately from change-failure-rate. | `Apache DevLake`, `Argo CD deploy history` |

### Security & Access Control

| Criterion | What It Checks | Tools (keyless-first) |
|---|---|---|
| **Service-to-service authentication** | every inter-service call cryptographically authenticated; no implicit trust from network location alone. | `SPIFFE/SPIRE`, `Istio/Linkerd mTLS` |
| **Service-to-service authorization** | fine-grained, least-privilege policy controlling which service identities may call which endpoints. | `Istio AuthorizationPolicy`, `OPA/Gatekeeper` |
| **Per-service secrets management** | secrets scoped per service rather than shared blanket credentials, injected at runtime with rotation. | `HashiCorp Vault (OSS)`, `External Secrets Operator` |
| **Zero-trust network posture** | no service relies on "inside the VPC/cluster = trusted"; every call is authenticated/authorized regardless of origin. | `SPIFFE/SPIRE`, `Istio/Cilium STRICT mTLS` |
| **Token/credential blast-radius** | short-lived, narrowly-scoped tokens per call instead of long-lived static API keys shared across many callers. | `Vault dynamic secrets`, `Vault PKI short-lived certs` |
| **Per-service supply-chain provenance** | each service's image signed and scanned independently, since a compromised dependency has a network path to every peer it talks to. | `Sigstore Cosign`, `Trivy`, `SLSA provenance` |
| **Cross-service audit logging** | security-relevant calls logged with caller identity for forensic reconstruction across the mesh during an incident. | `Envoy/Istio access logs`, `Grafana Loki`, `Wazuh` |
| **API data-exposure minimization** | services return only the fields consumers need, avoiding "whole entity" responses that leak internal data across trust boundaries. | `Spectral custom rule`, `Pact consumer schemas` |
| **Per-service CVE monitoring (continuous)** | each already-deployed service's dependency tree and base image are re-scanned on a schedule, not just at build time — so a CVE disclosed six months after deploy still gets caught and paged, distinct from provenance/signing at build time. | `Trivy (server mode, scheduled)`, `Grype (cron re-scan of deployed digests)`, `Dependabot security alerts` |

### Cost & Resource Efficiency

| Criterion | What It Checks | Tools (keyless-first) |
|---|---|---|
| **Per-service right-sizing** | CPU/memory requests/limits set from observed usage per service, not copy-pasted defaults. | `Goldilocks + Kubernetes VPA`, `OpenCost` |
| **Idle-service detection** | services with near-zero sustained traffic/CPU flagged for scale-to-zero, consolidation, or decommission. | `KEDA scale-to-zero`, `OpenCost idle-cost allocation` |
| **Over-provisioning audit** | utilization tracked against requests at workload and cluster level. | `OpenCost`, `Goldilocks/VPA recommender`, `kube-resource-report` |
| **Cost allocation / showback per service** | spend attributed down to namespace/service/team so owning teams see their own footprint. | `OpenCost`, `Grafana on OpenCost + Prometheus` |
| **Mesh/sidecar overhead cost** | proxy CPU/memory tax multiplied across every pod in the mesh, quantified against sidecar-less alternatives. | `Istio Ambient mode`, `OpenCost + cAdvisor` |
| **Autoscaling correctness** | HPA/VPA/KEDA thresholds reflect actual service-specific load patterns instead of defaults. | `KEDA`, `Kubernetes HPA/VPA`, `Karpenter` |
| **Redundant cross-cutting capability audit** | multiple services independently reimplementing the same concern (retry, auth, caching), a consolidation candidate into a shared platform capability. | `Semgrep cross-repo rule`, `jscpd fleet-wide scan` |
| **Cross-AZ/region data-transfer cost** | chatty cross-zone service calls measured for both added latency and egress cost. | `OpenCost network cost`, `Cilium topology-aware routing + Hubble` |
