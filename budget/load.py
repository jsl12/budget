import hashlib
import logging
import re
from pathlib import Path

import pandas as pd
import yaml
LOGGER = logging.getLogger(__name__)


def load_from_cfg_path(config_path: Path) -> pd.DataFrame:
    with Path(config_path).open('r') as file:
        cfg = yaml.load(file, Loader=yaml.SafeLoader)
        return load_all_accounts(cfg['Loading']['Accounts'], Path(cfg['Loading']['base']))


def load_all_accounts(cfg, base: Path):
    return pd.concat(account_df_gen(cfg, base)).drop_duplicates('id').sort_index()


def account_df_gen(cfg, base: Path):
    for name, account_cfg in cfg.items():
        loader_name = account_cfg['loader']
        for f in (base / name).glob('*.csv'):
            df = globals()[loader_name](f)
            df['Account'] = name
            yield df


def load_transaction_file(filepath: Path, **kwargs) -> pd.DataFrame:
    LOGGER.debug(f'Loading from: {filepath.name}')
    df = pd.read_csv(filepath, **kwargs)

    date_col = df.filter(regex=re.compile('date', re.IGNORECASE)).columns[0]
    amt_col = df.select_dtypes('number').dropna(axis=1, how='all').columns[0]
    desc_col = df.select_dtypes('object').applymap(lambda v: len(str(v))).max().idxmax()

    df = df[[date_col, amt_col, desc_col]].set_index(date_col)
    df.columns = ['Amount', 'Description']
    df.index.name = 'Date'
    df.index = pd.to_datetime(df.index)

    df = (
        df
            .reset_index()
            .groupby(['Date', 'Amount', 'Description'])
            .sum()
            .reset_index()
            .set_index('Date')
    )
    df = df[['Amount', 'Description']]
    df['id'] = df.apply(hash, axis=1)

    return df.sort_index()


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


def load_chase(filepath: Path) -> pd.DataFrame:
    return load_transaction_file(filepath)


def load_barclays(filepath: Path) -> pd.DataFrame:
    return load_transaction_file(filepath, header='infer', skiprows=4)


def load_wells_fargo(filepath: Path) -> pd.DataFrame:
    return load_transaction_file(filepath, names=['date', 'amount', '', 'comment', 'desc'])
