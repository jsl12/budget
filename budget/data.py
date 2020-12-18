import logging
import re
import sqlite3
import warnings
from functools import reduce
from pathlib import Path
from typing import List, Dict

import numpy as np
import pandas as pd
import yaml

from . import processing
from . import utils
from .load import CSVLoader
from .notes import NoteManager
from .notes.note import Note

LOGGER = logging.getLogger(__name__)

class BudgetData:
    """Container class for the transactions and notes

    Created with a ``yaml`` file for configuration

    Can load from:
        - CSV files
        - `sqlite3` database files
    Can save to:
        - `sqlite3` database files


    Attributes
    ----------
    yaml_path : str or :class:`pathlib.Path`
        path to the `yaml` configuration file
    note_manager : :any:`NoteManager<budget.notes.manager.NoteManager>`
        a `NoteManager` instance to handle high level operations with `Note` objects
    SQL_DF_TABLE : str
        name for the transaction table in the SQL database
    SQL_SEL_TABLE : str
        name for the selections table in the SQL database
    DF_DATE_COL : str
        name for the date column in the SQL database
    """
    SQL_DF_TABLE = 'transactions'
    SQL_SEL_TABLE = 'selections'
    DF_DATE_COL = 'Date'

    def __init__(self, yaml_path: str):
        """
        Initializes the :class:`budget.BudgetData` object from a yaml file

        Parameters
        ----------
        yaml_path : str
            path to the yaml configuration file

        """
        self.yaml_path = Path(yaml_path)
        if not self.yaml_path.is_absolute():
            self.yaml_path = self.yaml_path.resolve()
        self.note_manager = NoteManager()

        self.RENDER_DROP_ID_COL = True
        self.RENDER_SORT = True

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

    @property
    def cfg(self) -> Dict:
        """Loads and returns the configuration `dict` from the yaml file used to create the :class:`budget.BudgetData`
        instance

        Returns
        -------
        dict
        """
        with self.yaml_path.open('r') as file:
            return yaml.load(file, Loader=yaml.SafeLoader)

    @property
    def categories(self) -> Dict:
        """

        Returns
        -------
        dict
        """
        return self.cfg['Categories']

    @property
    def exclude(self):
        try:
            return self.cfg['Exclude Notes']
        except KeyError as e:
            return

    @property
    def df(self) -> pd.DataFrame:
        """

        Returns
        -------
        :pandas_api:`pandas.DataFrame`
        """
        if not hasattr(self, '_df'):
            self.load_sql()
        if 'id' in self._df.columns:
            return self._df.drop('id', axis=1).fillna('')
        else:
            return self._df.fillna('')

    @property
    def id(self) -> pd.Series:
        return self._df['id']

    @property
    def categorization(self):
        def find_cat(row):
            try:
                if row.any():
                    res = row.index[row][-1]
                    return res
            except:
                raise

        if not hasattr(self, '_categorization'):
            self._categorization = self._sel.apply(find_cat, axis=1)
        return self._categorization

    @property
    def amounts(self) -> pd.Series:
        # there should only be 1 column with numbers, the amounts column. This abstraction removes the dependence on the column name
        return self.df.select_dtypes('number').iloc[:, 0]

    @property
    def unselected(self) -> pd.DataFrame:
        return ~self._sel.any(axis=1) & ~self._df['id'].isin(self._notes.index)

    @property
    def notes(self) -> pd.Series:
        # return self.note_manager.notes.map(lambda n: n.note)
        ids = self.note_manager.notes.index.to_series()
        res = ids.apply(lambda v: self.find_by_id(v))
        res['Note'] = self.note_manager.notes.apply(lambda n: n.note)
        res = res.set_index('Date').drop('id', axis=1).sort_index(ascending=False)
        return res

    @property
    def _notes(self) -> pd.Series:
        return self.note_manager.notes

    @property
    def db_path(self) -> Path:
        res = Path(self.cfg['Loading']['db'])
        if not res.is_absolute():
            res = self.yaml_path.parents[0] / res
        return res

    def hash_transactions(self, df: pd.DataFrame = None) -> pd.DataFrame:
        if df is None:
            df = self._df
        df['id'] = df.apply(utils.hash, axis=1)
        return df

    def load_csv(self):
        """Loads transactions from all the accounts into a single :class:`~pandas.DataFrame`

        Returns
        -------

        """
        LOGGER.debug(f'Loading CSV files from {self.yaml_path.name}')
        self._df = CSVLoader(
            accounts_cfg=self.cfg['Loading']['Accounts'],
            base_path=Path(self.cfg['Loading']['base'])
        ).load_all_accounts()

    def process_categories(self):
        """Processes the categories using :func:`~budget.processing.gen_mask_tree` and
        :func:`~budget.utils.flatten_mask_tree`.

        This results in

        """
        LOGGER.debug(f'Processing selections as defined in {self.yaml_path.name}')
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
        self._df['Category'] = self.categorization
        LOGGER.debug('Done')

    def sql_context(self, path=None):
        if path is None:
            path = self.db_path

        try:
            connection = sqlite3.connect(path)
        except:
            raise
        else:
            LOGGER.debug(f'Opened SQL connection to\n{path.resolve()}')
            return connection

    def save_sql(self, path=None):
        path = Path(path) if isinstance(path, str) else path
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            with self.sql_context(path) as con:
                self._df.to_sql(name=self.SQL_DF_TABLE, con=con, if_exists='replace')
                self._sel.to_sql(name=self.SQL_SEL_TABLE, con=con, if_exists='replace')
                self.note_manager.save_notes(con)

    def load_sql(self, path=None, notes=True):
        path = Path(path) if isinstance(path, str) else path
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
        LOGGER.debug(f'left sql connection context')

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
            return self.df[self.id.isin(self.note_manager.get_notes_by_type(input).apply(lambda n: n.id))]
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

        return utils.report(df=res, freq=freq, avg=avg)

    def render(self, df: pd.DataFrame, category: str = None, drop_id=None, sort=None) -> pd.DataFrame:
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

            LOGGER.debug(f'Starting render of transaction DataFrame')

            if category is not None:
                # Append based on notes that involve the category
                df = df.append(self.df_from_cat_notes(category))

            # find the transactions that are linked to ones in the df
            df = df.append(self.linked_sources(df))

            # drops duplicates in case multiple types of notes are linked to the same transaction
            df = df.drop_duplicates('id', keep='first')

            # Remove the excluded notes
            exc = self.exclude
            if exc is not None:
                for excluded_note in exc:
                    df = df[~df['id'].isin(self.note_manager.contains(excluded_note).index.values)]

            # Apply all the notes
            df = self.note_manager.apply_notes(df, category)

            # Clean up the result
            drop_id = drop_id or self.RENDER_DROP_ID_COL
            if drop_id:
                df = df.drop('id', axis=1)

            sort = sort or self.RENDER_SORT
            if sort:
                df = df.sort_index()

            LOGGER.debug(f'Done')
            return df

    def df_from_cat_notes(self, category: str) -> pd.DataFrame:
        """
        Gets transactions based on notes that involve categories:
            - manual categorizations of the form 'cat: <CATEGORY>'
            - split notes of the form 'split: ..., 1/2 <CATEGORY>, ...'

        :param category: category name as it appears in the user YAML file
        :return: DataFrame of matching transactions
        """
        return pd.concat(
            [
                # manually categorized
                self._df[self.id.isin(
                    # get ids of notes with a 'category' attribute that matches the category argument
                    self.note_manager.manual_ids(category)
                )],

                # with relevant splitnotes
                self._df[self.id.isin(
                    # get ids of notes with that have the category argument in one of its parts
                    self.note_manager.split_ids(category)
                )]
            ]
        )

    def linked_sources(self, df: pd.DataFrame):
        # select from the main DataFrame
        return self._df[
            # transactions with Link notes attached that target transactions in the DataFrame
            self.id.isin(self.note_manager.linked_ids(df))
        ]

    def add_note(self, df: pd.DataFrame, note: str) -> None:
        if isinstance(df, pd.Series):
            df = pd.DataFrame(df).transpose()
        df = self.hash_transactions(df)
        for h in df['id'].values:
            self.note_manager.add_note(h, note, drop_dups=False)
        self.note_manager.drop_duplicates()

    def find_by_id(self, id_to_find: str) -> pd.Series:
        try:
            return self._df.reset_index().set_index('id', drop=False).loc[id_to_find]
        except KeyError as e:
            raise KeyError(f'{id_to_find} not found in transactions')

    def df_from_ids(self, ids) -> pd.DataFrame:
        return pd.Series(ids).apply(lambda id: self.find_by_id(id)).set_index('Date')

    def note_search(self, query: str) -> pd.DataFrame:
        notes = self.note_manager.contains(query, text=True)
        df = self.df_from_ids(notes.index)
        try:
            df['Note'] = notes.values
        except TypeError:
            # Happens when no matching notes are found
            return pd.DataFrame(columns=self.df.columns.tolist() + ['Note'])
        else:
            return df.drop('id', axis=1).sort_index(ascending=False)

    def note_total(self, query: str):
        return self.df_from_ids(self.note_manager.contains(query).index.drop_duplicates().values)['Amount'].sum()

    def note_df(self, df: pd.DataFrame) -> pd.DataFrame:
        try:
            directly_attached_note_ids= df['id'][df['id'].isin(self.note_manager.notes.index)].values
            linked_note_ids = self.note_manager.linked_ids(df)
            ids = np.union1d(
                directly_attached_note_ids,
                linked_note_ids
            )

            # using the transaction ids to index the notes
            # this will also pick up multiple notes attached to a single transaction
            notes = self._notes.loc[ids]
        except KeyError:
        #     happens when there are no notes
            return pd.DataFrame(columns=df.columns)
        else:
            res = self.df_from_ids(notes.index)

            if res is not None:
                res['Note'] = notes.apply(lambda n: n.note if isinstance(n, Note) else '').values
                linked_targets = np.unique(self._notes.loc[linked_note_ids].apply(lambda n: n.target).values)
                linked_sources = self._df[self.id.isin(linked_targets)]
                res = res.append(linked_sources, sort=False)
                return res.sort_index()
            else:
                return pd.DataFrame(columns=df.columns.tolist() + ['Note'])