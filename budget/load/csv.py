import logging
import re
from pathlib import Path
from typing import Dict

import pandas as pd

from ..processing import sum_duplicates
from ..utils import hash

logger = logging.getLogger(__name__)

class CSVLoader:
    """
    Handles loading CSV files to produce a standardized DataFrame with the columns 'Description' and 'Amount' and a pd.DatetimeIndex named 'Date'
    """
    def __init__(self, accounts_cfg: Dict, base_path: Path):
        self.cfg = accounts_cfg.copy()
        self.base_path = base_path if isinstance(base_path, Path) else Path(base_path)
        self.validate_cfg()

    def validate_cfg(self):
        for key, value in self.cfg.items():
            if value is None:
                self.cfg[key] = {}
                value = self.cfg[key]

            if 'columns' in value:
                assert 'date' in value['columns']
                assert 'desc' in value['columns']
                assert 'amount' in value['columns']
                assert all([isinstance(v, int) for v in value['columns'].values()])

    def load_all_accounts(self) -> pd.DataFrame:
        def load(name: str):
            nonlocal self
            logger.info(f' {name} '.center(75, '-'))
            return self.load_account(name)
        df = pd.concat([load(account) for account in self.cfg.keys()]).sort_index()
        return df

    def load_account(self, name: str) -> pd.DataFrame:
        cfg = self.cfg[name]
        folder = (self.base_path / name)
        files = [f for f in folder.glob('*.csv')]

        logger.info(f'Loading {len(files)} files')
        try:
            df = pd.concat([load_csv(path=f, **cfg) for f in files])
        except ValueError:
            raise ValueError(f'No csv files found in {folder}')

        raw_size = df.shape[0]
        df = df[~df['id'].duplicated(keep='first')].sort_index()
        logger.info(f'{df.shape[0]} unique transactions, {raw_size-df.shape[0]} duplicates')
        df['Account'] = name
        return df

def load_csv(path: Path, **kwargs) -> pd.DataFrame:
    arg_list = [
        'header',
        'skiprows'
    ]
    read_csv_args = {a: kwargs[a] for a in arg_list if a in kwargs}

    try:
        df = pd.read_csv(path, **read_csv_args)
    except pd.errors.ParserError:
        raise pd.errors.ParserError(f'Error parsing {path.name}')
    else:
        logger.info(f'Successfully parsed {path.name}')

    if 'columns' in kwargs:
        col_date = kwargs['columns']['date']
        col_desc = kwargs['columns']['desc']
        col_amt = kwargs['columns']['amount']
    else:
        col_date = None
        col_desc = None
        col_amt = None

    res = pd.DataFrame(
        data={
            'Description': find_desc(df, col_desc),
            'Amount': find_amounts(df, col_amt)
        },
        index=pd.Index(
            data=find_dates(df, col_date),
            name='Date'
        )
    )

    res = sum_duplicates(res)
    logger.info(f'Hashing {res.shape[0]} transactions')
    res['id'] = res.apply(hash, axis=1)
    res = res.sort_index()
    return res


def find_dates(df: pd.DataFrame, col_num: int = None) -> pd.Series:
    if col_num is None:
        raw_vals = df.filter(regex=re.compile('date', re.IGNORECASE)).iloc[:, 0]
    else:
        raw_vals = df.iloc[:, col_num]
    return pd.to_datetime(raw_vals).values


def find_amounts(df: pd.DataFrame, col_num: int = None) -> pd.Series:
    if col_num is None:
        return df.select_dtypes('number').iloc[:,0].values
    else:
        return df.iloc[:, col_num].values


def find_desc(df: pd.DataFrame, col_num: int = None) -> pd.Series:
    if col_num is None:
        return df[df.select_dtypes('object').applymap(lambda v: len(str(v))).max().idxmax()].values
    else:
        return df.iloc[:, col_num].values
