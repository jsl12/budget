import pandas as pd
import warnings
import sqlite3
import re
import logging
from pathlib import Path
import yaml
from . import processing
from .notes import NoteManager
from .utils import hash
from .load import Loader
from functools import reduce
from typing import List

class BudgetData:
    SQL_DF_TABLE = 'transactions'
    SQL_SEL_TABLE = 'selections'
    DF_DATE_COL = 'Date'

    def __eq__(self, other):
        if isinstance(other, str):
            return self.search(other)
        else:
            return self.amounts == other

    def __ne__(self, other):
        if isinstance(other, str):
            return ~self.search(other)
        else:
            return self.amounts != other

    def __gt__(self, other):
        return self.amounts > other

    def __ge__(self, other):
        return self.amounts >= other

    def __lt__(self, other):
        return self.amounts < other

    def __le__(self, other):
        return self.amounts <= other

    def __getitem__(self, input):
        # Try to slice the transactions using the input
        # Allows slicing with date strings and boolean masks
        try:
            return self.render(self._df[input])
        except KeyError:
            # No big deal if it doesn't work
            pass

        # Try selecting based on a category name
        try:
            res = self._df[self._sel[input]]
        except KeyError:
            pass
        else:
            return self.render(res, input)

        # Try selecting using absolute value position
        try:
            return self.render(self._df.iloc[input])
        except IndexError:
            pass

        raise TypeError(f'Invalid selection: {type(input)}: {input}')

    def __init__(self, yaml_path: str):
        self.yaml_path = Path(yaml_path)
        self.note_manager = NoteManager()
        self.logger = logging.getLogger(__name__)

    def debug(self, *args, **kwargs):
        self.logger.debug(*args, **kwargs)

    def info(self, *args, **kwargs):
        self.logger.info(*args, **kwargs)

    @property
    def cfg(self):
        with self.yaml_path.open('r') as file:
            return yaml.load(file, Loader=yaml.SafeLoader)

    @property
    def categories(self):
        return self.cfg['Categories']

    @property
    def df(self):
        if not hasattr(self, '_df'):
            self.load_sql()
        if 'id' in self._df.columns:
            return self._df.drop('id', axis=1).fillna('')
        else:
            return self._df.fillna('')

    @property
    def id(self):
        return self._df['id']

    @property
    def amounts(self):
        # there should only be 1 column with numbers, the amounts column. This abstraction removes the dependence on the column name
        return self.df.select_dtypes('number').iloc[:, 0]

    @property
    def unselected(self):
        return ~self._sel.any(axis=1)

    @property
    def notes(self):
        return self.note_manager.notes.map(lambda n: n.note)

    @property
    def _notes(self):
        return self.note_manager.notes

    @property
    def db_path(self):
        return Path(self.cfg['Loading']['db'])

    def hash_transactions(self, df: pd.DataFrame = None) -> pd.DataFrame:
        if df is None:
            df = self._df
        df['id'] = df.apply(hash, axis=1)
        return df

    def load_csv(self):
        self.debug(f'Loading CSV files from {self.yaml_path.name}')
        self._df = Loader(self.cfg['Loading']['Accounts']).load_all_accounts()

    def process_categories(self):
        self.debug(f'Processing selections as defined in {self.yaml_path.name}')
        # Warnings need to be filtered out because there's groups in the regex matching down in there
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self._sel = pd.DataFrame(
                processing.flatten_mask_tree(
                    processing.gen_mask_tree(
                        df=self.df,
                        cats=self.categories
                    )
                )
            )
        self.debug('Done')

    def sql_context(self, path=None):
        if path is None:
            path = self.db_path
        return sqlite3.connect(path)

    def save_sql(self, path=None):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            with self.sql_context(path) as con:
                self._df.to_sql(name=self.SQL_DF_TABLE, con=con, if_exists='replace')
                self._sel.to_sql(name=self.SQL_SEL_TABLE, con=con, if_exists='replace')
                self.note_manager.save_notes(con)

    def load_sql(self, path=None, notes=True):
        with self.sql_context(path) as con:
            kwargs = {
                'con': con,
                'index_col': self.DF_DATE_COL,
                'parse_dates': self.DF_DATE_COL
            }
            self._df = pd.read_sql_query(sql=f'select * from {self.SQL_DF_TABLE}', **kwargs)
            self._sel = pd.read_sql_query(sql=f'select * from {self.SQL_SEL_TABLE}', **kwargs) == 1
            # the '== 1' is necessary because the DataFrame comes in as 0s and 1s instead of Booleans

            if notes:
                self.note_manager.load_notes(con)

    def update_sql(self):
        '''
        Loads fresh data from CSVs based on the yaml file, processes the yaml categories, and saves everything to the SQL database
        '''
        # need to load the SQL database first to get the notes
        with self.sql_context() as con:
            self.note_manager.load_notes(con)
        self.load_csv()
        self.process_categories()
        self.save_sql()

    def search(self, query: str) -> pd.Series:
        search_col = self.df.filter(regex=re.compile('desc', re.IGNORECASE)).columns[0]

        if isinstance(query, list):
            assert all([isinstance(q, str) for q in query]), 'query must be all strings'
            query = '.*'.join([f'(?={q})' for q in query])

        if isinstance(query, str):
            return self.df[search_col].str.contains(query, case=False)
        else:
            try:
                return self.df[search_col].str.contains(query)
            except Exception as e:
                raise TypeError(f'{query} couldn\'t be passed to pd.Series.str.contains()')

    def search_multiple(self, queries: List[str]) -> pd.Series:
        return reduce(lambda a,b: a | b, [self.search(query) for query in queries])

    def search_notes(self, input) -> pd.DataFrame:
        if isinstance(input, str):
            rgx = re.compile(input, re.IGNORECASE)
            return self.df[self.id.isin([n.id for n in self._notes.values if rgx.search(n.note)])]
        elif isinstance(input, type):
            return self.df[self.id.isin([n.id for n in self.note_manager.get_notes_by_type(input)])]
        else:
            raise TypeError(f'invalid input for BudgetData.search_notes(): {input}')

    def report(self, selections, timing: str = None, avg_periods: int = None) -> pd.DataFrame:
        if isinstance(selections, str):
            selections = [selections]

        try:
            res = pd.concat(
                [self[sel].groupby(self[sel].index).sum().iloc[:,0].rename(sel) for sel in selections],
                axis=1
            ).fillna(0)
        except KeyError as e:
            raise KeyError(f'invalid category: {e.args[0]}')

        if timing is not None:
            try:
                # https://stackoverflow.com/questions/24082784/pandas-dataframe-groupby-datetime-month
                res = res.groupby(pd.Grouper(freq=timing)).sum()
            except ValueError as e:
                raise ValueError(f'invalid timing for report(): {timing}')

        if avg_periods is not None:
            try:
                res = res.rolling(avg_periods).mean()
            except ValueError as e:
                raise ValueError(f'invalid avg_periods for report(): {avg_periods}')

        return res.sort_index(ascending=False).applymap(lambda v: round(v, 2))

    def render(self, df: pd.DataFrame, category: str=None) -> pd.DataFrame:
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')

            if isinstance(df, pd.Series):
                df = pd.DataFrame(df).transpose()

            # SplitNotes might not have a category assigned to their first part, in which case
            # the value always needs to be modified
            df = self.note_manager.apply_splits(render_df=df, category=None)
            if category is not None:
                ids = [s.id for s in self.note_manager.find_splits(category)]
                df = pd.concat([df, self._df[self.id.isin(ids)]]).sort_index()
                df = self.note_manager.apply_splits(render_df=df, category=category)
            df = self.note_manager.apply_linked(render_df=df, full_df=self._df)
            return df.drop('id', axis=1)

    def add_note(self, df: pd.DataFrame, note: str) -> None:
        if isinstance(df, pd.Series):
            df = pd.DataFrame(df).transpose()
        df = self.hash_transactions(df)
        for id in df['id'].values:
            self.note_manager.add_note(id, note, drop_dups=False)
        self.note_manager.drop_duplicates()
