import os
import re
import numpy as np
import pandas as pd
from pandas.api.types import is_numeric_dtype
from scipy.stats import skew, kurtosis
from recordlinkage.preprocessing import clean
from joblib import Parallel, delayed
from tqdm.auto import tqdm
from tqdm_joblib import tqdm_joblib
from sklearn.feature_extraction.text import CountVectorizer


def clean_column(
    series,
    keywords_list=None,
    keywords_dict=None,
    parallel=False,
    n_jobs=-1,
    chunk_size=1000,
):
    """
    Cleans a pandas Series with custom replacements and text preprocessing.
    Supports both sequential and parallel processing.

    Args:
        series (pd.Series): The Series to clean.
        keywords_list (list, optional): List of keywords to replace with a single space. Default is None.
        keywords_dict (dict, optional): Dictionary of keywords to replace with specific strings. Default is None.
        parallel (bool, optional): Whether to use parallel processing. Default is False.
        n_jobs (int, optional): Number of parallel jobs. Default is -1 (use all available CPUs).
        chunk_size (int, optional): Number of rows per chunk for parallel processing. Default is 100000.

    Returns:
        pd.Series: Cleaned Series with preserved index.
    """

    def process_chunk(chunk):
        # Step 1: Basic cleaning
        chunk = clean(
            chunk,
            lowercase=True,
            replace_by_none="[^ \\-\\_A-Za-z0-9]+",  # Remove non-alphanumeric characters
            replace_by_whitespace="[\\-\\_]",  # Replace "-" and "_" with spaces
            strip_accents=None,
            # encoding='utf-8',
            remove_brackets=True,
        )

        # Step 2: Replace keywords from keywords_list
        if keywords_list:
            combined_keywords = rf"\b({'|'.join(map(re.escape, keywords_list))})\b"
            chunk = chunk.str.replace(combined_keywords, " ", regex=True)

        # Step 3: Replace keywords from keywords_dict
        if keywords_dict:
            for key, value in keywords_dict.items():
                chunk = chunk.str.replace(
                    rf"\b{re.escape(key)}\b", f"{value}", regex=True
                )

        # Step 4: Reduce multiple spaces to a single space
        chunk = chunk.str.replace(r"\s+", " ", regex=True).str.strip()

        return chunk

    if parallel:
        # Split the data into chunks
        num_chunks = max(1, (len(series) + chunk_size - 1) // chunk_size)
        chunks = [
            series.iloc[i * chunk_size : (i + 1) * chunk_size]
            for i in range(num_chunks)
        ]

        # Parallel processing
        with tqdm_joblib(
            tqdm(desc="Processing chunks", total=len(chunks))
        ) as progress_bar:
            processed_chunks = Parallel(n_jobs=n_jobs)(
                delayed(process_chunk)(chunk) for chunk in chunks
            )

        # Concatenate results and preserve the original index
        return pd.concat(processed_chunks).reindex(series.index)
    else:
        # Sequential processing
        return process_chunk(series)


def winsorize(df, lower_percentile=1, upper_percentile=99):
    """
    Detect continuous numeric columns with extreme outliers or heavy tails, apply winsorization,
    and return the names of these columns.

    Args:
        df (pd.DataFrame): Input DataFrame.
        lower_percentile (int): Lower bound for winsorization (default: 1).
        upper_percentile (int): Upper bound for winsorization (default: 99).

    Returns:
        list: Names of columns where winsorization was applied.
    """
    affected_columns = []

    # Iterate over numeric columns excluding binary or categorical variables
    for col in df.columns:
        if not is_numeric_dtype(df[col]) or isinstance(
            df[col].dtype, pd.CategoricalDtype
        ):  # Skip non-numeric or cardinality categorical variables
            continue

        # Compute skewness and kurtosis
        col_skewness = skew(df[col].dropna())
        col_kurtosis = kurtosis(df[col].dropna(), fisher=False)

        # Define thresholds for detecting extreme outliers or heavy tails
        if abs(col_skewness) > 2 or col_kurtosis > 9:  # Customize thresholds if needed
            affected_columns.append(col)

            # Winsorize the column
            lower_bound = np.percentile(df[col], lower_percentile)
            upper_bound = np.percentile(df[col], upper_percentile)
            df[col] = np.clip(df[col], lower_bound, upper_bound)

    return affected_columns


def log_transform(df, y, threshold=10):
    """
    Detect continuous numeric columns with significant magnitude difference compared to variable y,
    or identify positive continuous variables with heavy tails, and apply log transformation to those columns.
    Create new columns with "ln_" prefix.

    Args:
        df (pd.DataFrame): Input DataFrame.
        y (str): Target variable name.
        threshold (float): Threshold for magnitude difference (default: 10).

    Returns:
        list: Names of columns where log transformation was applied.
    """
    log_transformed_columns = []

    # Ensure y exists in the DataFrame
    if y not in df.columns:
        raise ValueError(f"The target variable '{y}' is not in the DataFrame.")

    y_magnitude = df[y].abs().mean()

    for col in df.columns:
        if not is_numeric_dtype(df[col]) or isinstance(
            df[col].dtype, pd.CategoricalDtype
        ):  # Skip non-numeric or low-cardinality variables
            continue

        col_magnitude = df[col].abs().mean()
        col_skewness = skew(df[col].dropna())
        col_kurtosis = kurtosis(df[col].dropna(), fisher=False)

        # Check if column is positive and meets criteria for log transformation
        if (df[col] > 0).all() and (
            (col_magnitude / y_magnitude > threshold)
            or (abs(col_skewness) > 2 or col_kurtosis > 9)
        ):
            log_transformed_columns.append(col)
            df[f"ln_{col}"] = np.log(
                df[col]
            )  # Apply log(x) assuming strictly positive values

    return log_transformed_columns


# """Example usage"""
## random data
# np.random.seed(42)  # For reproducibility
# data = {
#     "user": [f"user_{i}" for i in range(1, 101)],
#     "age": np.random.exponential(scale=30, size=100).astype(int) + 20,  # Right-skewed, > 0
#     "salary": np.random.exponential(scale=50000, size=100).astype(int) + 30000  # Right-skewed, > 0
# }
# df = pd.DataFrame(data)

# # Winsorizing extreme values
# outlier_cols = winsorize(df)
# print("Winsorized columns:", outlier_cols)

# # Log-transforming specific columns
# log_transformed_cols = log_transform(df, 'salary')
# print("Log-transformed columns:", log_transformed_cols)


def create_aggregate_variable(df, levels, var, func):
    """
    Replace non-numeric values in the specified variable and create an aggregate variable by applying a specified aggregation function.

    Parameters:
    df (DataFrame): Input DataFrame containing data to be aggregated.
    levels (list): List of columns to group by (e.g., ['year', 'state']).
    var (str): The name of the variable to be aggregated.
    func (str or callable): The aggregation function to apply (e.g., 'sum', 'mean', or a custom function).

    Returns:
    DataFrame: Modified DataFrame with the aggregated variable added.
    """
    # Ensure the variable is numeric
    df[var] = pd.to_numeric(df[var], errors="coerce")

    # Define the new column name
    agg_col_name = (
        f'{"_".join(levels)}_{func.__name__}_{var}'
        if callable(func)
        else f'{"_".join(levels)}_{func}_{var}'
    )

    # Perform groupby and aggregation
    aggregated = (
        df.groupby(levels, as_index=False)[var]
        .agg(func)
        .rename(columns={var: agg_col_name})
    )

    # Merge the aggregated result back into the original DataFrame
    df = df.merge(aggregated, on=levels, how="left")

    return df


# """Example usage"""
# firm_year_panel = create_aggregate_variable(firm_year_panel, ['year', 'state'], 'direct_premium_written', 'sum')


from recordlinkage.base import BaseIndexAlgorithm


class NgramsOverlap(BaseIndexAlgorithm):
    """
    Custom indexing class that uses n-gram overlap to link records between two DataFrames.
    """

    def __init__(self, query_column="given_name", candidate_column="given_name", n=4):
        """
        Initialize the NgramsOverlap indexer.

        Parameters:
        - query_column (str): The column name in df_a containing text for queries.
        - candidate_column (str): The column name in df_b containing text for candidates.
        - n (int): The size of the n-grams to be used for overlap calculation.
        """
        super().__init__()
        self.query_column = query_column
        self.candidate_column = candidate_column
        self.n = n

    def _ngrams_overlap(
        self, df_queries, df_candidates, query_column, candidate_column, n
    ):
        """
        Compute the n-gram overlap between query and candidate text columns and return the indices of overlaps.

        Parameters:
        - df_queries (pd.DataFrame): DataFrame containing the queries.
        - df_candidates (pd.DataFrame): DataFrame containing the candidates.
        - query_column (str): Column containing query text.
        - candidate_column (str): Column containing candidate text.
        - n (int): N-gram size.

        Returns:
        - pd.MultiIndex: MultiIndex where each pair (query_index, candidate_index) has n-gram overlap.
        """

        # 1. Initialize the n-gram vectorizer
        vectorizer = CountVectorizer(
            analyzer="char", ngram_range=(n, n), binary=True, dtype=np.uint8
        )

        # 2. Transform query and candidate text columns into n-gram feature matrices
        X_queries = vectorizer.fit_transform(df_queries[query_column])
        X_candidates = vectorizer.transform(df_candidates[candidate_column])

        # 3. Compute the n-gram overlap matrix using dot product
        overlap_matrix = X_queries.dot(X_candidates.T)

        # 4. Find all non-zero positions in the overlap matrix
        query_indices, candidate_indices = np.nonzero(overlap_matrix)

        # 5. Map back to the original indices
        query_index_original = df_queries.index[query_indices]
        candidate_index_original = df_candidates.index[candidate_indices]

        # 6. Return a MultiIndex of (query_index, candidate_index) pairs
        return pd.MultiIndex.from_arrays(
            [query_index_original, candidate_index_original],
            names=["query_index", "candidate_index"],
        )

    def _link_index(self, df_a, df_b):
        """
        Generate index pairs based on n-gram overlap between df_a and df_b.

        Parameters:
        - df_a (pd.DataFrame): The first DataFrame containing records to be indexed.
        - df_b (pd.DataFrame): The second DataFrame containing records to be indexed.

        Returns:
        - pd.MultiIndex: MultiIndex of (query_index, candidate_index) pairs with n-gram overlap.
        """
        return self._ngrams_overlap(
            df_queries=df_a,
            df_candidates=df_b,
            query_column=self.query_column,
            candidate_column=self.candidate_column,
            n=self.n,
        )


# def ngrams_overlap(df_queries, df_candidates, query_column, candidate_column, n=4):
#     """
#     Compute the n-gram overlap between query and candidate text columns and return the indices of overlaps.

#     Parameters:
#     - df_queries (pd.DataFrame): DataFrame containing the queries.
#     - df_candidates (pd.DataFrame): DataFrame containing the candidates.
#     - query_column (str): Column containing query text.
#     - candidate_column (str): Column containing candidate text.
#     - n (int): N-gram size.

#     Returns:
#     - pd.MultiIndex: MultiIndex where each pair (query_index, candidate_index) has n-gram overlap, using the original indices.
#     """

#     # Initialize the vectorizer for n-grams
#     vectorizer = CountVectorizer(
#         analyzer="char", ngram_range=(n, n), binary=True, dtype=np.uint8
#     )

#     # Transform query and candidate text columns into n-gram matrices
#     X_queries = vectorizer.fit_transform(df_queries[query_column])
#     X_candidates = vectorizer.transform(df_candidates[candidate_column])

#     # Compute overlap matrix as the dot product of query and candidate matrices
#     overlap_matrix = X_queries.dot(X_candidates.T)

#     # Find non-zero indices in the overlap matrix
#     query_indices, candidate_indices = np.nonzero(overlap_matrix)

#     # Map back to original indices
#     query_index_original = df_queries.index[query_indices]
#     candidate_index_original = df_candidates.index[candidate_indices]

#     # Return MultiIndex using original indices
#     return pd.MultiIndex.from_arrays(
#         [query_index_original, candidate_index_original],
#         names=["query_index", "candidate_index"],
#     )


# # """Example usage"""
# # df_queries = pd.DataFrame({'text': ['apple banana', 'orange grape']})
# # df_candidates = pd.DataFrame({'text': ['banana apple', 'grape orange', 'pineapple']})
# # ngram_overlap = ngrams_overlap(df_queries, df_candidates, 'text', 'text', n=3)


def determine_entity(df, column, string_list):
    """
    Categorize entries based on the exact presence of terms using word boundaries.
    Avoids partial matches like 'partner' matching 'partnership'.
    """
    # Use regex with word boundaries (\b) for exact word matching
    contains_any = pd.concat(
        [
            df[column].str.lower().str.contains(rf"\b{s}\b", na=False, regex=True)
            for s in string_list
        ],
        axis=1,
    )
    contains_any.columns = string_list

    # Count matches
    matches = contains_any.sum(axis=1)
    entity = pd.Series("other", index=df.index)

    # Assign categories
    for s in string_list:
        entity[contains_any[s] & (matches == 1)] = s

    # Assign 'multi' for multiple matches
    entity[matches > 1] = "multi"
    return entity


# build blocking string for uniersity
entity_list = [
    "university",
    "school",
    "college",
    "center",
    "centre",
    "academy",
    "institute",
]
directions_list = [
    "northern",
    "southern",
    "eastern",
    "western",
    "northeast",
    "southeast",
    "northwest",
    "southwest",
]


"""
useful dict and keywords list to clean columns for match
"""
face_book_url_list = ["https", "http", "www", "com", "facebook"]
linkedin_url_list = ["https", "http", "www", "linkedin", "company", "com"]

# read member to create blocking string for entity and direction at first when merge university
university_list = ["of", "the", "and", "at", "lnc", "main campus"] + entity_list
university_dict = {
    "technology": "tech",
    "technical": "tech",
    "state": "stat",
    "community": "comm",
    "christian": "christ",
    "north": "abcde",
    "south": "fghij",
    "east": "klmno",
    "west": "pqrst",
    "saint": "st",
    "aampm": "a m",
    "aampt": "a t",
}
# build blocking string for uniersity
entity_list = [
    "university",
    "school",
    "college",
    "center",
    "centre",
    "academy",
    "institute",
]
directions_list = [
    "northern",
    "southern",
    "eastern",
    "western",
    "northeast",
    "southeast",
    "northwest",
    "southwest",
]

firm_dict = {
    "ac": " ",
    "ca": " ",
    "co": " ",
    "lc": " ",
    "pa": " ",
    "pc": " ",
    "pcinc": " ",
    "pl": " ",
    "plc": " ",
    "ps": " ",
    "psc": " ",
    "cia": " ",
    "cie": " ",
    "pro forma": " ",
    "adr": " ",
    "ads": " ",
    "cl a": " ",
    "cl b": " ",
    "conn": " ",
    "consolidated": " ",
    "de": " ",
    "del": " ",
    "ny shares": " ",
    "old": " ",
    "ord": " ",
    "pre amend": " ",
    "pre divest": " ",
    "pre fasb": " ",
    "preamend": " ",
    "predivest": " ",
    "pref": " ",
    "prefasb": " ",
    "pro forma": " ",
    "pro forma1": " ",
    "pro forma2": " ",
    "pro forma3": " ",
    "proj": " ",
    "projected": " ",
    "redh": " ",
    "ser a": " ",
    "ser a com": " ",
    "spn": " ",
    "3m co": "3m company",
    "a b": " ",
    "a california corp": " ",
    "a delaware corp": " ",
    "a s": " ",
    "aac": " ",
    "ab": " ",
    "academy": "acad",
    "accptnce": "acceptance",
    "actien gesellschaft": " ",
    "actiengesellschaft": " ",
    "ad": " ",
    "advertsg": "advertising",
    "advisors": " ",
    "advntge": "advantage",
    " ae": " ",
    " ag": " ",
    "ag co": "ag & co kg",
    "ag co kg": "ag & co kg",
    "ag co ohg": "ag & co ohg",
    "ag cokg": "ag & co kg",
    "ag coohg": "ag & co ohg",
    "ag u co": "ag & co kg",
    "ag u co kg": "ag & co kg",
    "ag u co ohg": "ag & co ohg",
    "ag u cokg": "ag & co kg",
    "ag u coohg": "ag & co ohg",
    "agricola": "agric",
    "agricolas": "agric",
    "agricole": "agric",
    "agricoles": "agric",
    "agricoli": "agric",
    "agricolture": "agric",
    "agricultura": "agric",
    "agricultural": "agric",
    "agriculture": "agric",
    "airln": "airlines",
    "airls": "airlines",
    "ais": " ",
    "akademi": "akad",
    "akademia": "akad",
    "akademie": "akad",
    "akademiei": "akad",
    "akademii": "akad",
    "akademija": "akad",
    "akademiya": "akad",
    "akademiyakh": "akad",
    "akademiyam": "akad",
    "akademiyami": "akad",
    "akademiyu": "akad",
    "akciova spolecnost": " ",
    "aksjeselskap": " ",
    "aksjeselskapet": " ",
    "aktiebolag": " ",
    "aktiebolaget": " ",
    "aktien gesellschaft": " ",
    "aktiengesellschaft": " ",
    "aktieselskab": " ",
    "aktieselskabet": " ",
    "aktionierno drushestwo": " ",
    "al": " ",
    "allgemeine": "allg",
    "allgemeiner": "allg",
    "allmennaksjeselskap": " ",
    "allmennaksjeselskapet": " ",
    "am": "america",
    "amba": " ",
    "amer": "american",
    "and": " ",
    "andelslag": " ",
    "andelslaget": " ",
    "andelsselskab": " ",
    "andelsselskabet": " ",
    "anonyme dite": " ",
    "anonymos etairia": " ",
    "anpartsselskab": " ",
    "anpartsselskabet": " ",
    "ans": " ",
    "ansvarlig selskap": " ",
    "ansvarlig selskapet": " ",
    "antrepriza": "antr",
    "apararii": "apar",
    "aparate": "apar",
    "aparatelor": "apar",
    "apb": " ",
    "apparate": "app",
    "apparatebau": "app",
    "apparatus": "app",
    "apparechhi": "app",
    "appareil": "app",
    "appareillage": "app",
    "appareillages": "app",
    "appareils": "app",
    "applian": "appliances",
    "application": "appl",
    "applications": "appl",
    "applicazione": "appl",
    "applicazioni": "appl",
    "applictn": "appl",
    "aps": " ",
    "archtcts": "architects",
    "as": " ",
    "asa": " ",
    "assd": "asso",
    "assoc": "asso",
    "associacao": "asso",
    "associate": "asso",
    "associated": "asso",
    "associates": "asso",
    "association": "asso",
    "assocs": "asso",
    "atomc": "atomic",
    "bancorporation": "bancorp",
    "bancorportn": "bancorp",
    "bancrp": "bancorp",
    "bancsh": "bancshares",
    "bancshr": "bancshares",
    "bcshs": "bancshares",
    "bell & howell operating co": "bell + howell company",
    "bendix corp": "bendix corporation(now allied-signal inc.)",
    "beperkte aansprakelijkheid": "pvba",
    "beschrankter haftung": "bet gmbh",
    "besloten vennootschap": " ",
    "besloten vennootschap met": " ",
    "beteiligungs gesellschaft mit": "bet gmbh",
    "beteiligungsgesellschaft": "bet ges",
    "beteiligungsgesellschaft mbh": "bet gmbh",
    "bk": "bank",
    "bldgs": "buildings",
    "blsa": " ",
    "bncshrs": "bancshares",
    "borgwarner inc": "borg-warner corporation",
    "broadcastg": "broadcasting",
    "broderna": "brdr",
    "brodrene": "brdr",
    "broederna": "brdr",
    "broedrene": "brdr",
    "brothers": "bros",
    "brwg": "brewing",
    "btlng": "bottling",
    "business": "biz",
    "bv": " ",
    "bv beperkte aansprakelijkheid": "bvba",
    "cblvision": "cablevision",
    "center": "cent",
    "centraal": "cent",
    "central": "cent",
    "centrala": "cent",
    "centrale": "cent",
    "centrales": "cent",
    "centraux": "cent",
    "centre": "cent",
    "centro": "cent",
    "centrs": "centers",
    "centrul": "cent",
    "centrum": "cent",
    "cercetare": "cerc",
    "cercetari": "cerc",
    "champnship": "championship",
    "chemical": "chem",
    "chemicals": "chem",
    "chemicke": "chem",
    "chemickej": "chem",
    "chemicky": "chem",
    "chemickych": "chem",
    "chemiczne": "chem",
    "chemiczny": "chem",
    "chemie": "chem",
    "chemii": "chem",
    "chemisch": "chem",
    "chemische": "chem",
    "chemiskej": "chem",
    "chemistry": "chem",
    "chevrontexaco": "chevron texaco",
    "chimic": "chim",
    "chimica": "chim",
    "chimice": "chim",
    "chimici": "chim",
    "chimico": "chim",
    "chimie": "chim",
    "chimiei": "chim",
    "chimieskoj": "chim",
    "chimii": "chim",
    "chimiko": "chim",
    "chimique": "chim",
    "chimiques": "chim",
    "chimiya": "chim",
    "chimiyakh": "chim",
    "chimiyam": "chim",
    "chimiyami": "chim",
    "chimiyu": "chim",
    "chrysler corp": "chrysler motors corporation",
    "chse": "chase",
    "cie": " ",
    "cisco systems inc": "cisco technology, inc.",
    "cl a": " ",
    "cla": " ",
    "close corporation": "cc",
    "cmmnctns": "communication",
    "cnvrsion": "conversion",
    "co": " ",
    "co ltd": " ",
    "co operative": "coop",
    "co operatives": "coop",
    "coff": "coffee",
    "cogmbh": " ",
    "combinatul": "comb",
    "comm": "communication",
    "commanditaire vennootschap": " ",
    "commanditaire vennootschap op aandelen": " ",
    "commanditaire vennootschap op andelen": " ",
    "commercial": "comml",
    "commerciale": "comml",
    "commn": "communication",
    "commun": "communication",
    "communctn": "communication",
    "communications": "communication",
    "communicatns": "communication",
    "communictns": "communication",
    "comp": "computers",
    "compagnia": "cia",
    "compagnie": " ",
    "compagnie francaise": "cie fr",
    "compagnie generale": "cie gen",
    "compagnie industriale": "cie ind",
    "compagnie industrielle": "cie ind",
    "compagnie industrielles": "cie ind",
    "compagnie internationale": "cie int",
    "compagnie nationale": "cie nat",
    "compagnie parisien": "cie paris",
    "compagnie parisienn": "cie paris",
    "compagnie parisienne": "cie paris",
    "companhia": "cia",
    "companies": " ",
    "company": " ",
    "computr": "computer",
    "conferencg": "conferencing",
    "consolidated": "consol",
    "constrn": "constr",
    "construccion": "constr",
    "construccione": "constr",
    "construcciones": "constr",
    "constructie": "constr",
    "constructii": "constr",
    "constructiilor": "constr",
    "construction": "constr",
    "constructions": "constr",
    "constructor": "constr",
    "constructortul": "constr",
    "constructorul": "constr",
    "consultants": "cons",
    "consulting": "cons",
    "contl": "continental",
    "contnt": "continental",
    "contrl": "control",
    "cooperatieve": "coop",
    "cooperativa": "coop",
    "cooperative": "coop",
    "cooperatives": "coop",
    "corp": " ",
    "corporastion": " ",
    "corporate": " ",
    "corporation": " ",
    "corporation of america": " ",
    "corporatioon": " ",
    "cos": " ",
    "costruzioni": "costr",
    "cp": " ",
    "cpas": "cpa",
    "ctr": "cent",
    "ctrs": "centers",
    "cv": " ",
    "cva": " ",
    "cvoa": " ",
    "cvrgs": "coverings",
    "da": " ",
    "dell inc": "dell products, l.p.",
    "delphi corp": "delphi technologies, inc.",
    "demokratische republik": "ddr",
    "demokratischen republik": "ddr",
    "departement": "dept",
    "department": "dept",
    "deutsch": "deut",
    "deutsche": "deut",
    "deutschen": "deut",
    "deutscher": "deut",
    "deutsches": "deut",
    "deutschland": "deut",
    "dev": "dev",
    "develop": "dev",
    "development": "dev",
    "developments": "dev",
    "developpement": "dev",
    "developpements": "dev",
    "devl": "dev",
    "devlp": "dev",
    "df": " ",
    "distr": "distribution",
    "distribut": "distribution",
    "distributn": "distribution",
    "division": "div",
    "divisione": "div",
    "dpt": "dept",
    "dpt sts": "dept stores",
    "drushestwo s orgranitschena otgowornost": " ",
    "du pont (e i) de nemours": "e. i. du pont de nemours and company",
    "ead": " ",
    "ee": " ",
    " eg": " ",
    "egenossenschaft": " ",
    "eingetragene genossenschaft": " ",
    "eingetragener verein": "ev",
    "elctrncs": "electronics",
    "electr": "electronics",
    "electronics": "electronics",
    "engineering": "eng",
    "engnrd": "engineered",
    "enmt": "entertainment",
    "enrgy": "energy",
    "enterprises": "ent",
    "entertain": "entertainment",
    "entertnmnt": "entertainment",
    "entmnt": "entertainment",
    "entmt": "entertainment",
    "entreprise unipersonnelle a responsabilite limitee": " ",
    "entrpr": "ent",
    "entrprise": "ent",
    "entrprs": "ent",
    "envir": "environmental",
    "envirnmntl": "environmental",
    "envr": "environmental",
    "eood": " ",
    "epe": " ",
    "equipement": "equip",
    "equipements": "equip",
    "equipment": "equip",
    "equipments": "equip",
    "equipmt": "equip",
    "espana": " ",
    "establishment": "estab",
    "establishments": "estab",
    "establissement": "estab",
    "establissements": "estab",
    "et": " ",
    "et cie": " ",
    "etablissement": "etab",
    "etablissements": "etab",
    "etabs": "etab",
    "etairia periorismenis evthinis": " ",
    "etcie": " ",
    "eterrorrythmos": " ",
    "ets": "etab",
    "etude": "etud",
    "etudes": "etud",
    "eurl": " ",
    "europaeische": "euro",
    "europaeischen": "euro",
    "europaeisches": "euro",
    "europaische": "euro",
    "europaischen": "euro",
    "europaisches": "euro",
    "europe": "euro",
    "europea": "euro",
    "european": "euro",
    "europeen": "euro",
    "europeenne": "euro",
    "exchg": "exchange",
    "exploatering": "expl",
    "exploaterings": "expl",
    "exploitatie": "expl",
    "exploitation": "expl",
    "exploitations": "expl",
    "explor": "exploration",
    "f lli": "frat",
    "fabbrica": "fab",
    "fabbricazioni": "fab",
    "fabbriche": "fab",
    "fabrica": "fab",
    "fabrication": "fab",
    "fabrications": "fab",
    "fabriek": "fab",
    "fabrieken": "fab",
    "fabrik": "fab",
    "fabriker": "fab",
    "fabrique": "fab",
    "fabriques": "fab",
    "fabrizio": "fab",
    "fabryka": "fab",
    "farmaceutica": "farm",
    "farmaceutice": "farm",
    "farmaceutiche": "farm",
    "farmaceutici": "farm",
    "farmaceutico": "farm",
    "farmaceuticos": "farm",
    "farmaceutisk": "farm",
    "farmacevtskih": "farm",
    "farmacie": "farm",
    "finl": "financial",
    "firma": "fa",
    "flli": "frat",
    "fncl": "financial",
    "fndg": "funding",
    "fondation": "fond",
    "fondazione": "fond",
    "foundation": "found",
    "foundations": "found",
    "francais": "fr",
    "francaise": "fr",
    "fratelli": "frat",
    "gakko hojin": "gh",
    "gakko houjin": "gh",
    "gbr": " ",
    "geb": "gebr",
    "gebroder": "gebr",
    "gebroders": "gebr",
    "gebroeder": "gebr",
    "gebroeders": "gebr",
    "gebruder": "gebr",
    "gebruders": "gebr",
    "gebrueder": "gebr",
    "gebrueders": "gebr",
    "general": "gen",
    "generala": "gen",
    "generale": "gen",
    "generales": "gen",
    "generaux": "gen",
    "genossenschaft": " ",
    "gesellschaft": " ",
    "gesellschaft burgerlichen rechts": " ",
    "gesellschaft m b h": " ",
    "gesellschaft mbh": " ",
    "gesellschaft mit beschrankter haftung": " ",
    "gesmbh": " ",
    "gewerkschaft": "gew",
    "gewone commanditaire vennootschap": "gcv",
    "gie": " ",
    "gld": "gold",
    "gmbh": " ",
    "gmbh co": "gmbh & co kg",
    "gmbh co kg": "gmbh & co kg",
    "gmbh co ohg": "gmbh &co ohg",
    "gmbh cokg": "gmbh & co kg",
    "gmbh coohg": "gmbh & co ohg",
    "gmbh u co": "gmbh & co kg",
    "gmbh u co kg": "gmbh & co kg",
    "gmbh u co ohg": "gmbh & co ohg",
    "gmbh u cokg": "gmbh & co kg",
    "gmbh u coohg": "gmbh & co ohg",
    "gmbhco": " ",
    "gmbhcokg": " ",
    "gmbhcokgaa": " ",
    "gomei gaisha": "gk",
    "gomei kaisha": "gk",
    "goodrich corp": "b. f. goodrich co.",
    "goshi kaisha": "gk",
    "goushi gaisha": "gk",
    "gp": " ",
    "grace (w r) & co": "w. r. grace & co.",
    "great britain": "gb",
    "groupement": " ",
    "groupement d interet economique": " ",
    "groupment": " ",
    "grp": " ",
    "gruppe": " ",
    "gutehoffnungschuette": "ghh",
    "gutehoffnungschutte": "ghh",
    "handels bolaget": " ",
    "handelsbolag": "hb ",
    "handelsbolaget": " ",
    "handelsmaatschappij": "handl",
    "handelsmij": "handl",
    "hb": " ",
    "her majesty the queen": "uk",
    "her majesty the queen in right of canada as represented by the minister of": "canada min of",
    "hldg": "hldgs",
    "hldgs": "hldgs",
    "hlds": "hldgs",
    "hlt ntwk": "health network",
    "hlth": "health",
    "hlthcare": "healthcare",
    "hlthcr": "healthcare",
    "holding": "hldgs",
    "holdings": "hldgs",
    "homemde": "homemade",
    "hsptl": "hospital",
    "htls res": "hotels & resorts",
    "illum": "illumination",
    "inc": " ",
    "incorporated": " ",
    "incorporation": " ",
    "indl": "ind",
    "indpt": "independent",
    "indty": "indemnity",
    "industri": "ind",
    "industria": "ind",
    "industrial": "ind",
    "industriala": "ind",
    "industriale": "ind",
    "industriali": "ind",
    "industrializare": "ind",
    "industrializarea": "ind",
    "industrials": "ind",
    "industrias": "ind",
    "industrie": "ind",
    "industrieele": "ind",
    "industriei": "ind",
    "industriel": "ind",
    "industriell": "ind",
    "industrielle": "ind",
    "industrielles": "ind",
    "industriels": "ind",
    "industrier": "ind",
    "industries": "ind",
    "industrii": "ind",
    "industrij": "ind",
    "industriya": "ind",
    "industriyakh": "ind",
    "industriyam": "ind",
    "industriyami": "ind",
    "industriyu": "ind",
    "industry": "ind",
    "informatn": "info",
    "ingenier": "ing",
    "ingenieria": "ing",
    "ingenieur": "ing",
    "ingenieurbuero": "ing",
    "ingenieurbureau": "ing",
    "ingenieurburo": "ing",
    "ingenieurgesellschaft": "ing",
    "ingenieurs": "ing",
    "ingenieursbureau": "ing",
    "ingenieurtechnische": "ing",
    "ingenieurtechnisches": "ing",
    "ingenioerfirmaet": "ing",
    "ingeniorsfirma": "ing",
    "ingeniorsfirman": "ing",
    "ingenjorsfirma": "ing",
    "inginerie": "ing",
    "insinooritomisto": "instmsto",
    "institut": "inst",
    "institut francais": "inst fr",
    "institut national": "inst nat",
    "instituta": "inst",
    "institutam": "inst",
    "institutami": "inst",
    "institutamkh": "inst",
    "institute": "inst",
    "institute francaise": "inst fr",
    "institute nationale": "inst nat",
    "institutes": "inst",
    "institutet": "inst",
    "instituto": "inst",
    "institutom": "inst",
    "institutov": "inst",
    "institutt": "inst",
    "institutu": "inst",
    "institutul": "inst",
    "instituty": "inst",
    "instituut": "inst",
    "institzht": "inst",
    "instns": "institutions",
    "instrumen": "instr",
    "instrument": "instr",
    "instrumentation": "instr",
    "instrumente": "instr",
    "instruments": "instr",
    "instrumnt": "instr",
    "instytut": "inst",
    "integratrs": "integrators",
    "interessentskab": " ",
    "interessentskabet": " ",
    "internacional": "int",
    "international": "int",
    "internationale": "int",
    "internationalen": "int",
    "internationaux": "int",
    "internationella": "int",
    "internationl": "int",
    "internatl": "int",
    "internazionale": "int",
    "intl": " ",
    "intreprinderea": "intr",
    "intrtechnlgy": "intertechnology",
    "investments": " ",
    "invs": " ",
    "invt": "investment",
    "is": " ",
    "istituto": "ist",
    "itali": "ital",
    "italia": "ital",
    "italian": "ital",
    "italiana": "ital",
    "italiane": "ital",
    "italiani": "ital",
    "italiano": "ital",
    "italien": "ital",
    "italienne": "ital",
    "italo": "ital",
    "italy": "ital",
    "jpmorgan": "j p morgan",
    "jsc": " ",
    "julkinen osakeyhtio": " ",
    "junior": "jr",
    "kabushiki gaisha": " ",
    "kabushiki gaisya": " ",
    "kabushiki kaisha": " ",
    "kabushiki kaisya": " ",
    "kabushikigaisha": " ",
    "kabushikigaisya": " ",
    "kabushikikaisha": " ",
    "kabushikikaisya": " ",
    "kas": " ",
    "kb": " ",
    "kd": " ",
    "kda": " ",
    "kg": " ",
    "kgaa": " ",
    "kk": " ",
    "kogyo kk": " ",
    "komandit gesellschaft": " ",
    "komanditgesellschaft": " ",
    "komanditni spolecnost": " ",
    "komanditno drushestwo": " ",
    "komanditno drushestwo s akzii": " ",
    "kombinat": "komb",
    "kombinatu": "komb",
    "kombinaty": "komb",
    "kommandiittiyhtio": " ",
    "kommandit bolag": " ",
    "kommandit bolaget": " ",
    "kommandit gesellschaft": " ",
    "kommandit gesellschaft auf aktien": " ",
    "kommanditaktieselskab": " ",
    "kommanditaktieselskabet": " ",
    "kommanditbolag": " ",
    "kommanditbolaget": " ",
    "kommanditgesellschaft": " ",
    "kommanditgesellschaft auf aktien": " ",
    "kommanditselskab": " ",
    "kommanditselskabet": " ",
    "kommandittselskap": " ",
    "kommandittselskapet": " ",
    "koncernovy podnik": "kp",
    "koninklijke": "konink",
    "kood": " ",
    "koop": " ",
    "ks": " ",
    "kunststoff": "kunst",
    "kunststofftechnik": "kunst",
    "kutato intezet": "ki",
    "kutato intezete": "ki",
    "kutatointezet": "ki",
    "kutatointezete": "ki",
    "ky": " ",
    "laboratoir": "lab",
    "laboratoire": "lab",
    "laboratoires": "lab",
    "laboratori": "lab",
    "laboratoriei": "lab",
    "laboratories": "lab",
    "laboratorii": "lab",
    "laboratorij": "lab",
    "laboratorio": "lab",
    "laboratorios": "lab",
    "laboratorium": "lab",
    "laboratory": "lab",
    "labortori": "lab",
    "lavoraza": "lavoraz",
    "lavorazi": "lavoraz",
    "lavorazio": "lavoraz",
    "lavorazione": "lavoraz",
    "lavorazioni": "lavoraz",
    "lilly (eli) & co": "eli lilly and company",
    "limitada": "ltda",
    "limited": " ",
    "limited partnership": " ",
    "llc": " ",
    "llcllp": " ",
    "llcpc": " ",
    "llcpllc": " ",
    "llp": " ",
    "llppc": " ",
    "llpllc": " ",
    "lp": " ",
    "ltd": " ",
    "ltd co": " ",
    "ltd ltee": " ",
    "maatschappij": "mij",
    "magyar tudomanyos akademia": "mta",
    "managemnt": "management",
    "managmnt": "management",
    "manhatn": "manhattan",
    "manifattura": "mfr",
    "manifatturas": "mfr",
    "manifatture": "mfr",
    "manuf": "mfg",
    "manufacturas": "mfr",
    "manufacture": "mfr",
    "manufacturer": "mfr",
    "manufacturers": "mfr",
    "manufactures": "mfr",
    "manufacturing": "mfg",
    "manufacturings": "mfg",
    "manufatura": "mfr",
    "maschin": "masch",
    "maschinen": "masch",
    "maschinenbau": "maschbau",
    "maschinenbauanstalt": "maschbau",
    "maschinenfab": "maschfab",
    "maschinenfabriek": "maschfab",
    "maschinenfabrik": "maschfab",
    "maschinenfabriken": "maschfab",
    "maschinenvertrieb": "masch",
    "mdse": "merchandising",
    "measurmnt": "measurement",
    "med optic": "medical optics",
    "medical": "med",
    "merchndsng": "merchandising",
    "mgmt": "management",
    "mgrs": "managers",
    "mgt": "management",
    "microwav": "microwave",
    "minister": "min",
    "ministere": "min",
    "ministerium": "min",
    "ministero": "min",
    "ministerstv": "min",
    "ministerstva": "min",
    "ministerstvakh": "min",
    "ministerstvam": "min",
    "ministerstvami": "min",
    "ministerstve": "min",
    "ministerstvo": "min",
    "ministerstvom": "min",
    "ministerstvu": "min",
    "ministerstwo": "min",
    "ministerul": "min",
    "ministre": "min",
    "ministry": "min",
    "minnesota mining and manufacturing company": "3m company",
    "mit": " ",
    "mit beschrankter haftung": "mbh",
    "mkts": "markets",
    "mltimedia": "multimedia",
    "mtg": "mortgage",
    "mtns": "moutains",
    "mtrs": "motors",
    "n v": " ",
    "naamloose venootschap": " ",
    "naamloze vennootschap": " ",
    "narodni podnik": "np",
    "narodnij podnik": "np",
    "narodny podnik": "np",
    "nat res": "natural resources",
    "nationaal": "nat",
    "national": "nat",
    "nationale": "nat",
    "nationaux": "nat",
    "natl": "nat",
    "nazionale": "naz",
    "nazionali": "naz",
    "netwrk": "network",
    "netwrks": "network",
    "norddeutsch": "norddeut",
    "norddeutsche": "norddeut",
    "norddeutscher": "norddeut",
    "norddeutsches": "norddeut",
    "nowest": "northwest",
    "ntwrk": "network",
    "nv": " ",
    "oborovy podnik": "op",
    "ocd": " ",
    "oe": " ",
    "oesterreich": "oesterr",
    "oesterreichisch": "oesterr",
    "oesterreichische": "oesterr",
    "oesterreichisches": "oesterr",
    "offene handels gesellschaft": " ",
    "offene handelsgesellschaft": " ",
    "officine meccanica": "off mec",
    "officine meccaniche": "off mec",
    "officine nationale": "off nat",
    "offshre": "offshore",
    "ohg": " ",
    "omorrythmos": " ",
    "ontwikkelings": "ontwik",
    "ontwikkelingsbureau": "ontwik",
    "ood": " ",
    "organisatie": "org",
    "organisation": "org",
    "organisations": "org",
    "organization": "org",
    "organizations": "org",
    "organiztn": "org",
    "organizzazione": "org",
    "osakeyhtio": " ",
    "osterreich": "oesterr",
    "osterreichisch": "oesterr",
    "osterreichische": "oesterr",
    "osterreichisches": "oesterr",
    "owens corning": "owens-corning fiberglas corporation",
    "oy": " ",
    "oy ab": " ",
    "oyj": " ",
    "oyj ab": " ",
    "p a": " ",
    "papsc": " ",
    "pac railwy": "pacific railway",
    "partnership": " ",
    "pblg": "publishing",
    "personenvennootschap met": "pvba",
    "pf": " ",
    "pharmaceutica": "pharm",
    "pharmaceutical": "pharm",
    "pharmaceuticals": "pharm",
    "pharmaceuticl": "pharm",
    "pharmaceutique": "pharm",
    "pharmaceutiques": "pharm",
    "pharmact": "pharm",
    "pharmacticals": "pharm",
    "pharmazeutika": "pharm",
    "pharmazeutisch": "pharm",
    "pharmazeutische": "pharm",
    "pharmazeutischen": "pharm",
    "pharmazie": "pharm",
    "plast": "plastics",
    "plc": " ",
    "pllc": " ",
    "pllp": " ",
    "ppty": "property",
    "pptys": "properties",
    "pptys tst": "properties trust",
    "prelucrare": "preluc",
    "prelucrarea": "preluc",
    "prodotti": "prod",
    "prods": "prod",
    "prodtn": "prodn",
    "produce": "prod",
    "product": "prod",
    "producta": "prod",
    "productas": "prod",
    "productie": "prod",
    "production": "prodn",
    "productions": "prodn",
    "productn": "prodn",
    "producto": "prod",
    "productores": "prod",
    "productos": "prod",
    "products": "prod",
    "produit": "prod",
    "produit chimique": "prod chim",
    "produit chimiques": "prod chim",
    "produits": "prod",
    "produkcji": "prod",
    "produkt": "prod",
    "produkte": "prod",
    "produkter": "prod",
    "produktion": "prodn",
    "produktions": "prodn",
    "produse": "prod",
    "produtos": "prod",
    "produzioni": "prodn",
    "proiectare": "proi",
    "proiectari": "proi",
    "property tr": "property trust",
    "proprietary": "pty",
    "prpane": "propane",
    "przedsiebiostwo": "przedsieb",
    "przemyslu": "przeym",
    "pts": "parts",
    "public liability company": " ",
    "public limited": " ",
    "public limited company": " ",
    "publikt aktiebolag": " ",
    "publish": "publishing",
    "publshing": "publishing",
    "pubn": "publications",
    "pubns": "publications",
    "pwr": "power",
    "railrd": "railroad",
    "realisation": "real",
    "realisations": "real",
    "rech & dev": "r&d",
    "recherche": "rech",
    "recherche et development": "r&d",
    "recherche et developpement": "r&d",
    "recherches": "rech",
    "recherches et developments": "r&d",
    "recherches et developpements": "r&d",
    "recreatn": "recreation",
    "recycl": "recycling",
    "refin": "refining",
    "refng": "refining",
    "res & dev": "r&d",
    "research": "res",
    "research & development": "r&d",
    "research and development": "r&d",
    "restr": "restaurant",
    "rests": "restaurants",
    "retailng": "retailing",
    "rijksuniversiteit": "rijksuniv",
    "rlty": "realty",
    "rr": "railroad",
    "rsch": "res",
    "rtng": "rating",
    "sa": " ",
    "sa dite": " ",
    "sapa": " ",
    "sarl": " ",
    "sarl unipersonnelle": " ",
    "sarlu": " ",
    "sas": " ",
    "sas unipersonnelle": " ",
    "sasu": " ",
    "sc": " ",
    "sca": " ",
    "schlumberger ltd": "schlumberger technology corporation",
    "schweizer": "schweiz",
    "schweizerisch": "schweiz",
    "schweizerische": "schweiz",
    "schweizerischer": "schweiz",
    "schweizerisches": "schweiz",
    "science": "sci",
    "sciences": "sci",
    "scientif": "sci",
    "scientific": "sci",
    "scientifica": "sci",
    "scientifique": "sci",
    "scientifiques": "sci",
    "scs": " ",
    "sdruzeni podnik": " ",
    "sdruzeni podniku": " ",
    "searle (g.d.) & co": "g. d. searle & co.",
    "secreatry": "sec",
    "secretary": "sec",
    "secretary of state for": "uk sec for",
    "secretaty": "sec",
    "secretry": "sec",
    "selskap med delt ansar": " ",
    "semicondtr": "semiconductor",
    "serv": "services",
    "shadan hojin": "sh",
    "sicmed life systems": "sci-med life systems, inc.",
    "siderurgic": "sider",
    "siderurgica": "sider",
    "siderurgicas": "sider",
    "siderurgie": "sider",
    "siderurgique": "sider",
    "sk": " ",
    "sl": " ",
    "sltns": "solutions",
    "snc": " ",
    "soc a responsabilit� limitata": " ",
    "soc anonyme": " ",
    "soc dite": " ",
    "soc en commandita": " ",
    "soc in accomandita per azioni": " ",
    "soc limitada": " ",
    "soc par actions simplifiees": " ",
    "sociedad": "soc",
    "sociedad anonima": " ",
    "sociedad civil": "soc civ",
    "sociedad de responsabilidad limitada": " ",
    "sociedad espanola": "soc espan",
    "sociedade": "soc",
    "societa": "soc",
    "societa applicazione": "soc appl",
    "societa in accomandita semplice": " ",
    "societa in nome collectivo": " ",
    "societa per azioni": " ",
    "societe": "soc",
    "societe a responsabilite limitee": " ",
    "societe a responsibilite limitee": " ",
    "societe alsacienne": "soc alsac",
    "societe anonyme": " ",
    "societe anonyme dite": " ",
    "societe anonyme simplifiee": " ",
    "societe application": "soc appl",
    "societe auxiliaire": "soc aux",
    "societe chimique": "soc chim",
    "societe civile": "soc civ",
    "societe civile immobiliere": "sci",
    "societe commerciale": "soc comml",
    "societe commerciales": "soc comml",
    "societe en commandite par actions": " ",
    "societe en commandite simple": " ",
    "societe en nom collectif": " ",
    "societe en participation": " ",
    "societe etude": "soc etud",
    "societe etudes": "soc etud",
    "societe exploitation": "soc expl",
    "societe generale": "soc gen",
    "societe industrielle": "soc ind",
    "societe industrielles": "soc ind",
    "societe mecanique": "soc mec",
    "societe mecaniques": "soc mec",
    "societe nationale": "soc nat",
    "societe nouvelle": "soc nouv",
    "societe parisien": "soc paris",
    "societe parisienn": "soc paris",
    "societe parisienne": "soc paris",
    "societe privee a responsabilite limitee": " ",
    "societe technique": "soc tech",
    "societe techniques": "soc tech",
    "society": "soc",
    "softwre": "software",
    "soltns": "solutions",
    "solu": "solutions",
    "solut": "solutions",
    "sp": " ",
    "sp z oo": " ",
    "sp zoo": " ",
    "spa": " ",
    "spitalul": "spital",
    "spolecnost s rucenim omezenym": " ",
    "spolka akcyjna": " ",
    "spolka komandytowa": " ",
    "spolka prawa cywilnego": " ",
    "spolka z ograniczona odpowiedzialnoscia": " ",
    "sprl": " ",
    "spz oo": " ",
    "spzoo": " ",
    "squibb corp": "e. r. squibb + sons, inc.",
    "srl": " ",
    "sro": " ",
    "srvc": "services",
    "srvcs": "services",
    "st & almn": "steel & aluminum",
    "std": "standard",
    "ste anonyme": " ",
    "steakhse": "steakhouse",
    "sthwst": "southwest",
    "stiintifica": "stiint",
    "stl": "steel",
    "strs": "stores",
    "suddeutsch": "suddeut",
    "suddeutsche": "suddeut",
    "suddeutscher": "suddeut",
    "suddeutsches": "suddeut",
    "sup": "supply",
    "supermkts": "supermarkets",
    "supp": "supplies",
    "survys": "surveys",
    "svc": "services",
    "svcs": "services",
    "svsc": "services",
    "sys": "sys",
    "system": "sys",
    "systems": "sys",
    "systm": "sys",
    "tchnlgy": "tech",
    "tdk corp": "tdk corporation",
    "techngs": "tech",
    "technical": "tech",
    "technico": "tech",
    "techniczny": "tech",
    "technik": "tech",
    "technikai": "tech",
    "techniki": "tech",
    "technique": "tech",
    "techniques": "tech",
    "technisch": "tech",
    "technische": "tech",
    "technisches": "tech",
    "technl": "tech",
    "technlgies": "tech",
    "technol": "tech",
    "technolgs": "tech",
    "technologies": "tech",
    "technology": "tech",
    "tel": "telephone",
    "tele-comm": "telecom",
    "tele-commun": "telecom",
    "telecomms": "telecom",
    "telecommunicacion": "telecom",
    "telecommunication": "telecom",
    "telecommunications": "telecom",
    "telecommunicazioni": "telecom",
    "telecomunicazioni": "telecom",
    "teleconferenc": "teleconferencing",
    "teleg": "telegraph",
    "telegr": "telegraph",
    "telvsn": "television",
    "the ": " ",
    "tr": "trust",
    "trading ltd": " ",
    "transn": "transportation",
    "transportatn": "transportation",
    "transportn": "transportation",
    "trnsactn": "transaction",
    "trustul": "trust",
    "u s surgical corp": "united states surgical corporation",
    "united kingdom": "uk",
    "united states": "usa",
    "united states government as represented by the secretary of": "us sec",
    "united states of america": "usa",
    "united states of america administrator": "us admin",
    "united states of america as represented by the administrator": "us admin",
    "united states of america as represented by the dept": "us dept",
    "united states of america as represented by the secretary": "us sec",
    "united states of america as represented by the united states dept": "us dept",
    "united states of america represented by the secretary": "us sec",
    "united states of america secretary of": "us sec",
    "united states of american as represented by the united states dept": "us dept",
    "united states of americas as represented by the secretary": "us sec",
    "unites states of america as represented by the secretary": "us sec",
    "universidad": "univ",
    "universidade": "univ",
    "universita": "univ",
    "universita degli studi": "univ",
    "universitaet": "univ",
    "universitair": "univ",
    "universitaire": "univ",
    "universitat": "univ",
    "universitatea": "univ",
    "universite": "univ",
    "universiteit": "univ",
    "universitet": "univ",
    "universiteta": "univ",
    "universitetam": "univ",
    "universitetami": "univ",
    "universitete": "univ",
    "universitetom": "univ",
    "universitetov": "univ",
    "universitetu": "univ",
    "universitety": "univ",
    "university": "univ",
    "uniwersytet": "univ",
    "ust inc": "united sts tob co",
    "utd": "united",
    "utilaj": "util",
    "utilaje": "util",
    "utilisation volkseigener betriebe": "veb",
    "utilisations volkseigener betriebe": "veb",
    "veb kombinat": "veb komb",
    "vennootschap onder firma": " ",
    "vereenigde": "ver",
    "verein": "ver",
    "vereinigte vereinigung": "ver",
    "vereinigtes vereinigung": "ver",
    "vereinigung volkseigener betriebung": "vvb",
    "verejna obchodni spolecnost": " ",
    "vereniging": "ver",
    "verwaltungen": "verw",
    "verwaltungs": "verw",
    "verwaltungsgesellschaft": "verw ges",
    "verwertungs": "verw",
    "vof": " ",
    "vos": " ",
    "vyzk ustav": "vu",
    "vyzk vyvojovy ustav": "vvu",
    "vyzkumny ustav": "vu",
    "vyzkumny vyvojovy ustav": "vvu",
    "vyzkumnyustav": "vu",
    "werkzeugmaschinenfabrik": "werkz maschfab",
    "werkzeugmaschinenkombinat": "werkz masch komb",
    "westdeutsch": "westdeut",
    "westdeutsche": "westdeut",
    "westdeutscher": "westdeut",
    "westdeutsches": "westdeut",
    "westinghouse elec": "westinghouse electric corp.",
    "williams (a.l.) corp": "a. l. williams corp.",
    "wissenschaftliche(s)": "wiss",
    "wissenschaftliches technisches zentrum": "wtz",
    "wstn": "western",
    "wtr": "water",
    "yugen kaisha": "yg yugen gaisha",
    "yuugen gaisha": "yg yugen gaisha",
    "yuugen kaisha": "yg yugen gaisha",
    "yuugen kaisya": "yg yugen gaisha",
    "zaidan hojin": "zh",
    "zaidan houjin": "zh",
    "zavodu": "zavod",
    "zavody": "zavod",
    "zentrale": "zent",
    "zentralen": "zent",
    "zentrales": "zent",
    "zentralinstitut": "zent inst",
    "zentrallaboratorium": "zent lab",
    "zentralna": "zent",
    "zentrum": "zent",
}
