import re

import numpy as np
import pandas as pd


def find_dates(df: pd.DataFrame, col_num: int = None) -> np.ndarray:
    """Finds the date column by searching for ``date`` in the column names, ignoring case, using
    :pandas_api:`filter<pandas.DataFrame.filter>`, uses :pandas_api:`to_datetime<pandas.to_datetime>` to parse

    Parameters
    ----------
    df : :class:`~pandas.DataFrame`
        raw `DataFrame` loaded from a CSV
    col_num : :class:`int`, optional
        optionally specify the column

    Returns
    -------
    :class:`~numpy.ndarray` `datetime64[ns]`
        an array of the transaction `datetimes`
    """
    if col_num is None:
        raw_vals = df.filter(regex=re.compile('date', re.IGNORECASE)).iloc[:, 0]
    else:
        raw_vals = df.iloc[:, col_num]
    return pd.to_datetime(raw_vals).values


def find_amounts(df: pd.DataFrame, col_num: int = None) -> np.ndarray:
    """Finds the ``amount`` column by selecting the first column with a numeric `dtype`
    :meth:`~pandas.DataFrame.select_dtypes`

    Parameters
    ----------
    df : :class:`~pandas.DataFrame`
        raw :class:`~pandas.DataFrame` loaded from a CSV
    col_num : :class:`int`, optional
        optionally specify the column

    Returns
    -------
    :class:`~numpy.ndarray` `float`
        an array of the transaction amounts
    """
    if col_num is None:
        return df.select_dtypes('number').iloc[:,0].values
    else:
        return df.iloc[:, col_num].values


def find_desc(df: pd.DataFrame, col_num: int = None) -> np.ndarray:
    """Finds the ``description`` column by taking the column with the longest string in it

        Parameters
        ----------
        df : :class:`~pandas.DataFrame`
            raw :class:`~pandas.DataFrame` loaded from a CSV
        col_num : :class:`int`, optional
            optionally specify the column

        Returns
        -------
        :class:`~numpy.ndarray` `float`
            an array of the transaction descriptions
        """
    if col_num is None:
        return df[df.select_dtypes('object').applymap(lambda v: len(str(v))).max().idxmax()].values
    else:
        return df.iloc[:, col_num].values
