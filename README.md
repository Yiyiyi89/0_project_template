# <center><font size=6>Empirical Research Template</font></center>
<p align=right> <font size=2>易翊翼<br>20241011</font></p>
___________________________________________________________________________________________________________________________

## <font size=5>Project Description</font>

This is an empirical research project template designed to provide a standardized project structure for:
1. Version control
2. Code synchronization between local machine and HPC
3. Decoupling of code and data
4. Unified code organization (data processing and analysis in one place)

The template structure follows the [Guide by Matthew Gentzkow and Jesse M. Shapiro](https://web.stanford.edu/~gentzkow/research/CodeAndData.pdf) and includes useful `config.do` and `config.py` files for setting up paths and packages in Stata and Python.

## <font size=5>Directory Structure</font>

```text
├── code                         # All code (data processing and analysis)
│   ├── config.py                # Python path configuration
│   ├── config.do                # Stata path configuration
│   ├── step1_import_and_clean.py   # Import raw data, clean, save to temp/
│   ├── step2_merge.py              # Merge datasets, save merge key to temp/
│   ├── step3_build_up_panel.py     # Build panel, save to output/
│   ├── step4_panels.do             # Load parquet panel, construct variables
│   ├── step5_tables.do             # Regression tables → tables_and_figures/
│   └── step5_figures.do            # Figures → tables_and_figures/
├── data                         # Data directory
│   ├── input                    # Raw input data (read-only) (1)
│   │    ↓
│   ├── temp                     # Intermediate files, merge keys (2)
│   │    ↓
│   ├── output                   # Analysis-ready panels (3)
│   │    ↓
│   └── tables_and_figures       # Tables and figures (4)
├── resource             # Related papers and materials
├── README.md            # Project documentation
└── README.py            # Directory tree generator
```

## <font size=5>Usage Guide</font>

### 1. Data Management
- `data/input`: Store raw input data (read-only)
- `data/temp`: Store temporary files, merge keys, and intermediate files
- `data/output`: Store analysis-ready panels
- `data/tables_and_figures`: Store generated tables and figures

### 2. Code Organization
- `code/`: Contains all code (data processing and analysis)
  - `config.py` / `config.do`: Path configuration (see §4 Configuration)
  - `step1_import_and_clean.py`: Import from `input/`, clean, save `temp/[data]_[level].parquet`
  - `step2_merge.py`: Merge datasets, save `temp/key_[data1]_[data2].parquet`
  - `step3_build_up_panel.py`: Build panel, save `temp/panel_[level].parquet`
  - `step4_panels.do`: Load parquet via `pq use`, construct variables, save `output/panel_[level].dta`
  - `step5_tables.do`: Regression tables → `tables_and_figures/table_[des].xls/.tex`
  - `step5_figures.do`: Figures → `tables_and_figures/figure_[des].png`

### 3. Version Control
- Use `.gitignore` for large data files
- Use `.gitkeep` to maintain empty directories
- Regular code commits

### 4. Configuration
- **Python**: Use `code/config.py` for path configuration
  - `CODE`, `PARENT`, `DATA`
  - `DATA_INPUT`, `DATA_TEMP`, `DATA_OUTPUT`, `DATA_RESULTS`
  - Import with: `from config import DATA_INPUT, DATA_TEMP` etc.
- **Stata**: Use `code/config.do` for path configuration
  - `$CODE`, `$PARENT`, `$DATA`
  - `$DATA_INPUT`, `$DATA_TEMP`, `$DATA_OUTPUT`, `$DATA_RESULTS`
  - Run with: `do "config.do"` (from within the `code/` directory)
  - Packages auto-installed on first run
- Both config files use the same variable names for consistency across languages

## <font size=5>Best Practices</font>

1. Data Security
   - Don't commit sensitive data
   - Use `.gitignore` for large files

2. Code Standards
   - Keep code clean and documented
   - Use meaningful names
   - Add appropriate comments

3. Performance
   - Use chunking for large datasets
   - Choose appropriate data structures

4. Collaboration
   - Regular code sync
   - Keep documentation updated
   - Follow project standards

## <font size=5>Maintenance</font>

- Regular dependency updates
- Documentation maintenance
- Temporary file cleanup
- Data backup
