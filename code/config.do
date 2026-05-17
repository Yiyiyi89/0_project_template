
****************************************************
* 📁  Current Packages Configuration
****************************************************
// List all the packages to be installed
local pkgs estout spmap shp2dta mif2dta egenmore binscatter ftools reghdfe ivreg2 ranktest ivreghdfe csdid eventstudyinteract bacondecomp coefplot outreg2 honestdid fect _gwtmean

qui {
// 2. Loop over each package, check with ssc describe, install if missing
foreach pkg of local pkgs {
    if "`pkg'" == "egenmore" {
        // use help to check if the package is installed
        capture help egenmore
        if _rc {
            display "📦 Installing egenmore..."
            ssc install egenmore, replace
        }
        else {
            display "✔ egenmore is already installed."
        }
    }
    else if "`pkg'" == "ivreghdfe" {
        // use help to check if the package is installed
        capture which `pkg'.ado
        if _rc {
            display "📦 Installing ivreghdfe..."
            net install ivreghdfe, from("https://raw.githubusercontent.com/sergiocorreia/ivreghdfe/master/src/") replace
        }
        else {
            display "✔ ivreghdfe is already installed."
        }
    }
    else if "`pkg'" == "fect" {
        capture which fect.ado
        if _rc {
            display "📦 Installing fect..."
            net install fect, from("https://raw.githubusercontent.com/xuyiqing/fect_stata/master/") replace
        }
        else {
            display "✔ fect is already installed."
        }
    }
    else {
        // use which to check if the package is installed
        capture which `pkg'.ado
        if _rc {
            display "📦 Installing `pkg'..."
            ssc install `pkg', replace
        }
        else {
            display "✔ `pkg' is already installed."
        }
    }
}
****************************************************
* set_paths.do - Cross-platform, portable path setup
****************************************************

* Save current working directory
global CODE "`c(pwd)'"


mata:
    // Get current code path from Stata global macro
    CODE = st_global("CODE")

    // Extract parent directory (one level up from code)
    PARENT = pathgetparent(CODE)

    // Save them back to Stata as global macros
    st_global("PARENT", PARENT)

    // Detect the path separator used in CODE
    pos_slash  = strpos(CODE, "/")
    pos_bslash = strpos(CODE, "\")

    if (pos_slash > 0 & (pos_bslash == 0 | pos_slash < pos_bslash)) {
        sep = "/"
    } else if (pos_bslash > 0) {
        sep = "\"
    } else {
        sep = "/"  // fallback to forward slash
    }

    // Save separator to global macro
    st_global("sep", sep)
end




****************************************************
* 📁 Main project folders
****************************************************

global DATA             "$PARENT${sep}data"
global DATA_RAW         "$DATA${sep}raw"
global DATA_TEMP        "$DATA${sep}temp"
global DATA_PROCESSED   "$DATA${sep}processed"

global OUTPUT           "$PARENT${sep}output"
global OUTPUT_TABLES    "$OUTPUT${sep}tables"
global OUTPUT_FIGURES   "$OUTPUT${sep}figures"
}

****************************************************
* 📁 Current Paths Configuration
****************************************************

qui {
noisily display "--------------------------------------------"
noisily display "📁 OS Detected:            `c(os)'"
noisily display "📁 Path Separator:         $sep"
noisily display "--------------------------------------------"
noisily display "📁 PARENT:            $PARENT"
noisily display "--------------------------------------------"
noisily display "📁 DATA:              $DATA"
noisily display "   	📁 DATA_RAW:          $DATA_RAW"
noisily display "   	📁 DATA_TEMP:         $DATA_TEMP"
noisily display "   	📁 DATA_PROCESSED:    $DATA_PROCESSED"
noisily display "--------------------------------------------"
noisily display "📁 OUTPUT:            $OUTPUT"
noisily display "   	📁 OUTPUT_TABLES:     $OUTPUT_TABLES"
noisily display "   	📁 OUTPUT_FIGURES:    $OUTPUT_FIGURES"
noisily display "--------------------------------------------"
}