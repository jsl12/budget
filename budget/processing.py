from typing import Dict, Union
import pandas as pd
import numpy as np
from . import utils


def flatten_mask_tree(mask_tree: Dict[str, Union[Dict, str]]) -> Dict[str, pd.Series]:
    '''
    Walks through the mask_tree using recursive_items() and builds a resultant dictionary by summarizing the portion of
    the tree below each node.

    Essentially used to pre-process the tree so that any key can be used to immediately retrieve the correct selection mask

    :param mask_tree: nested dictionary of boolean Series objects
    :return: dictionary of selection masks
    '''

    return {key: summarize(value) for key, value in utils.recursive_items(mask_tree)}


def gen_mask_tree(df: pd.DataFrame, cats: Dict[str, Union[Dict, str]]) -> Dict[str, Union[Dict, str]]:
    '''
    Walks through the nested dictionary of categories and calls proc_query on all the leaves.
    Keeps track of what's already been matched with the already_matched_mask variable

    :param df: DataFrame object of transaction history
    :param cats: nested dictionary of categories (queries) to match the transaction history against
    :return: nested dictionary of boolean Series objects
    '''
    already_matched_mask = pd.Series(np.full(len(df.index), False), index=df.index).astype(bool)
    def match_transactions(query):
        nonlocal already_matched_mask
        raw_match_mask = proc_query(df, query)
        matches = raw_match_mask & (~already_matched_mask)
        already_matched_mask |= matches
        return matches
    return utils.apply_func(cats, match_transactions)


def proc_query(df, query):
    """
    Looks for a query in a DataFrame and returns a boolean Series for selection

    query can be a string or a list of strings. Lists of strings get logically ANDed together
    """

    assert isinstance(df, pd.DataFrame)

    if isinstance(query, list):
        query = ''.join(['(?=.*{})'.format(q) for q in query])
    return df.filter(regex='(?i).*desc').iloc[:, 0].str.contains(query, case=False)


def summarize(mask_tree):
    '''
    Logically ORs all the boolean Series objects in the nested dictionary tree

    :param mask_tree: nested dictionary of boolean Series objects
    :return: boolean Series
    '''
    ref = utils.first_item(mask_tree)
    sel = pd.Series(np.full(len(ref.index), False), index=ref.index).astype(bool)

    def add_to_sel(mask):
        nonlocal sel
        sel |= mask
    utils.apply_func(mask_tree, add_to_sel)
    return sel


def sum_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    '''
    Combine duplicate rows in the DataFrame by summing the columns that are numbers

    :param df: pandas DataFrame to search for combined duplicates
    :return: modified pandas DataFrame
    '''

    # Turn the index into a column so it can be considered for calculating the duplicates
    index_name = df.index.name
    df = df.reset_index()

    dups = df[df.duplicated(keep=False)]

    unique_dups = dups.drop_duplicates(keep='first')

    # need the copy here to prevent hidden chaining
    # https://www.dataquest.io/blog/settingwithcopywarning/
    res = df.drop_duplicates(keep='first').copy()
    for i, row in unique_dups.iterrows():
        vals = dups[dups == row].sum()
        res.loc[i, vals.index] = vals

    res = res.set_index(index_name).sort_index()
    return res
