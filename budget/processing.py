from typing import Dict, Union, List

import numpy as np
import pandas as pd

from . import utils


def flatten_mask_tree(mask_tree: Dict[str, Union[Dict, str]]) -> Dict[str, pd.Series]:
    """Walks through the mask_tree using :func:`~budget.utils.recursive_items` and builds a resultant dictionary by summarizing the portion
    of the tree below each node using :func:`~budget.utils.summarize`

    Essentially used to pre-process the tree so that any key can be used to immediately retrieve the correct selection
    mask

    Parameters
    ----------
    mask_tree : :class:`dict`
        nested :class:`dict` of :class:`~pandas.Series` with :class:`bool` `dtype`. :class:`Dict` keys must by unique

    Returns
    -------
    dict
        flattened :class:`dict` of :class:`~pandas.Series` with :class:`bool` `dtype`
    """

    return {key: summarize(value) for key, value in utils.recursive_items(mask_tree)}


def gen_mask_tree(df: pd.DataFrame, cats: Dict[str, Union[Dict, str]]) -> Dict[str, Union[Dict, str]]:
    """Walks through the nested dictionary of categories, using :func:`~budget.utils.apply_func`
    and calls :func:`~budget.processing.proc_query` on all the leaves.

    Parameters
    ----------
        df : :class:`~pandas.DataFrame`
            :class:`~pandas.DataFrame` of transaction history
        cats : :class:`dict`
            nested :class:`dict` of categories (queries) to match the transaction history against

    Returns
    -------
    :class:`dict`
        nested :class:`dict` of :class:`~pandas.Series` with :class:`bool` `dtype`

    """

    # keeps track of what's already been matched with already_matched_mask
    already_matched_mask = pd.Series(np.full(df.shape[0], False), index=df.index).astype(bool)
    def match_transactions(query):
        nonlocal already_matched_mask
        raw_match_mask = proc_query(df, query)
        matches = raw_match_mask & (~already_matched_mask)
        already_matched_mask |= matches
        return matches
    return utils.apply_func(cats, match_transactions)


def proc_query(df: pd.DataFrame, query: Union[str, List[str]]) -> pd.Series:
    """Looks for a query in a :class:`~pandas.DataFrame` and returns a boolean :class:`~pandas.Series` for selection
    \n
    query can be a string or a list of strings. Lists of strings get logically ``AND`` together

    Parameters
    ----------
    df : :class:`~pandas.DataFrame`
        `DataFrame` of transactions. Must have a column that matches regex ``(?i).*desc``
    query : str or List[str]
        string to search for using :class:`~pandas.Series.str.contains` `(case=False)`, results from multiple strings get combined
        with logical ``AND``

    Returns
    -------
    :class:`~pandas.Series`
        :class:`~pandas.Series` with :class:`bool` `dtype` indicating whether each transaction matches the query
    """

    assert isinstance(df, pd.DataFrame)

    if isinstance(query, list):
        query = ''.join(['(?=.*{})'.format(q) for q in query])
    return df.filter(regex='(?i).*desc').iloc[:, 0].str.contains(query, case=False)


def summarize(mask_tree: Dict[str, Union[Dict, pd.Series]]) -> pd.Series:
    """Uses :func:`~budget.utils.apply_func` to walk the tree of nested :class:`dict`, using logical ``OR`` to combine every
    :class:`~pandas.Series`

    Parameters
    ----------
    mask_tree : nested :class:`dict` with :class:`str` keys and :class:`~pandas.Series` values
        Tree of nested :class:`dict`, keys

    Returns
    -------
    :class:`~pandas.Series`
        :class:`~pandas.Series` with :class:`bool` `dtype`
    """

    ref = utils.first_item(mask_tree)
    sel = pd.Series(np.full(len(ref.index), False), index=ref.index).astype(bool)

    def add_to_sel(mask):
        nonlocal sel
        sel |= mask
    utils.apply_func(mask_tree, add_to_sel)
    return sel


def sum_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """Combine duplicate rows in the DataFrame by summing numeric columns. Values are set using
    :meth:`~pandas.DataFrame.loc` with the indices of duplicates, which are found using
    :meth:`~pandas.DataFrame.drop_duplicates` with `(keep='first')`

    Parameters
    ----------
    df : :class:`~pandas.DataFrame`
        :class:`~pandas.DataFrame` of transactions

    Returns
    -------
    :class:`~pandas.DataFrame`
        modified :class:`~pandas.DataFrame`
    """

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
