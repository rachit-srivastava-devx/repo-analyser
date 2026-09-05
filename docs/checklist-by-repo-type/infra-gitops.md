# Infra/GitOps Repo

*Part of the [Meta & Content-Purpose Repos](README.md) family: Smaller categories, sorted by what's inside rather than how code is split: a repo that only points at other repos, a published package, infrastructure-as-code, or pure documentation.*

## How to Detect This Repo Type

| Signal | How to Check |
|---|---|
| **Majority .tf/.tf.json, or Chart.yaml (Helm), or kustomization.yaml; CI runs plan/apply/helm template** | `cloc --by-file-by-lang .`, `file-extension ratio` |

## Audit Checklist

| Criterion | What It Checks | Tools (keyless-first) |
|---|---|---|
| **Infra drift detection** | live cloud/cluster state vs. what the repo declares, catching manual console changes or half-applied runs. | `OpenTofu/Terraform plan -detailed-exitcode`, `Steampipe` |
| **Policy-as-code compliance** | every proposed change validated against org security/cost/tagging rules before merge, not just "does it apply cleanly." | `OPA`, `Conftest`, `Kyverno` |
| **IaC security/misconfiguration scanning** | open security groups, public buckets, missing encryption caught pre-merge rather than in prod. | `Trivy (tfsec merged in)`, `Checkov`, `Terrascan` |
| **Secret leakage in IaC files** | hardcoded credentials/keys committed in .tf/values.yaml/manifests instead of pulled from a vault. | `gitleaks`, `TruffleHog` |
| **Plan/apply review discipline** | no apply/upgrade happens without a reviewed plan tied to the exact merged commit; no applies from a laptop. | `Atlantis`, `OpenTaco (formerly Digger)` |
| **GitOps reconciliation health** | cluster state continuously reconciled against the repo, with alerting on sync failures or prolonged OutOfSync. | `Argo CD`, `Flux` |
| **State file integrity & locking** | remote (not local/committed) state, encrypted at rest, with locking to block concurrent-apply races. | `Terraform/OpenTofu native state locking`, `Terragrunt remote_state` |
| **Least-privilege pipeline credentials** | the identity CI assumes to apply changes is scoped to only what this repo should touch, via short-lived federated credentials. | `OIDC federation to cloud IAM`, `cloudsplaining` |
| **Blast-radius / change-impact analysis** | whether a bad merge touches an isolated dev namespace or the shared prod VPC/cluster, sized before merge. | `terraform plan diff review`, `Rover (plan visualizer)` |
| **Module/chart version pinning** | Terraform modules and Helm charts referenced at pinned versions with a controlled upgrade path, never latest/floating. | `Renovate (Terraform & Helm)`, `terraform-docs` |
| **Module functional testing** | whether a module actually provisions correctly, independent of security/policy rules. | `native terraform test`, `Terratest` |
| **Orphaned/unmanaged resource detection** | live cloud resources never declared anywhere, structurally invisible to state-diff drift tools that only compare already-tracked resources. | `Steampipe`, `Cloud Custodian` |
| **IaC provider/module CVE monitoring** | Terraform providers and modules are watched on a schedule for newly disclosed CVEs, not just scanned once at the time a version was pinned. | `Renovate (tracks provider/module registry advisories)`, `Trivy (scheduled re-scan of pinned versions)` |
