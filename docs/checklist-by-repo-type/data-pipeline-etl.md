# Data-Pipeline / ETL Repo

*Part of the [Meta & Content-Purpose Repos](README.md) family: Smaller categories, sorted by what's inside rather than how code is split: a repo that only points at other repos, a published package, infrastructure-as-code, or pure documentation.*

## How to Detect This Repo Type

| Signal | How to Check |
|---|---|
| `dbt_project.yml`, a `dags/` directory (Airflow), or Dagster/Prefect project config, with no serving/app layer | `test -f dbt_project.yml` · `test -d dags` |

## Audit Checklist

| Criterion | What It Checks | Tools (keyless-first) |
|---|---|---|
| **Declarative data-quality tests per table** | not-null, uniqueness, and referential-integrity checks run against real table output on every run, not asserted once when the pipeline was first built. | `dbt tests`, `Great Expectations` |
| **DAG idempotency / safe-backfill review** | re-running a date range can't double-count or duplicate rows, verified explicitly rather than assumed from the pipeline working the first time it ran. | `Airflow DAG review`, `Astronomer Cosmos (dbt-in-Airflow)` |
| **End-to-end data lineage** | a downstream break can be traced back to the exact source transform that caused it, instead of every incident starting with "which of the 40 jobs touched this table." | `OpenLineage`, `Marquez` |
| **Freshness / SLA monitoring** | a table's actual update recency is checked against its declared SLA continuously, so silent staleness is caught before a consumer notices a stale dashboard. | `dbt source-freshness checks` |
| **Schema-drift / contract enforcement on upstream sources** | an upstream source changing shape without warning is caught at the pipeline boundary instead of silently corrupting every table downstream of it. | `dbt contracts` |
| **Warehouse query-cost regression** | a newly-added join or scan that spikes billed warehouse compute is caught in review, since a bad query here is billed compute, not just a slow response. | `dbt project evaluator` |
