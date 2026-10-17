# Implementation TODO — Cloud Resource Intelligence

Targets: `notebook.ipynb` holds the completed one-time dataset preparation (Module 1). `analysis.ipynb` loads its cached Parquet file and holds Modules 2 through 5. Keep explanatory Markdown and small, useful outputs.

## Scope and methodology

Keep the synopsis goals: workload characterization, future CPU/memory prediction, potential bottleneck detection, allocation comparison, and what-if analysis. Use a small Google Cluster Data **2011-2** subset and CPU-only scikit-learn models. No GPU, deep learning, full-cluster download, or cloud account is required for the intended workflow.

Google documents this version as approximately **41 GB compressed**, rather than terabytes: [official 2011 trace documentation](https://github.com/google/cluster-data/blob/master/ClusterData2011_2.md). We need only a subset. Preserve attribution to Google and its linked CC-BY license in the notebook.

Use task usage as the core table. Predict the next observed, contiguous reporting interval for each `(job_id, task_index)`; do not predict current CPU from other current CPU measurements. Keep normalized resource units rather than claiming they are physical cores or GB. Treat allocation and bottleneck results as a controlled simulation, not measured production failures. Disk/I/O remains a characterization feature; CPU and memory are the main prediction and allocation targets.

### Laptop limits and defaults

| Item | Initial setting |
|---|---|
| Paths | Colab default: `/content/drive/MyDrive/ml-project/` with `data/raw/`, `data/processed/`, `artifacts/`; configurable in the notebook |
| Pilot | One task-usage shard; inspect temporal coverage before expanding |
| Compressed download budget | 1,000,000,000 bytes total; actual metadata determines shard count |
| Total data/artifact disk cap | 2,500,000,000 bytes, including partial files and temporary writes |
| CSV processing | 50,000 rows/chunk; selected columns and explicit dtypes |
| Retained modeling rows | At most 300,000; reduce if memory diagnostics require it |
| RAM target | Aim for less than 1 GB of working data; actual process RAM must be measured |
| Model settings | Seed 42; bounded tree depth, roughly 100 trees, `n_jobs=1` |

Do not extract gzip files to full CSVs. Budget disk and RAM separately: a compressed size is not the pandas memory requirement. Reserve space before every write, count existing caches, and stop cleanly before exceeding the cap. Avoid duplicate caches and accumulating all chunks in a list. These are implementation limits, not already-measured performance guarantees.

## Module 1 — Notebook cleanup and bounded dataset loading

- [x] Replace the exploratory setup with imports, dependency instructions, a shared configuration cell, local paths, seed, and budgets. Keep meaningful schema inspection and a tiny data preview.
- [x] Remove failed `gcloud` experiments, CLI help dumps, raw bucket listings, documentation-printing/debug cells, duplicate inspection, and empty cells. Replace all `/content/...` paths. Clear stale outputs when restructuring.
- [x] Download and cache the official `schema.csv`; select the task-usage schema and verify its column order/count before reading data. The existing saved output has 20 columns; do not invent column names from guesses.
- [x] List public object metadata using `https://storage.googleapis.com/storage/v1/b/clusterdata-2011-2/o` with `prefix=task_usage/` and pagination via `nextPageToken`. Build a compact manifest with names, sizes, checksums where available, selection, and download status.
- [x] Start with `task_usage/part-00000-of-00500.csv.gz`. Use public HTTPS downloads, e.g. `https://storage.googleapis.com/clusterdata-2011-2/task_usage/part-00000-of-00500.csv.gz`. Check HTTP status before writing; use streaming, timeouts, bounded retries, `.part` files, size/checksum verification, and rename only after success. Reuse verified files on reruns.
- [x] Inspect the pilot's timestamps, task continuity, row count, and memory use. Add adjacent shards while within the byte budget if more history is needed. Verify actual time coverage rather than assuming shard numbers guarantee it. Do not download all tables or all 500 usage shards.
- [x] Read gzip directly with `pd.read_csv(..., compression='gzip', header=None, usecols=..., dtype=..., chunksize=50000)`. Keep IDs/timestamps as exact integers, not float32; use float32 for suitable usage measurements.
- [x] Retain a reproducible subset of task identities with their histories using a stable hash/seed, rather than independently sampling rows. If the row cap is exceeded, reduce the task selection and reprocess cached files; preserve chronological sequences. Avoid Python's process-randomized `hash()`.
- [x] Save a compact Parquet subset and manifest, with measured compressed bytes, retained rows/tasks, time range, disk use, and DataFrame memory. Report subset bias and missing coverage explicitly. The pilot may already be sufficient; 1 GB is a ceiling, not a download target.

**Done when:** rerunning reuses verified data, the notebook works with local paths, the schema matches, and bounded chunk processing produces a usable subset under the disk cap. Saved Colab outputs are evidence of an earlier run, not proof the downloaded file exists on this laptop.

**Prompt:** `Implement Module 1 from TODO.md in notebook.ipynb, including cleanup and the enforced dataset budgets. Validate with the pilot before expanding downloads.`

## Module 2 — Cleaning, temporal features, and exploratory analysis

**Implementation status:** Complete. The revised Colab run produced 159,546 exact 300-second pairs (108,945 train; 22,864 validation; 24,483 test; 3,254 purged). Features and training-only medians were saved, plots reviewed, and total data/artifact use was 558.5 MB.


- [x] Validate identifiers, timestamps, interval lengths, missing values, duplicates, and nonnegative usage. Keep a cleaning report. Do not silently clip legitimate bursts; document the meaning of each selected memory/CPU field and normalization using the trace schema documentation.
- [x] Sort each task's records by time and handle overlapping/duplicate intervals explicitly. Build current and historical CPU, memory, and I/O features, lag values, rolling mean/std/max, and burstiness using only observations available at prediction time. Carry task history across chunk/shard boundaries.
- [x] Set the prediction instant to the end of the current observed interval. Create next-interval CPU and memory targets only when the next interval is contiguous and valid; drop terminal rows and gaps. Record the actual prediction horizon. Never bridge missing shards or task restarts without validating continuity.
- [x] Split by global time into approximately 70% train, 15% validation, and 15% test. Purge examples whose target crosses a split boundary. Fit imputers/scalers only on training data; do not use raw job/task/machine IDs as numeric predictive features.
- [x] Use plots for CPU/memory distributions, sampled time series, missingness, correlations, and burstiness. Report eligible temporal pairs per split; if too few remain, adjust task sampling or expand within Module 1's budget, not by fabricating observations.
- [x] Save the feature definitions, split timestamps, selected feature list, and compact model-ready data. State that repeated tasks across time splits measure future behavior of observed workloads, not necessarily generalization to unseen jobs.

**Done when:** features cannot access their future targets, temporal pairs are valid, all splits have usable data, and the preprocessing statistics come only from training data.

**Prompt:** `Implement Module 2 from TODO.md in analysis.ipynb using the cached Module 1 Parquet and manifest. Check temporal continuity and prevent target leakage.`

## Module 3 — Workload clustering and resource-demand prediction

**Implementation status:** Complete. Refreshed Colab outputs show two workload clusters (silhouette 0.625), validation/test comparisons against persistence, and saved selected plus alternative forest predictions. Final data/artifact use: 565.4 MB.

- [x] Cluster standardized historical workload profiles with MiniBatchKMeans. Try a small range such as k=2–6, using sampled silhouette scores with at most 5,000 rows and sufficient cluster membership. Fit on training data, then assign validation/test profiles.
- [x] Use PCA to visualize clusters in two dimensions; fit PCA on training data. Interpret profiles from their resource statistics, allowing mixed groups. Do not force every run to produce CPU-heavy, memory-heavy, I/O-heavy, and bursty groups.
- [x] Predict next-interval CPU and memory separately with a persistence baseline (`next = current`), Ridge regression, and a bounded RandomForestRegressor. Use only a small validation search; keep test data untouched until model selection is complete.
- [x] Compare per-target MAE, RMSE, and R², plus runtime and predicted-vs-actual plots. Flag undefined R² for constant targets. Avoid MAPE on near-zero usage. Report negative R² or failure to beat persistence honestly.
- [x] Save selected preprocessing/model pipelines and validation predictions for Module 4. Any clipping of negative demand predictions must be consistent during evaluation and simulation.

**Done when:** clusters have interpretable profiles and the regression comparison includes a real forecasting baseline, validation-based selection, and a single final test evaluation.

**Prompt:** `Implement Module 3 from TODO.md in analysis.ipynb. Keep model training small enough for a laptop and report the persistence baseline.`

## Module 4 — Potential bottleneck classification

**Implementation status:** Complete. The Colab run used frozen training-only references (CPU 0.05072, memory 0.06677), all four classes had support, the decision tree reached test macro-F1 0.8752 versus 0.2279 for the majority baseline, and the classifier/predictions were saved.

- [x] Define a fixed simulated CPU/memory allocation from training-only statistics (for example, each resource's training 90th percentile with a positive floor). Freeze this reference for validation and test.
- [x] Define future risk labels by comparing next-interval observed CPU/memory demand against that allocation: `balanced`, `CPU risk`, `memory risk`, or `both`. These are **rule-derived proxy labels**, not native Google bottleneck annotations or verified failures.
- [x] Train a class-weighted LogisticRegression and a shallow DecisionTreeClassifier on historical features only. Do not include future demand, future demand/allocation ratios, or the generated label as input. Include a majority-class baseline.
- [x] Compare validation macro-F1 and per-class recall, then report test precision/recall/F1, confusion matrix, and class counts. ROC-AUC is optional only when valid probabilities and class support exist. Handle absent/rare classes explicitly; do not use random time mixing or synthetic labels to manufacture balanced classes.
- [x] Explain risky examples using historical profiles and connect them to predicted demand. Keep the reference-allocation labels fixed rather than redefining the ground truth separately for each policy.

**Done when:** labels, assumptions, class balance, and temporal separation are explicit; the notebook calls this potential allocation-risk prediction.

**Prompt:** `Implement Module 4 from TODO.md in analysis.ipynb with clearly documented proxy labels and no future-data leakage.`

## Module 5 — Allocation simulation, what-if analysis, and final results

**Implementation status:** Complete. A fresh Colab run executed all 25 analysis code cells in order without errors, regenerated the final metrics and plots, saved the results, and kept project data/artifacts at 565.8 MB.

- [x] Replay the same held-out task intervals for three policies: fixed allocation from training statistics, persistence-based demand allocation, and the separately saved random-forest forecast plus a safety margin. Module 3 selected persistence on MAE, so the forest remains an alternative policy candidate. Tune margins on validation data only, then freeze them.
- [x] Use the same simulated CPU and memory pool capacities, chosen from training data, for all policies. At each time step, enforce per-resource pool limits with a documented deterministic contention rule. Measure achieved allocations after that rule. Do not use future test demand when assigning resources.
- [x] For demand D and allocation A, report per-resource utilization `sum(min(D,A))/sum(A)`, unused allocation `sum(max(A-D,0))`, unmet demand `sum(max(D-A,0))`, and fraction of intervals with `D>A`. Handle zero denominators and use duration weighting where intervals differ. Report CPU and memory separately.
- [x] Compare policies at similar overload risk where possible and show the utilization/overload trade-off. Do not claim an improvement merely because one policy allocates less and leaves more demand unmet.
- [x] Run a small scenario set: original demand, +20% demand, +50% demand, and -20% pool capacity. Explain whether policies can observe the demand shift; use the same information for every policy. Do not retrain on test outcomes.
- [x] Add a final results table, policy/scenario plots, limitations, and conclusions tied to the synopsis. State that usage is observed consumption, not unconstrained demand, and that this simulation does not reproduce Borg scheduling, latency, SLA violations, or real cost savings.
- [x] Verify a restart-and-run-all using cached data, concise outputs, saved artifacts, reproducibility settings, and the total disk cap. Mark completed checkboxes only after the corresponding work is verified.

**Done when:** the notebook runs end to end and presents measured model results and fair simulated policy comparisons, including unsuccessful outcomes.

**Prompt:** `Implement Module 5 from TODO.md in analysis.ipynb, then validate the complete analysis notebook with cached data and summarize actual results and limitations.`

---

**Methodology changes from the synopsis:** prioritize a few justified models over trying every listed algorithm; make forecasting strictly temporal; explicitly simulate allocations instead of requiring large event-table joins; label bottleneck classification as a proxy task; and include persistence and fair-capacity baselines. Actual historical resource-request analysis would require correctly time-aligned task-event joins and is outside this compact core implementation.
