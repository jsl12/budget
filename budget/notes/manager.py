import logging
import re
from typing import List

import numpy as np
import pandas as pd

from . import note, split
from .note import Note, Link, Category
from .split import SplitNote

LOGGER = logging.getLogger(__name__)
NOTE_PARSE_REGEX = re.compile('id=\'([\d\w]+)\', note=\'([\d\w :,]+)\'')

class NoteManager:
    """Class to handle higher-level :class:`~budget.Note` manipulation

    Attributes
    ----------
    notes : :class:`~pandas.DataFrame`
        :class:`~pandas.DataFrame` of the :class:`~budget.Note` objects. `Index` is the :class:`str` ID of the
        transaction that each :class:`~budget.Note` is linked to

    """
    SQL_NOTE_TABLE = 'notes'

    def __init__(self):
        self.notes = pd.Series(name='note', dtype='object')
        self.logger = logging.getLogger(__name__)

    def load_notes(self, con) -> pd.Series:
        """Loads the :class:`~budget.Note` :class:`~pandas.Series` using a connection to a SQL database using



        Parameters
        ----------
        con : SQLAlchemy connectable, :class:`str`, or :mod:`sqlite3` connection
            SQL connection

        Returns
        -------
        :class:`~pandas.Series`
        """

        # Read the whole table of notes
        notes = pd.read_sql_query(sql=f'select * from {self.SQL_NOTE_TABLE}', con=con)

        self.logger.debug(f'{notes.shape[0]} notes loaded from \'{self.SQL_NOTE_TABLE}\'')

        # Set up the index, which will be the ID of the transaction the note is attached to
        notes.set_index(notes.columns[0], inplace=True)

        try:
            # Select only the first column (should only be one)
            notes = notes.iloc[:, 0].map(NoteManager.eval_note)
        except NameError:
            self.logger.debug('No notes loaded')
            pass
        # Assign to attribute
        self.notes = notes
        return notes

    @staticmethod
    def eval_note(input: str) -> note.Note:
        """Evaluates the :func:`repr` string, which reconstructs a :class:`~budget.Note` object

        Parameters
        ----------
        input : :class:`str`
            :class:`str` produced by the :func:`repr` of that object

        Returns
        -------
        :class:`~budget.Note`
        """

        try:
            return eval(input)
        except (NameError, SyntaxError):
            m = NOTE_PARSE_REGEX.search(input)
            return NoteManager.parse_note(m.group(1), m.group(2))

    @staticmethod
    def parse_note(id: str, input: str, add_note_types=None) -> note.Note:
        """Looks for the `tag` of each type of :class:`~budget.Note` in the `input` string, then constructs a new
        :class:`~budget.Note` object when it finds one

        Parameters
        ----------
        id : :class:`str`
            id of the `Note` to create
        input : :class:`str`
            input :class:`str` to look in
        add_note_types :
            additional :class:`~budget.Note` types to parse

        Returns
        -------
        :class:`~budget.Note`
        """

        note_types = [SplitNote, Link, Category]
        if add_note_types is not None:
            try:
                note_types.append(add_note_types)
            except:
                note_types.extend(add_note_types)

        if isinstance(input, str):
            for nt in note_types:
                try:
                    if nt._tag in input:
                        res = nt(id, input)
                        break
                except AttributeError:
                    raise AttributeError('Notes must have a _tag attribute')
            try:
                return res
            except NameError as e:
                # res won't be set if none of the tags match
                return Note(id, input)
        else:
            if isinstance(input, Note):
                raise TypeError(f'\'{input}\' is already a {type(input)}')
            else:
                raise TypeError(f'unknown type of note: {type(input)}')

    def validate_notes(self, ids: pd.Series) -> bool:
        """Checks to make sure that all of the :class:`~budget.Note`s are contained in the ids

        Parameters
        ----------
        ids : set or like-like
            :class:`list` or something that can be used in :meth:`~pandas.Series.isin`

        Returns
        -------
        bool
            `True` if all of the `Notes` in the :class:`~budget.notes.NoteManager` are in the given list of IDs
        """

        return self.notes.map(lambda n: n.id).isin(ids).all()

    def add_note(self, id: str, note: str, drop_dups: bool = True):
        """Parses a string into a :class:`~budget.Note` object and adds it to the :class:`~budget.notes.NoteManager` using
        :class:`~pandas.Series.append` and optionally uses :class:`~pandas.Series.drop_duplicates`

        Parameters
        ----------
        id : str
            id of the transaction to attach the :class:`~budget.Note` to
        note : str
            input string used to create the :class:`~budget.Note` object
        drop_dups : bool
            Whether to drop the duplicate notes

        """

        n = self.parse_note(id, note)
        self.notes = self.notes.append([pd.Series([n], index=[n.id])])
        if drop_dups:
            self.drop_duplicates()

    def drop(self, id: str, note_text: str):
        """Drops a specific :class:`~budget.Note` using its ID and text

        Parameters
        ----------
        id : str
            id of the note to drop
        note_text : str
            text of the note to drop
        """

        print(f'Dropping note from {id}: {note_text}')
        self.notes = self.notes[~self.notes.apply(
            lambda n: (n.note == note_text) and (n.id == id)
        )]

    def drop_duplicates(self):
        """Removes duplicate `Notes` in the :class:`~budget.notes.NoteManager`
        """

        self.notes = self.notes[~self.notes.map(repr).duplicated()]

    def save_notes(self, con):
        self.notes.map(repr).to_sql(name=self.SQL_NOTE_TABLE, con=con, if_exists='replace')

    def get_notes_by_id(self, ids: List[str]) -> pd.Series:
        """Gets the notes that match the IDs in the given list

        Parameters
        ----------
        ids : List[str]
            list of ids to get the notes

        Returns
        -------
        :class:`~pandas.Series`
        """

        return self.notes[self.notes.apply(lambda n: n.id in ids)]

    def get_notes_by_type(self, typ: type) -> pd.Series:
        """Gets the notes that match the given type

        Parameters
        ----------
        typ : type
            type of :class:`~budget.Note` to get

        Returns
        -------
        :class:`~pandas.Series`
        """

        # doesn't use isinstance() to prevent subtypes from being selected
        return self.notes[self.notes.apply(lambda n: type(n) is typ)]

    def manual_ids(self, cat: str) -> np.ndarray:
        """Gets ids of transactions that have been manually categorized as the given category

        Parameters
        ----------
        cat : str
            category of transactions to get IDs for

        Returns
        -------
        :class:`~numpy.ndarray`
        """

        return self.notes[
            # select from notes
            self.notes.apply(
                # the ones which are both a Category type and have a matching categorization
                lambda n: isinstance(n, note.Category) and n.category == cat
            )
        ].apply(lambda n: n.id).values

    def split_ids(self, cat: str) -> pd.Series:
        return self.notes[
            # select from notes
            self.notes.apply(
                # the ones which are both a SplitNote type and have the category in one of its parts
                lambda n: isinstance(n, split.SplitNote) and cat in n.parts
            )
        # convert to the value of the id attribute of each note
        ].apply(lambda n: n.id)

    def linked_ids(self, df: pd.DataFrame) -> np.ndarray:
        """Gets ids of transactions that target those in the given DataFrame

        Example
            Transactions A and B are both linked to transaction C, which appears in the given DataFrame
            Returns a Series of ids that include the ids of A and B

        Returns
        -------
        :class:`~numpy.ndarray`: str
        """

        return self.notes[
            # select from notes
            self.notes.apply(
                # the ones which are both a Link type and have a target id in the given DataFrame
                lambda n: isinstance(n, note.Link) and n.target in df['id'].values
            )
        # convert to the value of the id attribute of each note
        ].apply(lambda n: n.id).values

    def apply_linked(self, df: pd.DataFrame) -> pd.DataFrame:
        """Applies Link notes in the given DataFrame, adding the value of each linked transaction onto the one it targets
        
        The DataFrame needs to include both the original transactions and the ones linked to them. The values of the linked
        transactions will be set to 0 as they are added onto the target transaction

        Parameters
        ----------
        df : :class:`~pandas.DataFrame`
            transactions to apply the linked notes to

        Returns
        -------
        :class:`~pandas.DataFrame`
            :class:`~pandas.DataFrame` of the modified transactions
        """

        link_notes = self.get_notes_by_type(note.Link)
        source_in_df = link_notes.apply(lambda n: n.id in df['id'].values)
        target_in_df = link_notes.apply(lambda n: n.target in df['id'].values)
        # assert (target_in_df & ~source_in_df).any()

        df = df.reset_index().set_index('id')

        try:
            # if both source and target exist in the DataFrame, add the source Amount to the target Amount
            for n in link_notes[source_in_df & target_in_df]:
                df.loc[n.target, 'Amount'] += df.loc[n.id, 'Amount']
            # set the values of all source transactions to 0
            for n in link_notes[source_in_df]:
                df.loc[n.id, 'Amount'] = 0
        except Exception as e:
            raise

        df = df.reset_index().set_index(df.columns[0])
        return df

    def apply_split(self, df: pd.DataFrame, cat: str) -> pd.DataFrame:
        split_notes = self.get_notes_by_type(split.SplitNote)
        for_this_cat = split_notes.apply(lambda n: cat in n.parts)
        trans_in_df = split_notes.apply(lambda n: n.id in df['id'].values)

        df = df.reset_index().set_index('id')

        try:
            # If the split is for this category, set the Amount equal to the modified value
            for n in split_notes[trans_in_df & for_this_cat]:
                orig_val = df.loc[n.id, 'Amount']
                df.loc[n.id, 'Amount'] = n.parts[cat].modify(orig_val)
            # If the split is not for this category, then subtract all the other modified values
            for n in split_notes[trans_in_df & ~for_this_cat]:
                orig_val = df.loc[n.id, 'Amount']
                for target_cat, split_obj in n.parts.items():
                    df.loc[n.id, 'Amount'] -= split_obj.modify(orig_val)

        except Exception as e:
            raise

        df = df.reset_index().set_index(df.columns[0])
        return df

    def apply_notes(self, df: pd.DataFrame, cat: str) -> pd.DataFrame:
        df = self.apply_linked(df)
        df = self.apply_split(df, cat)
        return df

    def re_parse(self):
        self.notes = self.notes.map(lambda n: self.parse_note(n.id, n.note))

    @property
    def note_text(self) -> pd.Series:
        res = self.notes.apply(lambda n: n.note)
        res.name = 'note text'
        return res

    def contains(self, input: str, case: bool = False, text: bool = False) -> pd.Series:
        res = self.notes[self.note_text.str.contains(input, case=case)]
        if text:
            res = res.apply(lambda n: n.note)
        return res

    @property
    def tagged_categories(self) -> pd.Series:
        # returns a Series of the unique categories in Category notes
        return self.get_notes_by_type(Category).apply(lambda n: n.category).drop_duplicates()

    def drop_orphans(self, ids):
        orphans = self.notes[~self.notes.index.isin(ids)]
        self.notes = self.notes.drop(orphans.index)
        LOGGER.debug(f'Dropped {orphans.shape[0]} orphaned messages')
