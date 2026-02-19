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
DATA_RAW = DATA / "raw"
DATA_CLEAN = DATA / "clean"
DATA_TEMP = DATA / "temp"

# ————————————————————————————— #
#     Output Area
# ————————————————————————————— #
OUTPUT = PARENT / "output"
OUTPUT_FIGURE = OUTPUT / "figure"
OUTPUT_TABLE = OUTPUT / "table"


# ————————————————————————————— #
#     Debug / Display
# ————————————————————————————— #
if __name__ == "__main__":
    print("|" + "-" * 78)
    print("|PARENT:           ", PARENT)
    print("|CODE:             ", CODE)
    print("|" + "-" * 78)

    print("|DATA:             ", DATA)
    print("|  DATA_RAW:       ", DATA_RAW)
    print("|  DATA_TEMP:      ", DATA_TEMP)
    print("|  DATA_CLEAN:     ", DATA_CLEAN)
    print("|" + "-" * 78)

    print("|OUTPUT:                   ", OUTPUT)
    print("|  OUTPUT_FIGURE:          ", OUTPUT_FIGURE)
    print("|  OUTPUT_TABLE:           ", OUTPUT_TABLE)
    print("|" + "-" * 78)
