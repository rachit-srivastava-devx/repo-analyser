# ML / Data Science Repo

*Part of the [Meta & Content-Purpose Repos](README.md) family: Smaller categories, sorted by what's inside rather than how code is split: a repo that only points at other repos, a published package, infrastructure-as-code, or pure documentation.*

## How to Detect This Repo Type

| Signal | How to Check |
|---|---|
| `.ipynb` notebooks, `dvc.yaml`/`.dvc` files, or a requirements file naming torch/tensorflow/scikit-learn/pandas as primary dependencies | `find . -name "*.ipynb" | wc -l` · `cat dvc.yaml` |

## Audit Checklist

| Criterion | What It Checks | Tools (keyless-first) |
|---|---|---|
| **Experiment reproducibility** | a training run pins its random seed, dependency/environment snapshot, and exact dataset version so the result can be regenerated bit-for-bit later, not merely approximated. | `MLflow`, `DVC` |
| **Data drift / schema validation** | incoming data is validated against an expected schema and reference distribution before drift silently degrades a production model's quality. | `Great Expectations`, `Evidently AI`, `TensorFlow Data Validation` |
| **Model performance regression testing** | a candidate model's held-out metrics are diffed against the currently-deployed model's before promotion, catching a real quality regression that a "does it run" check would miss. | `Deepchecks`, `CML (Continuous Machine Learning)` |
| **Training data lineage / provenance** | which dataset version and commit/hash, run through which pipeline, produced a given model artifact is traceable end to end instead of reconstructed from memory. | `DVC`, `lakeFS` |
| **Model registry versioning** | trained models are versioned in a registry with lineage and metadata attached, not left as unlabeled loose files in a bucket. | `MLflow Model Registry`, `BentoML` |
| **Notebook hygiene** | committed notebooks have outputs cleared, carry no hardcoded secrets or absolute paths, and actually re-execute top-to-bottom in a fresh kernel instead of only having "run once, out of order." | `nbstripout`, `nbQA`, `papermill`, `Gitleaks` |
| **Model card / documentation completeness** | intended use, training-data summary, known limitations, and evaluation metrics are documented per model in a standard template instead of surviving only as tribal knowledge. | `Hugging Face Model Cards`, `markdownlint-cli` |
| **Bias/fairness evaluation** | model performance is broken out across relevant demographic/subgroup slices to catch disparate error rates an aggregate accuracy number would hide. | `Fairlearn`, `AI Fairness 360` |
| **GPU/compute cost tracking** | per-experiment GPU utilization, energy draw, and job cost are tracked so idle or oversized training runs are visible instead of buried in a monthly cloud bill. | `OpenCost`, `NVIDIA DCGM Exporter`, `CodeCarbon` |
| **Model/artifact size and storage hygiene** | large model binaries and datasets are tracked through dedicated large-file tooling instead of bloating git's own object store with every version. | `DVC`, `Git LFS`, `git-annex` |
