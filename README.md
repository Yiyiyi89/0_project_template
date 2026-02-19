# <center><font size=6>Empirical Research Template</font></center>
<p align=right> <font size=2>易翊翼<br>20241011</font></p>
___________________________________________________________________________________________________________________________

## <font size=5>Project Description</font>

This is an empirical research project template designed to provide a standardized project structure for:
1. Version control
2. Code synchronization between local machine and HPC
3. Decoupling of code and data
4. Separation of build and analysis phases

The template structure follows the [Guide by Matthew Gentzkow and Jesse M. Shapiro](https://web.stanford.edu/~gentzkow/research/CodeAndData.pdf) and includes useful `config.do` and `config.py` files for setting up paths and packages in Stata and Python.

## <font size=5>Directory Structure</font>

```text
├── build                # Data construction phase
│   ├── code             # Data processing code
│   └── data          
│       ├── raw          # Raw data (1) 
|       |    ↓         
│       ├── temp         # Temporary files, merge keys, etc. (2) 
|       |    ↓        
│       └── processed→|  # Processed databases (3) 
├── analysis          |  # Analysis phase
│   ├── code          |  # Analysis code
│   └── data          | 
│       ├── input←←←←←| # Panel data for descriptive stats and regressions(4) 
|       |    ↓        
│       └── output      # Generated tables and figures (5)
├── README.md           # Project documentation
├── README.py           # Directory tree generator
└── resource            # Related papers and materials


```
## <font size=5>Usage Guide</font>

### 1. Data Management
- `build/data/raw`: Store raw data (read-only)
- `build/data/processed`: Store processed data
- `build/data/temp`: Store intermediate files
- `analysis/data/input`: Store analysis-ready data
- `analysis/data/output`: Store analysis results

### 2. Code Organization
- `build/code`: Data cleaning and construction code
- `analysis/code`: Analysis code
- Each code file should have clear documentation

### 3. Version Control
- Use `.gitignore` for large data files
- Use `.gitkeep` to maintain empty directories
- Regular code commits

### 4. Configuration
- Use `config.py` for Python paths and packages
- Use `config.do` for Stata paths and packages

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
