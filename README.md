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
├── code                 # All code (data processing and analysis)
│   ├── config.py        # Python path configuration
│   ├── config.do        # Stata path configuration
│   ├── toolkit.py       # Utility functions
│   ├── data_merge_template.py  # Data merging template
│   └── variables_record.py     # Variable documentation
├── data                 # Data directory
│   ├── raw              # Raw data (read-only) (1)
│   │    ↓
│   ├── temp             # Temporary files, merge keys, etc. (2)
│   │    ↓
│   └── clean            # Cleaned/processed data (3)
│        ↓
├── output               # Analysis outputs
│   ├── figure           # Generated figures (4)
│   └── table            # Generated tables (5)
├── resource             # Related papers and materials
├── README.md            # Project documentation
└── README.py            # Directory tree generator
```

## <font size=5>Usage Guide</font>

### 1. Data Management
- `data/raw`: Store raw data (read-only)
- `data/temp`: Store temporary files, merge keys, and intermediate files
- `data/clean`: Store cleaned and processed data
- `output/figure`: Store generated figures
- `output/table`: Store generated tables

### 2. Code Organization
- `code/`: Contains all code (data processing and analysis)
  - `config.py`: Python path configuration (defines CODE, PARENT, DATA, OUTPUT paths)
  - `config.do`: Stata path configuration (defines $CODE, $PARENT, $DATA, $OUTPUT globals)
  - `toolkit.py`: Utility functions for data processing
  - `data_merge_template.py`: Template for data merging operations
  - `variables_record.py`: Variable documentation and metadata
- Each code file should have clear documentation

### 3. Version Control
- Use `.gitignore` for large data files
- Use `.gitkeep` to maintain empty directories
- Regular code commits

### 4. Configuration
- **Python**: Use `code/config.py` for path configuration
  - Variables: `CODE`, `PARENT`, `DATA`, `DATA_RAW`, `DATA_CLEAN`, `DATA_TEMP`, `OUTPUT`, `OUTPUT_FIGURE`, `OUTPUT_TABLE`
  - Import with: `from config import *` or `import config`
- **Stata**: Use `code/config.do` for path configuration
  - Globals: `$CODE`, `$PARENT`, `$DATA`, `$DATA_RAW`, `$DATA_CLEAN`, `$DATA_TEMP`, `$OUTPUT`, `$OUTPUT_FIGURE`, `$OUTPUT_TABLE`
  - Run with: `do code/config.do`
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
