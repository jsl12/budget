import logging
import re
import sqlite3
import warnings
from functools import reduce
from pathlib import Path
from typing import List

import pandas as pd
import yaml

from . import processing
from .load import Loader
from .notes import NoteManager
from .notes.note import Category
from .utils import hash, report


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

        if isinstance(input, str):
            # Try selecting based on a category name
            try:
                res = self._df[self._sel[input]]
            except KeyError:
                raise KeyError(f'\'{input}\' is not a category. Valid categories:' + str(self._sel.columns.tolist()))
            else:
                return self.render(res, input)
        else:
            # Try selecting using absolute value position
            try:
                res = self._df.iloc[input]
            except IndexError:
                pass
            else:
                return self.render(res)

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
        return ~self._sel.any(axis=1) & ~self._df['id'].isin(
            [n.id for n in self.note_manager.get_notes_by_type(Category)]
        )

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
        # OBSOLETE?
        # need to load the SQL database first to get the notes
        # with self.sql_context() as con:
        #     self.note_manager.load_notes(con)
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

    def report(self, selections, freq: str = None, avg: int = None) -> pd.DataFrame:
        if isinstance(selections, str):
            selections = [selections]

        try:
            res = pd.concat(
                [self[sel].groupby(self[sel].index).sum().iloc[:,0].rename(sel) for sel in selections],
                axis=1
            ).fillna(0)
        except KeyError as e:
            raise KeyError(f'invalid category: {e.args[0]}')

        return report(df=res, freq=freq, avg=avg)

    def render(self, df: pd.DataFrame, category: str = None) -> pd.DataFrame:
        """
        Applies any notes that are attached to transactions in the DataFrame. DataFrame needs to have
        an 'id' column. A category can also be passed in to find additional transactions with a SplitNote
        attached.

        :param df:
        :param category:
        :return:
        """
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')

            if isinstance(df, pd.Series):
                df = pd.DataFrame(df).transpose()

            # Append the manually categorized
            df = df.append(self._df[self.id.isin(self.note_manager.manual_ids(category))])

            # Append transactions with relevant SplitNotes attached
            df = df.append(self._df[self.id.isin(self.note_manager.split_ids(category))])

            # Append the linked
            df = df.append(self._df[self.id.isin(self.note_manager.linked_ids(df))])

            # Apply all the notes
            df = self.note_manager.apply_notes(df, category)

            # Clean up the result
            df = df.drop('id', axis=1).sort_index()
            return df

    def add_note(self, df: pd.DataFrame, note: str) -> None:
        if isinstance(df, pd.Series):
            df = pd.DataFrame(df).transpose()
        df = self.hash_transactions(df)
        for h in df['id'].values:
            self.note_manager.add_note(h, note, drop_dups=False)
        self.note_manager.drop_duplicates()

    def find_by_id(self, id_to_find: str) -> pd.Series:
        return self._df.reset_index().set_index('id').loc[id_to_find]

    def df_from_ids(self, ids: List[str]) -> pd.DataFrame:
        df = pd.DataFrame([self.find_by_id(i) for i in ids])
        df.index.name = 'id'
        df = df.reset_index()
        try:
            return df.set_index('Date')
        except KeyError:
            # this will happen if the DataFrame is empty
            return None

    def df_note_search(self, query: str) -> pd.DataFrame:
        note_mask = self.notes.str.contains(query, case=False)
        notes = self._notes[note_mask]
        df = self.df_from_ids(notes.index)
        try:
            df['Note'] = [n.note for n in notes]
        except TypeError:
            # Happens when no matching notes are found
            return None
        else:
            return df.drop('id', axis=1)
