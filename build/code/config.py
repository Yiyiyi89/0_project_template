from pathlib import Path

# ————————————————————————————— #
#     Core Paths
# ————————————————————————————— #
BUILD_CODE = Path.cwd()
PARENT_PATH = BUILD_CODE.parent.parent

# ————————————————————————————— #
#     Build Area
# ————————————————————————————— #
BUILD_ROOT = PARENT_PATH / "build"
BUILD_CODE = BUILD_ROOT / "code"
BUILD_DATA = BUILD_ROOT / "data"

DATA_RAW = BUILD_DATA / "raw"
# AA_DATA_PATH = DATA_RAW / "Audit Analytics"
DATA_TEMP = BUILD_DATA / "temp"
DATA_PROCESSED = BUILD_DATA / "processed"

# ————————————————————————————— #
#     Analysis Area
# ————————————————————————————— #
ANALYSIS_ROOT = PARENT_PATH / "analysis"
ANALYSIS_CODE = ANALYSIS_ROOT / "code"
ANALYSIS_DATA = ANALYSIS_ROOT / "data"

ANALYSIS_INPUT = ANALYSIS_DATA / "input"
ANALYSIS_OUTPUT = ANALYSIS_DATA / "output"


# ————————————————————————————— #
#     Debug / Display
# ————————————————————————————— #
if __name__ == "__main__":
    print("|" + "-" * 78)
    print("|BUILD_CODE:               ", BUILD_CODE)
    print("|PARENT_PATH:             ", PARENT_PATH)
    print("|" + "-" * 78)

    print("|BUILD_ROOT:              ", BUILD_ROOT)
    print("|  BUILD_CODE:            ", BUILD_CODE)
    print("|  BUILD_DATA:            ", BUILD_DATA)
    print("|    RAW:                 ", DATA_RAW)
    print("|    TEMP:                ", DATA_TEMP)
    print("|    PROCESSED:           ", DATA_PROCESSED)
    print("|" + "-" * 78)

    print("|ANALYSIS_ROOT:           ", ANALYSIS_ROOT)
    print("|  ANALYSIS_CODE:         ", ANALYSIS_CODE)
    print("|  ANALYSIS_DATA:         ", ANALYSIS_DATA)
    print("|    INPUT:               ", ANALYSIS_INPUT)
    print("|    Only for data that can be used for generating tables and figures.")
    print("|    OUTPUT:              ", ANALYSIS_OUTPUT)
    print("|    Only for tables and figures.")
    print("|" + "-" * 78)
