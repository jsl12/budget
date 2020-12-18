import logging
from pathlib import Path
from typing import Dict

import pandas as pd

from .df import load_csv

logger = logging.getLogger(__name__)

class CSVLoader:
    """Handles loading CSV files to produce a standardized :class:`~pandas.DataFrame` with the columns ``Description``
    and ``Amount`` and a :class:`~pandas.DatetimeIndex` named ``Date``

    Parameters
    ----------
    accounts_cfg : :class:`dict`
        dict with a key for each account
    base_path : :class:`str` or :class:`pathlib.Path`
        path to the folder that contains folders for each account. The names of the folders need to match the names of
        the account keys
    """
    def __init__(self, accounts_cfg: Dict, base_path: Path):
        self.cfg = accounts_cfg.copy()
        self.base_path = base_path if isinstance(base_path, Path) else Path(base_path)
        self.validate_cfg()

    def validate_cfg(self):
        """Validates the configuration `dict` by asserting that it has ``date``, ``desc``, ``amount`` sub-keys if it
        has a ``columns`` key
        """
        for key, value in self.cfg.items():
            if value is None:
                self.cfg[key] = {}
                value = self.cfg[key]

            if 'columns' in value:
                assert 'date' in value['columns']
                assert 'desc' in value['columns']
                assert 'amount' in value['columns']
                assert all([isinstance(v, int) for v in value['columns'].values()])
        return True

    def load_all_accounts(self) -> pd.DataFrame:
        """Loads all accounts into a single :class:`~pandas.DataFrame` using :meth:`~budget.load.CSVLoader.load_account`

        Returns
        -------
        :class:`~pandas.DataFrame`
            A :class:`~pandas.DataFrame` of all the transactions from all the accounts, sorted by index
        """
        def load(name: str):
            nonlocal self
            logger.info(f' {name} '.center(75, '-'))
            return self.load_account(name)
        df = pd.concat([load(account) for account in self.cfg.keys()]).sort_index()
        return df

    def load_account(self, name: str) -> pd.DataFrame:
        """Uses :func:`~budget.load.load_csv` to load the transaction data for a single account based on its name

        Parameters
        ----------
        name : :class:`str`
            name of the account to load as it appears in ``yaml`` -> ``Loading`` -> ``Accounts``

        Returns
        -------
        :class:`~pandas.DataFrame`
            :class:`~pandas.DataFrame` of all transactions of a given account ``Description``, ``Amount``, ``Date``, and
            ``Account`` columns
        """
        cfg = self.cfg[name]
        folder = (self.base_path / name)
        files = [f for f in folder.glob('*.csv')]

        logger.info(f'Loading {len(files)} files')
        try:
            df = pd.concat([
                load_csv(
                    path=f,
                    header=cfg.get('header', 'infer'),
                    skiprows=cfg.get('skiprows', None),
                    columns=cfg.get('columns', None)
                )
                for f in files
            ])
        except ValueError:
            raise ValueError(f'No csv files found in {folder}')

        raw_size = df.shape[0]
        df = df[~df['id'].duplicated(keep='first')].sort_index()
        logger.info(f'{df.shape[0]} unique transactions, {raw_size-df.shape[0]} duplicates')
        df['Account'] = name
        return df
