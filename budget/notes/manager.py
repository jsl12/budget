import logging
import re
import sqlite3
from dataclasses import dataclass
from typing import List

import pandas as pd

from . import note, split
from .note import Note, Link, Category
from .split import SplitNote

NOTE_PARSE_REGEX = re.compile('id=\'([\d\w]+)\', note=\'([\d\w :,]+)\'')

def quickload_notes(path):
    with sqlite3.connect(path) as conn:
        return (
            NoteManager()
            .load_notes(con=conn)
        )

def quicksave_notes(path, note_df):
    nm = NoteManager()
    nm.notes = note_df
    with sqlite3.connect(path) as conn:
        nm.save_notes(con=conn)

@dataclass
class NoteManager:
    SQL_NOTE_TABLE = 'notes'

    def __post_init__(self):
        self.notes = pd.Series(name='note', dtype='object')
        self.logger = logging.getLogger(__name__)

    def validate_notes(self, ids: pd.Series):
        return self.notes.map(lambda n: n.id).isin(ids).all()

    def add_note(self, id, note, drop_dups=True):
        n = self.parse_note(id, note)
        self.notes = self.notes.append([pd.Series([n], index=[n.id])])
        if drop_dups:
            self.drop_duplicates()

    def drop(self, id, note_text):
        print(f'Dropping note from {id}: {note_text}')
        self.notes = self.notes[~self.notes.apply(
            lambda n: (n.note == note_text) and (n.id == id)
        )]

    def drop_duplicates(self):
        self.notes = self.notes[~self.notes.map(repr).duplicated()]

    def load_notes(self, con):
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

    def save_notes(self, con):
        self.notes.map(repr).to_sql(name=self.SQL_NOTE_TABLE, con=con, if_exists='replace')

    def get_notes_by_id(self, ids: List[str]) -> pd.Series:
        return self.notes[self.notes.apply(lambda n: n.id in ids)]

    def get_notes_by_type(self, typ: type) -> pd.Series:
        # doesn't use isinstance() to prevent subtypes from being selected
        return self.notes[self.notes.apply(lambda n: type(n) is typ)]

    def manual_ids(self, cat: str) -> pd.Series:
        """
        Gets ids of transactions that have been manually categorized as the given category

        :param cat:
        :return:
        """
        return self.notes[
            # select from notes
            self.notes.apply(
                # the ones which are both a Category type and have a matching categorization
                lambda n: isinstance(n, note.Category) and n.category == cat
            )
        ].apply(lambda n: n.id)

    def split_ids(self, cat: str) -> pd.Series:
        return self.notes[
            # select from notes
            self.notes.apply(
                # the ones which are both a SplitNote type and have the category in one of its parts
                lambda n: isinstance(n, split.SplitNote) and cat in n.parts
            )
        # convert to the value of the id attribute of each note
        ].apply(lambda n: n.id)

    def linked_ids(self, df: pd.DataFrame) -> pd.Series:
        """
        Gets ids of transactions that target those in the given DataFrame
        Example:
            Transactions A and B are both linked to transaction C, which appears in the given DataFrame
            Returns a Series of ids that include the ids of A and B

        :param df:
        :return:
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
        """
        Applies Link notes in the given DataFrame.
        The DataFrame needs to include both the original transactions and the ones linked to them

        :param df:
        :return:
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

    @staticmethod
    def eval_note(input):
        try:
            return eval(input)
        except (NameError, SyntaxError):
            m = NOTE_PARSE_REGEX.search(input)
            return NoteManager.parse_note(m.group(1), m.group(2))

    @staticmethod
    def parse_note(id: str, input: str, add_note_types=None):
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
