
****************************************************
* Listing packages to check and install if missing
****************************************************
// 1. List all the packages you want
local pkgs estout spmap shp2dta mif2dta egenmore binscatter ftools reghdfe ivreg2 ranktest ivreghdfe

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
global code_path "`c(pwd)'"


mata:
    // Get current code path from Stata global macro
    code_path = st_global("code_path")

    // Extract upper-level directories
    analysis_path = pathgetparent(code_path)
    parent_path = pathgetparent(analysis_path)

    // Save them back to Stata as global macros
    st_global("analysis_path", analysis_path)
    st_global("parent_path", parent_path)

    // Detect the path separator used in code_path
    pos_slash  = strpos(code_path, "/")
    pos_bslash = strpos(code_path, "\")

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
global build_path            "$parent_path${sep}build"
global data_path             "$build_path${sep}data"  
global raw_data_path         "$data_path${sep}raw"                
global temp_data_path        "$data_path${sep}temp"            
global output_data_path      "$data_path${sep}output"                 
global table_figure_path     "$analysis_path${sep}tables and figures"


****************************************************
* 📁 Display current configuration
****************************************************
display "--------------------------------------------"
display "📁 OS Detected:            `os'"
display "📁 Path Separator:         $sep"
display "--------------------------------------------"
display "📁 parent_path:            $parent_path"
display "--------------------------------------------"
display "📁 build:          "
display "	📁 data_path:              $data_path"
display "   	📁 raw_data_path:       $raw_data_path"
display "   	📁 temp_data_path:       $temp_data_path"
display "   	📁 output_data_path:     $output_data_path"
display "--------------------------------------------"
display "📁 analysis_path:          $analysis_path"
display "	📁 code_path:              $code_path"
display "	📁 table_figure_path:      $table_figure_path"
display "--------------------------------------------"

