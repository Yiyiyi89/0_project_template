# Empirical Research Template

Original template: 易翊翼, 2024-10-11. Simplified layout: 2026-11-04.

A template for version-controlled empirical research, local/HPC code synchronization, and separation of code from data. Inspired by the [Gentzkow–Shapiro guide](https://web.stanford.edu/~gentzkow/research/CodeAndData.pdf).

## Folder structure

Keep exactly these five top-level folders. Keep shared Markdown documentation at the project root.

```text
project/
├── .git/                    # Git metadata; managed by Git
├── code/                    # Formal analysis, configuration, and utilities
│   ├── config.py / config.do
│   ├── step1_import_and_clean.py
│   ├── step2_merge.py
│   ├── step3_build_up_panel.py
│   ├── step4_panels.do
│   ├── step5_tables.do / step5_figures.do
│   └── new-project.ps1      # Initialize a new independent project
├── data/
│   ├── input/              # Original data; read-only
│   ├── temp/               # Rebuildable intermediates and merge keys
│   ├── output/             # Analysis-ready panels
│   └── tables_and_figures/ # Formal generated results
├── resources/              # Reference papers and supporting materials
├── trial/                  # Local experiments and their outputs
├── README.md               # Structure, setup, usage, and review
├── AGENTS.md               # AI instructions and promotion rules
├── DECISIONS.md            # Decision history and reusable entry template
├── README.py               # Optional directory/data-flow diagram utility
├── requirements.txt        # Starter Python dependencies
└── .gitignore
```

## Research workflow

| Stage | Script | Input → output |
| --- | --- | --- |
| Import and clean | `code/step1_import_and_clean.py` | `data/input/` → `data/temp/[data]_[level].parquet` |
| Merge | `code/step2_merge.py` | Intermediates → `data/temp/key_[data1]_[data2].parquet` |
| Build panel | `code/step3_build_up_panel.py` | Intermediates and keys → `data/temp/panel_[level].parquet` |
| Construct variables | `code/step4_panels.do` | Temporary panel → `data/output/panel_[level].dta` |
| Tables and figures | `code/step5_tables.do`, `code/step5_figures.do` | Analysis-ready panel → `data/tables_and_figures/` |

Python scripts import paths from `code/config.py`: `CODE`, `PARENT`, `DATA`, `DATA_INPUT`, `DATA_TEMP`, `DATA_OUTPUT`, and `DATA_RESULTS`. Stata uses the same names as globals; run `do "config.do"` from within `code/`. Its current configuration may install missing packages.

**The scripts are scaffolds, not a ready-to-run pipeline.** Supply data and adapt filenames, columns, and research assumptions first. Preserve raw inputs, keep generated data out of Git, and use `.gitkeep` for empty directories.

## Trials and significant decisions

Read [AGENTS.md](AGENTS.md) before AI-assisted work. Create `trial/<YYYY-MM-DD-topic>/` with an experiment script, `NOTES.md`, and `outputs/`. Trial notes are local working notes; shared guidance and durable decisions stay at the root.

Write every experimental output to that trial's `outputs/`, never to formal data destinations. For Python, derive it from `Path(__file__).resolve().parent / "outputs"`; for Stata, explicitly set a trial output path and use it for every save/export. Changing the working directory alone does not redirect configured output paths.

Record significant choices in [DECISIONS.md](DECISIONS.md). Promote accepted code into `code/`, validate it, and regenerate formal outputs from formal code. Formal work must never depend on `trial/`. Trial contents are ignored by Git, so preserve important findings and reproduction details in the decision log before cleanup. This convention does not enforce filesystem isolation; use a container or account restrictions for untrusted scripts.

## Setup with CLI and Git

Here, setup means copying the research template and creating a Git repository. It does not deploy a service or supply research data.

### A. From this local folder (recommended for the current copy)

Use the initializer to create an independent project with fresh Git history. In PowerShell, replace the destination with your new project's absolute path:

```powershell
& 'D:\Dropbox\projects\0_project_template\code\new-project.ps1' -Destination 'D:\Dropbox\projects\my-new-study'
Set-Location 'D:\Dropbox\projects\my-new-study'
git status --short
git add .
git diff --cached --stat
git diff --cached
git commit -m "Initialize research project from template"
```

The destination must not exist or must be empty, including hidden files. The script copies template code, instructions, and maintenance scripts, creates empty data/resources/trial folders, and runs `git init -b main`. It does not copy existing data, reference papers, experiments, or any `.git` metadata. It makes no commit or network request. If PowerShell blocks scripts, use your organization's approved script-execution process.

If Git asks for your identity, set it for this repository using your actual name and email, then retry the commit:

```powershell
git config user.name "Your Name"
git config user.email "you@example.com"
```

### B. From a healthy Git repository

To continue an existing project with its history, use an actual repository URL and an empty destination:

```powershell
git clone https://github.com/YOUR-ACCOUNT/YOUR-REPOSITORY.git 'D:\Dropbox\projects\my-study'
Set-Location 'D:\Dropbox\projects\my-study'
```

If you are already inside an empty folder, `git clone <repository-url> .` uses that folder. Cloning retains history and sets `origin` to the source repository. To create an independent project from a healthy template, clone the template to a separate staging folder, then run its `code/new-project.ps1` with your final empty destination; the initializer gives the project fresh history.

### C. Publish an independent project

Create an empty remote repository first, with no generated README, license, or ignore file. In your initialized project, replace the example URL and run:

```powershell
git remote add origin https://github.com/YOUR-ACCOUNT/YOUR-NEW-STUDY.git
git remote -v
git push -u origin main
```

This publishes committed files; authenticate to your Git host when prompted. If `origin` already exists, inspect it before deliberately changing it with `git remote set-url origin <new-url>`. Do not push a new study into the template's repository accidentally.

### D. Prepare the research environment

Install Python if needed, and make sure `python --version` works. From the project root:

```powershell
python -m venv code/.venv
.\code\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\code\.venv\Scripts\python.exe code/config.py
```

The manifest is a starter list, not a tested lock. Record and pin the versions validated for your study. The optional `README.py` diagram utility also requires the Graphviz system executable `dot` on PATH.

For Stata, open Stata, change to the project's `code/` directory, and run `do "config.do"`. Its current configuration may download missing packages; Stata must be installed separately. Adapt and validate the step scripts before running them: their filenames, data, and column names are examples. There is no complete runnable dataset in the template.

Supply raw data separately to `data/input/`. Git synchronizes code and documentation, not ignored data, trial files, or environments. Transfer authorized datasets separately to an HPC machine and recreate the software environment there.

### E. Daily AI workflow

Have the AI read `AGENTS.md` first. Explore in `trial/<date-topic>/`; record significant choices in `DECISIONS.md`; implement accepted work in `code/`; validate it and regenerate formal outputs. Review the code and decision record together before committing. The trial boundary is a workflow convention; use filesystem/container restrictions when hard isolation is needed.

Official references: [git init](https://git-scm.com/docs/git-init), [git clone](https://git-scm.com/docs/git-clone), and [gitignore](https://git-scm.com/docs/gitignore).

## Review and remaining improvements

The five-folder structure is sufficient for a small empirical project. The template now includes an initializer, AI rules, a trial workspace, and a decision log; the documented step 3 destination and diagram input paths have been corrected.

- **Separate repositories:** this template uses `Yiyiyi89/0_project_template`; the prediction-market project uses its own private `Yiyiyi89/20260324_predic_market` repository. New projects should have their own remotes. The initializer creates fresh Git history; cloning keeps the source history and remote until you deliberately change it.
- **Example inputs:** step 1 produces `revelio_firm_year.parquet`; step 2 also expects `aa_state_year.parquet`. Replace placeholder columns such as `id`, `key_col`, `firm_id`, and `year`.
- **Research validity:** specify and validate merge cardinality, unmatched counts, missingness, and entity-year uniqueness. Step 3's full entity-year grid is a substantive balanced-panel choice and can use substantial memory.
- **Environment:** validate and pin Python/package versions and record Stata/package revisions. Consider separating Stata package installation from path configuration. Optional commented examples may need additional packages.
- **Reproducibility:** add a project-specific pipeline and meaningful data checks once schemas are known. Record source, acquisition date, access restrictions, checksum/version, unit of observation, and keys in this README when data are selected.
- **Git exclusions:** data and trials are excluded by folder. Legacy extension-wide exclusions also hide JSON, TXT, PDF, and images elsewhere; explicitly allow legitimate configuration/documentation files when needed. Ignore rules do not untrack already committed files.

No real research data were supplied. Research execution and Graphviz rendering have not been validated in this environment. Keep documentation current, back up source data, and review staged files before committing.
