import logging
from pathlib import Path
from typing import Dict

import pandas as pd

from .columns import find_desc, find_amounts, find_dates
from ..processing import sum_duplicates
from ..utils import hash

LOGGER = logging.getLogger(__name__)

def load_csv(path: Path, header: str = 'infer', skiprows: int = None, columns: Dict[str, int] = None) -> pd.DataFrame:
    """Load a CSV file using keyword arguments to account for variations between formats, based around
    :func:`~pandas.read_csv`
        - :func:`~budget.load.columns.find_desc`
        - :func:`~budget.load.columns.find_amounts`
        - :func:`~budget.load.columns.find_dates`

    Parameters
    ----------
    path : :class:`str`, :class:`pathlib.Path`
        path of the CSV file to be loaded
    header : :class:`int`, :class:`list` of :class:`int`, default ‘infer’
        Row number(s) to use as the column names, and the start of the data.
    columns :
        `Dict` of column numbers to use. Needs ``desc``, ``amount``, and ``date`` keys with `int` values

    Returns
    -------
    :class:`~pandas.DataFrame`
        :class:`~pandas.DataFrame` of loaded transactions with columns ``Description``, ``Amount``, a
        :class:`~pandas.DatetimeIndex` named ``Date``
    """
    try:
        df = pd.read_csv(path, header=header, skiprows=skiprows)
    except pd.errors.ParserError:
        raise pd.errors.ParserError(f'Error parsing {path.name}')
    else:
        LOGGER.info(f'Successfully parsed {path.name}')

    if columns is None:
        columns = {}

    res = pd.DataFrame(
        data={
            'Description': find_desc(
                df,
                col_num=columns.get('desc', None)
            ),
            'Amount': find_amounts(
                df,
                col_num=columns.get('amount', None)
            )
        },
        index=pd.Index(
            data=find_dates(
                df,
                col_num=columns.get('date', None)
            ),
            name='Date'
        )
    )

    res = sum_duplicates(res)
    LOGGER.info(f'Hashing {res.shape[0]} transactions')
    res['id'] = res.apply(hash, axis=1)
    res = res.sort_index()
    return res
