import logging
import re
from pathlib import Path
from typing import Dict

import pandas as pd

from ..processing import sum_duplicates
from ..utils import hash


class Loader:
    def __init__(self, accounts_cfg: Dict):
        self.cfg = accounts_cfg.copy()
        self.validate_cfg()
        self.logger = logging.getLogger(__name__)

    def debug(self, *args, **kwargs):
        self.logger.debug(*args, **kwargs)

    def info(self, *args, **kwargs):
        self.logger.info(*args, **kwargs)

    def validate_cfg(self):
        for key, value in self.cfg.items():
            assert 'folder' in value
            if 'columns' in value:
                assert 'date' in value['columns']
                assert 'desc' in value['columns']
                assert 'amount' in value['columns']
                assert all([isinstance(v, int) for v in value['columns'].values()])

    def load_all_accounts(self):
        def load(name, cfg):
            self.debug(f' {name} '.center(75, '-'))
            return self.load_account(cfg, name)
        df = pd.concat([load(*items) for items in self.cfg.items()]).sort_index()
        return df

    def load_account(self, cfg: Dict, name: str):
        files = [f for f in Path(cfg.pop('folder')).glob('*.csv')]

        while True:
        # try to filter with the file regex
            try:
                rgx = re.compile(cfg['file regex'], re.IGNORECASE)
                files = [f for f in files if rgx.search(f.name)]
            except TypeError:
                cfg['file regex'] = ''.join([f'.*(?={s})' for s in cfg['file regex']])
            except KeyError:
                break
            else:
                cfg.pop('file regex')
                break

        self.debug(f'Loading {len(files)} files')
        df = pd.concat([self.load_csv(path=f, **cfg) for f in files])

        raw_size = df.shape[0]
        df = df[~df['id'].duplicated(keep='first')].sort_index()
        self.debug(f'{df.shape[0]} unique transactions, {raw_size-df.shape[0]} duplicates')
        df['Account'] = name
        return df

    def load_csv(self, path: Path, **kwargs):
        kwargs = kwargs.copy()
        columns = kwargs.pop('columns', None)

        try:
            df = pd.read_csv(path, **kwargs)
        except pd.errors.ParserError:
            raise pd.errors.ParserError(f'Error parsing {path.name}')
        else:
            self.debug(f'Successfully parsed {path.name}')

        res = pd.DataFrame(
            data={
                'Description': self.find_desc(df, columns),
                'Amount': self.find_amounts(df, columns)
            },
            index=pd.Index(
                data=self.find_dates(df, columns),
                name='Date'
            )
        )

        res = sum_duplicates(res)
        self.debug(f'Hashing {res.shape[0]} transactions')
        res['id'] = res.apply(hash, axis=1)
        return res

    def find_dates(self, df: pd.DataFrame, cols: Dict = None):
        if cols is None:
            raw_vals = df.filter(regex=re.compile('date', re.IGNORECASE)).iloc[:, 0]
        else:
            raw_vals = df.iloc[:, cols['date']]
        return pd.to_datetime(raw_vals).values

    def find_amounts(self, df: pd.DataFrame, cols: Dict = None):
        if cols is None:
            return df.select_dtypes('number').iloc[:,0].values
        else:
            return df.iloc[:, cols['amount']].values

    def find_desc(self, df: pd.DataFrame, cols: Dict = None):
        if cols is None:
            return df[df.select_dtypes('object').applymap(lambda v: len(str(v))).max().idxmax()].values
        else:
            return df.iloc[:, cols['desc']].values
