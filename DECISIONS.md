# Project decisions

This root-level log preserves significant choices and their formal implementations. Historical locations in decision 0001 are shown using their current equivalents for navigation.

## 0001 - Separate experiments from formal research work

- Date: 2026-11-04
- Status: Implemented; documentation locations superseded by decision 0002
- Scope/authority: User requested folder review, CLI/Git setup guidance, and AI instructions with a separate trial area and recorded significant decisions.
- Supersedes: None

### Question and context
The template separated code and data but did not distinguish exploratory work from accepted implementations or preserve decision history. Git commands also fail on the current source checkout.

### Alternatives and decision
Keep the existing formal folder names to preserve configured paths. Add an ignored `trial/` directory and tracked `DECISIONS.md` records. Require accepted approaches to be implemented and validated in formal code. Use a fresh-project initializer that omits all Git metadata rather than modifying the source checkout's damaged metadata.

Using only chat history would lose durable reasoning; keeping every trial in formal code would blur which implementations are authoritative. A separate repository or container is optional when stronger isolation is required.

### Evidence and limitations
The README and code agree on the overall four-stage data flow after correcting step 3's documented destination. Example research scripts still require real schemas and data. The boundary is procedural: a folder and ignore rules cannot prevent arbitrary filesystem writes.

### Formal implementation
- `AGENTS.md`: folder ownership, decision triggers, promotion, and validation rules.
- `README.md` (trial guidance): experiment structure and explicit output paths.
- `DECISIONS.md` (entry template): durable decision format.
- `code/new-project.ps1` and `README.md` (setup): independent project creation.
- `.gitignore`, `README.md`, `README.py`, `requirements.txt`: supporting template updates.
- `README.md` (review): remaining research and environment limitations.

### Validation
On Windows with PowerShell and Git 2.51.1, ran `code/new-project.ps1 -Destination <temporary-empty-directory>` and checked the resulting repository with `git status --short`, `git check-ignore`, and `git diff --cached --check`. PASS: initialization and expected file selection; research data and trial scripts are ignored; requirements, AI instructions, the trial guide, and data placeholders are eligible for tracking; staged whitespace check is clean. PASS: re-running initialization against the populated destination fails without overwriting files. Checks used disposable repositories, with no commit or push.

Research pipeline execution and Graphviz rendering were not run: no input datasets were supplied and the `python` command in this environment resolves to an inaccessible Windows application alias. Stata execution was not tested.

### Consequences and follow-up
Each independent project must customize sample scripts and validate/pin its environment. Important experimental evidence must be preserved in tracked records before deleting local trials. Existing Git history is not recovered by the initializer.

## 0002 - Keep five top-level folders and root documentation

- Date: 2026-11-04
- Status: Implemented
- Authority: User explicitly requested only `.git`, `code`, `data`, `resources`, and `trial` folders, with Markdown guidance outside them.
- Supersedes: The documentation/utility locations in decision 0001; its trial and promotion rules remain in force.
- Decision: Consolidate setup, review, and trial guidance into root `README.md`; retain root `AGENTS.md`; combine decision history and template into root `DECISIONS.md`. Move the initializer to `code/new-project.ps1`, rename `resource/` to `resources/`, and preserve empty `trial/` with `.gitkeep`.
- Rationale: Reduce navigation and folder overhead while retaining durable decisions and AI guidance. Use `code/.venv/` for optional Python environments so setup does not add a sixth root folder.
- Formal implementation: `README.md`, `AGENTS.md`, `DECISIONS.md`, `code/new-project.ps1`, `.gitignore`, `resources/`, `trial/.gitkeep`.
- Validation: PASS on Windows/PowerShell with Git 2.51.1: `code/new-project.ps1 -Destination <temporary-empty-directory>` creates exactly the five requested folders; source layout also matches. Verified expected files, `git check-ignore` exclusions for data/trials/environments and inclusions for documentation/placeholders, `git diff --cached --check`, and refusal to overwrite a nonempty destination. Reviewed old path references; only the historical rename remains. Research scripts are unchanged and were not run.
- Consequences: Add future decisions as entries in this file; do not recreate separate docs or scripts folders. Trial-specific notes can stay with their experiments.

## 0003 - Separate prediction-market research from the template repository

- Date: 2026-11-04
- Status: Implemented
- Authority: User requested separation of the prediction-market project and the GitHub template after learning they shared a remote.
- Context: `20260324_predic_market` tracked `Yiyiyi89/0_project_template`, whose main branch contained research code at `4c73d8975b48259e2b048570debba92b125fc752`. The local template had incomplete Git metadata.
- Decision: Create private `Yiyiyi89/20260324_predic_market`, transfer all five committed branches, and point the research folder and its worktrees to that repository. Restore the simplified template as a normal new commit on `Yiyiyi89/0_project_template/main`. Preserve existing commit history rather than force-pushing it away.
- Evidence: Remote branch hashes matched the five local research branches. Before/after binary-diff hashes and status snapshots matched for all five research worktrees. Existing uncommitted edits remain local and were not automatically committed. The private research repository does not remove research from the template repository's historical public commits.
- Formal implementation: Root template documentation and `code/new-project.ps1`; separate Git remotes and branch tracking; repaired template Git metadata. The initializer creates fresh independent repositories, preventing future projects from inheriting the template remote.
- Validation: Verified branch transfer, worktree remotes, and unchanged research working edits. Template publication uses a reviewed normal commit; final remote commit and clean local status are checked after pushing. Research execution is outside this repository-separation task.
- Recovery: Original research Git configuration, all committed refs in a Git bundle, worktree patches/status snapshots, and the template's previous metadata are retained in a local temporary backup directory recorded in the task. Keep durable backups of uncommitted work and source data separately.

## Entry template

Append an entry using the next unused number:

```markdown
## NNNN - Short decision title

- Date: YYYY-MM-DD
- Status: Proposed / Accepted (implementation pending) / Implemented / Rejected / Superseded
- Authority: User instruction or delegated task
- Supersedes: None, or earlier decision number
- Context: Question, constraints, and data involved
- Alternatives and decision: What was considered, chosen, and why
- Evidence and limitations: Trial path, findings, input versions, uncertainty; preserve enough detail to understand the choice without the ignored trial
- Formal implementation: Relative code/document paths and affected outputs; explain if no code is appropriate
- Validation: Exact commands, environment, and passed/failed/not-run outcomes
- Consequences: Tradeoffs, follow-up work, and conditions for revisiting
```
