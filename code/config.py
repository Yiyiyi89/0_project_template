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
DATA_INPUT = DATA / "input"
DATA_TEMP = DATA / "temp"
DATA_OUTPUT = DATA / "output"
DATA_RESULTS = DATA / "tables_and_figures"


# ————————————————————————————— #
#     Debug / Display
# ————————————————————————————— #
if __name__ == "__main__":
    print("|" + "-" * 78)
    print("|PARENT:           ", PARENT)
    print("|CODE:             ", CODE)
    print("|" + "-" * 78)

    print("|DATA:             ", DATA)
    print("|  DATA_INPUT:     ", DATA_INPUT)
    print("|  DATA_TEMP:      ", DATA_TEMP)
    print("|  DATA_OUTPUT:    ", DATA_OUTPUT)
    print("|  DATA_RESULTS:   ", DATA_RESULTS)
    print("|" + "-" * 78)
