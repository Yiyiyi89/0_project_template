# AI working instructions

Read `README.md` and the relevant entries in `DECISIONS.md` before working. Keep only `.git/`, `code/`, `data/`, `resources/`, and `trial/` as top-level folders; shared Markdown documents belong at the root. These instructions apply throughout this project.

## Where content belongs

| Location | Purpose |
| --- | --- |
| `code/` | Formal, reusable Python and Stata processing and analysis code; shared path configuration and project setup/maintenance utilities. |
| `data/input/` | Original source data. Treat as read-only; never overwrite, clean in place, or commit. |
| `data/temp/` | Rebuildable intermediate datasets and merge keys from formal code. |
| `data/output/` | Analysis-ready datasets produced by formal code. |
| `data/tables_and_figures/` | Final generated tables and figures from formal code. |
| `resources/` | Reference materials; record bibliographic/source information in Markdown. |
| `trial/<YYYY-MM-DD-topic>/` | Exploratory code, notes, logs, and outputs for one experiment. |
| `DECISIONS.md` | Durable records of significant choices, including rejected approaches, and the entry template. |
| `README.md` | Setup instructions, methods, data provenance, and project documentation. |

## Experiment first when the approach is uncertain

1. Create a uniquely named trial directory and an `outputs/` subdirectory. Add local `NOTES.md` with the question, date, input paths, commands, environment, and outcome.
2. Keep exploratory scripts and all their outputs within that trial directory. Read source data without modifying it. Use synthetic or small permitted samples where practical.
3. Do not run an unchanged formal script as an experiment: it may write into formal data directories. Explicitly redirect every output first. Do not use the formal `DATA_TEMP`, `DATA_OUTPUT`, or `DATA_RESULTS` destinations in trial code.
4. Formal code must never import trial code or depend on files under `trial/`. Working-directory changes alone do not redirect absolute/configured paths.
5. Keep useful failed approaches in the notes. Do not choose samples or specifications merely because they produce preferred results.

## Record decisions and promote accepted work

A significant decision changes a data source, sample restriction, merge key/cardinality, missing-value treatment, variable definition, panel construction, estimator, specification, dependency, directory convention, or interpretation. Cosmetic edits do not need a record.

1. Append an entry to `DECISIONS.md` using its entry template and the next unused number. Record the decision when it is made, including alternatives, rationale, evidence, and limitations. A decision that requires user input stays Proposed; do not invent approval.
2. When an approach is accepted within the authorized task, implement its reusable code in `code/` (including maintenance utilities). Refactor the useful parts; do not copy trial outputs into formal results as a substitute for a reproducible pipeline.
3. Record the formal file paths and exact validation commands/outcomes. For data changes, check relevant key uniqueness, merge cardinality, unmatched counts, missingness, and row counts. Record the actual environment and input versions/checksums where possible.
4. Regenerate affected formal outputs using formal code when inputs and required software are available. Otherwise mark validation pending and state what is missing. Never claim that unrun code passed.
5. Mark the record Implemented only after the code and appropriate validation exist. For documentation-only decisions, identify the documents as the implementation. If rejected, preserve the reasoning without promoting code. Supersede old decisions with a new linked record rather than erasing history.
6. Keep the decision record, formal code, and documentation in the same change/commit when commits are requested. Significant accepted work is incomplete if it exists only in `trial/` or chat.

Before reporting completion, check: decision recorded when needed; formal implementation present; validation results recorded honestly; no formal dependency on trial files; raw data untouched; generated data and private material excluded from the staged changes. Do not automatically commit, push, or delete trial folders.

## Practical limits

`trial/` is an organizational boundary, not an operating-system security boundary. Git ignore rules prevent accidental staging of untracked files; they do not stop programs from writing elsewhere. For untrusted scripts or strong isolation, use a container or separate account with read-only inputs and only its trial directory writable. Keep decisions and reproducible accepted code in version control before cleaning up trials.
