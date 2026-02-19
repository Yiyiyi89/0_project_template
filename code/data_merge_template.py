import os
import re
import pandas as pd
import numpy as np
import recordlinkage

import warnings
from toolkit import clean_column, NgramsOverlap, firm_dict
from joblib import Parallel, delayed
from tqdm.auto import tqdm
from tqdm_joblib import tqdm_joblib

from config import temp_data_path, revelio_data_path

warnings.filterwarnings("ignore")


def block_candidates(
    df_queries_chunk, df_candidates_chunk, query_column, candidate_column
):
    # block 1: 4 n-grams overlap
    indexer = NgramsOverlap(
        query_column=f"{query_column}_clean",
        candidate_column=f"{candidate_column}_clean",
        n=4,
    )
    ngram_overlap = indexer.index(df_queries_chunk, df_candidates_chunk)

    # block 2: 1 ngram middle name
    indexer = NgramsOverlap(
        query_column="middle_name", candidate_column="middle_name", n=1
    )
    middlename_overlap = indexer.index(df_queries_chunk, df_candidates_chunk)

    # block 3: first name
    indexer = recordlinkage.Index()
    indexer.block(left_on=["first_name"], right_on=["first_name"])
    candidate_links1 = indexer.index(df_queries_chunk, df_candidates_chunk)

    # block 4: last name
    indexer = recordlinkage.Index()
    indexer.block(left_on=["last_name"], right_on=["last_name"])
    candidate_links2 = indexer.index(df_queries_chunk, df_candidates_chunk)

    # get intersection
    candidate_links = (
        candidate_links1.intersection(candidate_links2)
        .intersection(middlename_overlap)
        .intersection(ngram_overlap)
    )
    return candidate_links


def compare_and_save(
    df_queries_chunk,
    df_candidates_chunk,
    candidate_links,
    chunk_idx,
    query_id,
    candidate_id,
    query_column,
    candidate_column,
    output_path,
):
    # similarity calculation
    compare = recordlinkage.Compare(n_jobs=10)
    compare.string(
        f"{query_column}_clean",
        f"{candidate_column}_clean",
        method="levenshtein",
        label="name_similarity",
    )
    features = compare.compute(
        candidate_links, df_queries_chunk, df_candidates_chunk
    ).reset_index()

    # rename columns
    features = features.rename(
        columns={"level_0": "query_index", "level_1": "candidate_index"}
    )
    features = features.sort_values("name_similarity", ascending=False).drop_duplicates(
        subset="query_index"
    )

    # merge data
    df = pd.merge(
        df_queries_chunk,
        features,
        how="inner",
        left_on=df_queries_chunk.index,
        right_on="query_index",
    )
    df = pd.merge(
        df,
        df_candidates_chunk,
        how="inner",
        left_on="candidate_index",
        right_on=df_candidates_chunk.index,
    )

    # keep best match per query
    df = df.sort_values("name_similarity", ascending=False).drop_duplicates(
        subset=query_id
    )

    # save to disk immediately
    chunk_output_file = f"{output_path}/matched_chunk_{chunk_idx}.csv"
    df.to_csv(chunk_output_file, index=False)


def process_and_save_chunk(
    df_queries_chunk,
    df_candidates_chunk,
    chunk_idx,
    query_id,
    candidate_id,
    query_column,
    candidate_column,
    output_path,
):
    candidate_links = block_candidates(
        df_queries_chunk, df_candidates_chunk, query_column, candidate_column
    )
    compare_and_save(
        df_queries_chunk,
        df_candidates_chunk,
        candidate_links,
        chunk_idx,
        query_id,
        candidate_id,
        query_column,
        candidate_column,
        output_path,
    )


def match_by_chunk(
    df_queries,
    df_candidates,
    query_id,
    candidate_id,
    query_column,
    candidate_column,
    chunk_by="candidates",
    chunk_size=1000,
    output_path=temp_data_path,
):
    """
    Perform chunked matching and save intermediate results immediately.

    Parameters:
    - chunk_by (str): 'queries' or 'candidates' to decide how to split chunks
    - chunk_size (int): number of rows per chunk
    - output_path (str): folder to save intermediate results
    """
    if chunk_by == "queries":
        chunks = np.array_split(
            df_queries, (len(df_queries) + chunk_size - 1) // chunk_size
        )
        args = [(chunk, df_candidates, idx) for idx, chunk in enumerate(chunks)]
    else:
        chunks = np.array_split(
            df_candidates, (len(df_candidates) + chunk_size - 1) // chunk_size
        )
        args = [(df_queries, chunk, idx) for idx, chunk in enumerate(chunks)]

    with tqdm_joblib(tqdm(desc="Processing chunks", total=len(chunks))) as pbar:
        Parallel(n_jobs=10)(
            delayed(process_and_save_chunk)(
                q_chunk,
                c_chunk,
                idx,
                query_id,
                candidate_id,
                query_column,
                candidate_column,
                output_path,
            )
            for q_chunk, c_chunk, idx in args
        )

    return len(chunks)


def concat_chunk_results(output_path, num_chunks):
    """
    Concatenate chunk results into a single DataFrame.
    """
    dfs = []
    for idx in range(num_chunks):
        df = pd.read_csv(
            f"{output_path}/matched_chunk_{idx}.csv",
            usecols=[
                query_id,
                candidate_id,
                query_column,
                candidate_column,
                "name_similarity",
                f"{query_column}_clean",
                f"{candidate_column}_clean",
            ],
        )
        dfs.append(df)
    result = pd.concat(dfs, ignore_index=True)
    result = result.sort_values("name_similarity", ascending=False).drop_duplicates(
        subset=query_id
    )
    return result


if __name__ == "__main__":

    # --------------------------------------------------------------------------------------------------------
    # round 1:use company name
    # --------------------------------------------------------------------------------------------------------
    revelio_usecols1 = ["rcid", "company"]
    # revelio = pd.read_csv(os.path.join(raw_data_path, "company_mapping.csv.gz"),nrows=1000,usecols=revelio_usecols1,compression='gzip')
    revelio = pd.read_csv(
        os.path.join(revelio_data_path, "company_mapping.csv.gz"),
        # nrows=1000, # for testing
        usecols=revelio_usecols1,
        compression="gzip",
    )
    revelio = revelio.drop_duplicates().dropna().reset_index(drop=True)

    audit_analysis = pd.read_stata(os.path.join(temp_data_path, "aa_population2.dta"))
    audit_analysis_usecols = ["auditor_fkey", "auditor_name"]
    audit_analysis = (
        audit_analysis[audit_analysis_usecols]
        .drop_duplicates()
        .dropna()
        .reset_index(drop=True)
    )

    df_queries = audit_analysis.copy()
    df_candidates = revelio.copy()
    del audit_analysis, revelio

    query_id = "auditor_fkey"
    candidate_id = "rcid"
    query_column = "auditor_name"
    candidate_column = "company"

    """
    clean data
    """
    # unify data type
    df_queries[[query_id]] = df_queries[[query_id]].astype(str)
    df_candidates[[candidate_id]] = df_candidates[[candidate_id]].astype(str)
    df_queries[[query_column]] = df_queries[[query_column]].astype(str)
    df_candidates[[candidate_column]] = df_candidates[[candidate_column]].astype(str)

    keywords_list = [
        "the ",
        " co",
        "cpa",
        "p a",
        "cpas",
        "associates",
        "consulting",
        "consultants",
        "advisors",
        "pa",
        "aac",
        " ac",
        "pllc",
        "company",
        "sc",
        " plc",
        " ps",
        " pl",
        "llcpc",
        " psc",
        " ca",
        " lc",
    ]

    # Apply cleaning function to query and candidate names
    df_queries[f"{query_column}_clean"] = clean_column(
        df_queries[query_column],
        keywords_list=keywords_list,
        keywords_dict=firm_dict,
        parallel=True,
    )

    df_candidates[f"{candidate_column}_clean"] = clean_column(
        df_candidates[candidate_column],
        keywords_list=keywords_list,
        keywords_dict=firm_dict,
        parallel=True,
    )

    # unify data starting with a space
    df_queries[f"{query_column}_clean"] = df_queries[
        f"{query_column}_clean"
    ].str.replace(r"^([A-Za-z]) ([A-Za-z]) ", r"\1\2 ", regex=True)
    df_candidates[f"{candidate_column}_clean"] = df_candidates[
        f"{candidate_column}_clean"
    ].str.replace(r"^([A-Za-z]) ([A-Za-z]) ", r"\1\2 ", regex=True)

    """
    build block
    """

    # extract middle name
    df_queries["middle_name"] = (
        df_queries[f"{query_column}_clean"]
        .str.extract(r"\b([A-Za-z])\b")
        .fillna("abcdefghijklmnopqrstuvwxyz")
    )
    df_candidates["middle_name"] = (
        df_candidates[f"{candidate_column}_clean"]
        .str.extract(r"\b([A-Za-z])\b")
        .fillna("abcdefghijklmnopqrstuvwxyz")
    )

    # extract first name
    df_queries["first_name"] = df_queries[f"{query_column}_clean"].str.split().str[0]
    df_candidates["first_name"] = (
        df_candidates[f"{candidate_column}_clean"].str.split().str[0]
    )

    # extract last name
    extracted = df_queries[f"{query_column}_clean"].str.extractall(r"(\b\w{2,}\b)")
    df_extracted = extracted.unstack()
    df_queries["last_name"] = df_extracted.iloc[:, 1].fillna("")

    extracted = df_candidates[f"{candidate_column}_clean"].str.extractall(
        r"(\b\w{2,}\b)"
    )
    df_extracted = extracted.unstack()
    df_candidates["last_name"] = df_extracted.iloc[:, 1].fillna("")

    """
    only use name similarity
    """
    # Perform matching by chunk
    num_chunks = match_by_chunk(
        df_queries,
        df_candidates,
        query_id=query_id,
        candidate_id=candidate_id,
        query_column=query_column,
        candidate_column=candidate_column,
        chunk_by="candidates",
    )

    # Combine matching results from chunks
    result = concat_chunk_results(temp_data_path, num_chunks)

    # Sort results by similarity score and remove duplicates
    result = result.sort_values("name_similarity", ascending=False).drop_duplicates(
        subset=candidate_id
    )
    result = result[result["name_similarity"] >= 0.9]
    result["match_round"] = 1
    result.to_csv(
        os.path.join(temp_data_path, "key_AA_revelio1.csv.gz"),
        index=False,
        compression="gzip",
    )

    # --------------------------------------------------------------------------------------------------------
    # round 2:use children name
    # --------------------------------------------------------------------------------------------------------
    result_round1 = pd.read_csv(
        os.path.join(temp_data_path, "key_AA_revelio1.csv.gz"),
        compression="gzip",
        usecols=[query_id, candidate_id],
    )

    filtered_query_id = set(result_round1[query_id])
    filtered_candidate_id = set(result_round1[candidate_id])

    revelio_usecols2 = ["rcid", "company", "child_company"]
    revelio = pd.read_csv(
        os.path.join(revelio_data_path, "company_mapping.csv.gz"),
        # nrows=1000, # for testing
        usecols=revelio_usecols2,
        compression="gzip",
    )
    revelio = revelio[
        ~revelio["company"].str.lower().eq(revelio["child_company"].str.lower())
    ].drop(columns=["company"], axis=1)
    revelio = revelio[~revelio["rcid"].isin(filtered_candidate_id)]

    audit_analysis = pd.read_stata(os.path.join(temp_data_path, "aa_population2.dta"))
    audit_analysis_usecols = ["auditor_fkey", "auditor_name"]
    audit_analysis = (
        audit_analysis[audit_analysis_usecols]
        .drop_duplicates()
        .dropna()
        .reset_index(drop=True)
    )
    audit_analysis = audit_analysis[
        ~audit_analysis["auditor_fkey"].isin(filtered_query_id)
    ]

    df_queries = audit_analysis.copy()
    df_candidates = revelio.copy()
    del audit_analysis, revelio

    query_id = "auditor_fkey"
    candidate_id = "rcid"
    query_column = "auditor_name"
    candidate_column = "child_company"

    """
    clean data
    """
    # unify data type
    df_queries[[query_id]] = df_queries[[query_id]].astype(int)
    df_candidates[[candidate_id]] = df_candidates[[candidate_id]].astype(int)
    df_queries[[query_column]] = df_queries[[query_column]].astype(str)
    df_candidates[[candidate_column]] = df_candidates[[candidate_column]].astype(str)

    # clean
    df_queries[f"{query_column}_clean"] = clean_column(
        df_queries[query_column],
        keywords_list=keywords_list,
        keywords_dict=firm_dict,
        parallel=True,
    )
    df_candidates[f"{candidate_column}_clean"] = clean_column(
        df_candidates[candidate_column],
        keywords_list=keywords_list,
        keywords_dict=firm_dict,
        parallel=True,
    )

    # unify data starting with a space
    df_queries[f"{query_column}_clean"] = df_queries[
        f"{query_column}_clean"
    ].str.replace(r"^([A-Za-z]) ([A-Za-z]) ", r"\1\2 ", regex=True)
    df_candidates[f"{candidate_column}_clean"] = df_candidates[
        f"{candidate_column}_clean"
    ].str.replace(r"^([A-Za-z]) ([A-Za-z]) ", r"\1\2 ", regex=True)

    # extract middle name
    df_queries["middle_name"] = (
        df_queries[f"{query_column}_clean"]
        .str.extract(r"\b([A-Za-z])\b")
        .fillna("abcdefghijklmnopqrstuvwxyz")
    )
    df_candidates["middle_name"] = (
        df_candidates[f"{candidate_column}_clean"]
        .str.extract(r"\b([A-Za-z])\b")
        .fillna("abcdefghijklmnopqrstuvwxyz")
    )

    # extract first name
    df_queries["first_name"] = df_queries[f"{query_column}_clean"].str.split().str[0]
    df_candidates["first_name"] = (
        df_candidates[f"{candidate_column}_clean"].str.split().str[0]
    )

    # extract last name
    extracted = df_queries[f"{query_column}_clean"].str.extractall(r"(\b\w{2,}\b)")
    df_extracted = extracted.unstack()
    df_queries["last_name"] = df_extracted.iloc[:, 1].fillna("")

    extracted = df_candidates[f"{candidate_column}_clean"].str.extractall(
        r"(\b\w{2,}\b)"
    )
    df_extracted = extracted.unstack()
    df_candidates["last_name"] = df_extracted.iloc[:, 1].fillna("")

    """
    only use name similarity
    """
    # Perform matching by chunk
    num_chunks = match_by_chunk(
        df_queries,
        df_candidates,
        query_id=query_id,
        candidate_id=candidate_id,
        query_column=query_column,
        candidate_column=candidate_column,
        chunk_by="candidates",
    )

    # Combine matching results from chunks
    result = concat_chunk_results(temp_data_path, num_chunks)

    # Sort results by similarity score and remove duplicates
    result = result.sort_values("name_similarity", ascending=False).drop_duplicates(
        subset=candidate_id
    )
    result = result[result["name_similarity"] >= 0.9]
    result["match_round"] = 2
    result.to_csv(
        os.path.join(temp_data_path, "key_AA_revelio2.csv.gz"),
        index=False,
        compression="gzip",
    )

    """
    concat results
    
    """
    result1 = pd.read_csv(os.path.join(temp_data_path, "key_AA_revelio1.csv.gz"))
    result2 = pd.read_csv(os.path.join(temp_data_path, "key_AA_revelio2.csv.gz"))
    result = pd.concat([result1, result2], ignore_index=True)
    result = result.sort_values("name_similarity", ascending=False).drop_duplicates(
        subset="auditor_fkey"
    )
    result.to_csv(
        os.path.join(temp_data_path, "key_AA_revelio.csv.gz"),
        index=False,
        compression="gzip",
    )

    key = pd.read_csv(os.path.join(temp_data_path, "key_AA_revelio.csv"))


# from config import output_data_path
# panel = pd.read_stata(os.path.join(output_data_path, 'panel_firm_year_2.dta'))
# panel = panel.merge(key, how='inner', on='auditor_fkey')
