from pathlib import Path

# ————————————————————————————— #
#     Core Paths
# ————————————————————————————— #
CODE = Path(__file__).parent
PARENT = CODE.parent

# ————————————————————————————— #
#     Data Area
# ————————————————————————————— #
DATA = PARENT / "data"
DATA_RAW       = DATA / "raw"
DATA_TEMP      = DATA / "temp"
DATA_PROCESSED = DATA / "processed"

# ————————————————————————————— #
#     Output Area
# ————————————————————————————— #
OUTPUT         = PARENT / "output"
OUTPUT_TABLES  = OUTPUT / "tables"
OUTPUT_FIGURES = OUTPUT / "figures"


# ————————————————————————————— #
#     Debug / Display
# ————————————————————————————— #
if __name__ == "__main__":
    print("|" + "-" * 78)
    print("|PARENT:               ", PARENT)
    print("|CODE:                 ", CODE)
    print("|" + "-" * 78)

    print("|DATA:                 ", DATA)
    print("|  DATA_RAW:           ", DATA_RAW)
    print("|  DATA_TEMP:          ", DATA_TEMP)
    print("|  DATA_PROCESSED:     ", DATA_PROCESSED)
    print("|" + "-" * 78)

    print("|OUTPUT:               ", OUTPUT)
    print("|  OUTPUT_TABLES:      ", OUTPUT_TABLES)
    print("|  OUTPUT_FIGURES:     ", OUTPUT_FIGURES)
    print("|" + "-" * 78)
