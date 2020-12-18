import hashlib
from typing import Union, List, Dict, Callable
from datetime import timedelta
import pandas as pd


def report(df: pd.DataFrame,
           avg: int = None,
           freq: str = None,
           origin: str = 'start_day',
           offset: Union[str, timedelta] = None,
           ) -> pd.DataFrame:
    """Used to summarize transaction data by optionally grouping by date interval and applying moving averages

    .. _freq: https://pandas.pydata.org/pandas-docs/stable/user_guide/timeseries.html#timeseries-offset-aliases

    :class:`~pandas.Grouper`

    Parameters
    ----------
    df : :class:`~pandas.DataFrame`
        Starting transaction data
    avg : :class:`int`
        :meth:`~pandas.DataFrame.rolling`
    freq : :class:`str`
        `freq`_ string
    origin : :class:`str`
    offset : :class:`~datetime.timedelta` or :class:`str`


    Returns
    -------
    :class:`~pandas.DataFrame`
        Summarized transaction data
    """
    if freq is not None:
        try:
            df = df.groupby(pd.Grouper(freq=freq,
                                       origin=origin,
                                       offset=offset
                                       )).sum()
        except ValueError:
            raise ValueError(f'Invalid frequency: {freq}')

    if avg is not None:
        try:
            df = df.rolling(avg).mean()
        except ValueError:
            raise ValueError(f'invalid avg period: {avg}')

    df = df.sort_index(ascending=False).applymap(lambda v: round(v, 2))

    return df


def first_item(obj):
    if isinstance(obj, list):
        return first_item(obj[0])
    elif isinstance(obj, dict):
        return first_item(next(iter(obj.values())))
    else:
        return obj


def recursive_items(nested_dicts: Dict[object, Dict]):
    """Generator that yields values recursively from a set of nested `dicts`. Will also yield from `dicts` contained in
    lists

    `StackOverflow reference <https://stackoverflow.com/a/39234154>`_

    Parameters
    ----------
    nested_dicts : :class:`dict`


    Yields
    ------
    obj
        values from the nested :class:`dict`
    """
    for key, value in nested_dicts.items():
        yield (key, value)
        if isinstance(value, dict):
            yield (key, value)
            yield from recursive_items(value)
        elif isinstance(value, list) and any([isinstance(item, dict) for item in value]):
            for item in value:
                if isinstance(item, dict):
                    yield from recursive_items(item)


def apply_func(obj: Union[List, Dict], func: Callable):
    """Recursively iterates through a nested :class:`dict` calling a function on each item. Also works for a :class:`list` of nested `dicts`\n
    `StackOverflow reference <https://stackoverflow.com/a/32935278>`_

    Parameters
    ----------
    obj : Union[List, Dict]
        nested :class:`dict` or :class:`list` of nested `dicts`
    func :
        callable function to call with each item in the nested collection

    Returns
    -------
    :class:`dict` or :class:`list`
        object returned will have the same structure as the original `obj`
    """

    def comp_helper(x):
        if isinstance(x, dict):
            return apply_func(x, func)
        else:
            return func(x)

    if isinstance(obj, dict):
        return {key: apply_func(value, func) for key, value in obj.items()}
    elif isinstance(obj, list):
        # The obj is a list and there's a dictionary in there somewhere
        return [comp_helper(item) for item in obj]
    else:
        return func(obj)


def hash(row: pd.Series) -> str:
    """Uses the builtin :mod:`hashlib` to make a `md5` hash object, which is then updated with the transaction date
    (:class:`str` in ``%Y-%m-%d`` format), ``Description`` and ``Amount`` values. Used to uniquely identify transactions

    Parameters
    ----------
    row : :class:`~pandas.Series`
        row from the transaction :class:`~pandas.DataFrame`. The :class:`~pandas.DataFrame` needs to have a
        :class:`~pandas.DatetimeIndex` and ``Description`` and ``Amount`` columns

    Returns
    -------
    str : :meth:`hashlib.hash.hexdigest`
    """
    m = hashlib.md5()
    m.update(bytes(row.name.strftime('%Y-%m-%d'), encoding='UTF-8', errors='strict'))
    m.update(bytes(row['Description'], encoding='UTF-8', errors='strict'))
    m.update(bytes(int(row['Amount'] * 100).to_bytes(24, byteorder='big', signed=True)))
    return m.hexdigest()
