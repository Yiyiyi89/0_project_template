import os
import pandas as pd
import yaml
from concurrent.futures import ThreadPoolExecutor, as_completed
from ydata_profiling import ProfileReport
from tqdm import tqdm  # For progress bar

# Set up paths
code_path = os.getcwd()
parent_path = os.path.dirname(code_path)
temp_data_path = os.path.join(parent_path, "data", "temp")
raw_data_path = os.path.join(parent_path, "data", "raw")
output_data_path = os.path.join(parent_path, "data", "output")
lob_folder = os.path.join(raw_data_path, 'lob_level_variables')

data_folder = temp_data_path  # Data folder
output_yaml = os.path.join(data_folder, 'variable_records.yaml')  # Output file for recording column names


# Create ydata profiling report for each CSV file in the temp data folder
for file_name in os.listdir(temp_data_path):
    # Check if the file is a CSV file
    if file_name.endswith(".csv.gz"):
        try:
            # Load the CSV data
            file_path = os.path.join(temp_data_path, file_name)
            firm_year_panel = pd.read_csv(file_path)

            # Create a ydata profiling report
            profile = ProfileReport(
                firm_year_panel,
                title=f"summary report for {file_name}",
                # explorative=False
                # When set to False, the generated report will be simplified and focus on 
                # basic descriptive statistics and visualizations. Advanced features like 
                # detailed correlation analysis, interaction effects, missing value heatmaps, 
                # and in-depth variable warnings are disabled.
                # This option is useful for faster report generation, especially for large datasets, 
                # or when only a high-level overview of the data is needed.
                explorative=False,
                minimal=True,
                vars={"num": {"histogram_bins": 30}},  # Customize the number of histogram bins
            )

            # Save the report as an HTML file
            html_file_name = file_name.replace(".csv.gz", ".html")
            html_output_path = os.path.join(output_data_path, html_file_name)
            profile.to_file(html_output_path)

            print(f"HTML report generated: {html_output_path}")
        except Exception as e:
            print(f"Error processing file {file_name}: {e}")


def get_file_columns(file_path):
    """
    Extract column names from a given file.
    
    Args:
        file_path (str): Path to the file.

    Returns:
        list: List of column names, or an empty list if the file cannot be read.
    """
    ext = os.path.splitext(file_path)[-1].lower()  # Get file extension
    try:
        if ext == ".csv":
            # Read CSV header
            df = pd.read_csv(file_path, nrows=0)
        elif ext == ".csv.gz":
            # Read gzipped CSV header
            df = pd.read_csv(file_path, nrows=0, compression='gzip')
        elif ext in [".xls", ".xlsx"]:
            # Read Excel header
            df = pd.read_excel(file_path, nrows=0)
        elif ext == ".dta":
            # Read Stata header
            df = pd.read_stata(file_path, iterator=True).read(1)
        elif ext == ".parquet":
            # Read Parquet schema
            df = pd.read_parquet(file_path, engine='pyarrow', nrows=0)
            return list(df.columns)
        else:
            print(f"Unsupported file type: {file_path}")
            return []
        return list(df.columns)
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return []


def update_column_record(folder, record_file):
    """
    Update column records by scanning the folder and extracting column names from each data file.
    
    Args:
        folder (str): Path to the folder containing data files.
        record_file (str): Path to the YAML file for saving column records.
    """
    if not os.path.exists(folder) or not os.path.isdir(folder):
        print(f"Folder does not exist: {folder}")
        return

    column_record = {}
    files = [os.path.join(folder, f) for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))]

    # Process files with a progress bar
    with ThreadPoolExecutor() as executor:
        futures = {executor.submit(get_file_columns, file_path): file_path for file_path in files}
        for future in tqdm(as_completed(futures), total=len(futures), desc="Processing Files"):
            file_path = futures[future]
            file_name = os.path.basename(file_path)  # Extract file name
            try:
                columns = future.result()
                if columns:
                    column_record[file_name] = columns
            except Exception as e:
                print(f"Error processing file {file_name}: {e}")

    # Save column records to a YAML file
    with open(record_file, "w", encoding='utf-8') as f:
        yaml.dump(column_record, f, allow_unicode=True)

    print(f"Column records have been updated: {record_file}")

# Call the function
update_column_record(data_folder, output_yaml)





