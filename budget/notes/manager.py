import re
from dataclasses import dataclass
from typing import List

import pandas as pd

from .note import Note, Link, Category
from .split import SplitNote


@dataclass
class NoteManager:
    SQL_NOTE_TABLE = 'notes'

    def __post_init__(self):
        self.notes = pd.Series(name='note', dtype='object')

    def validate_notes(self, ids: pd.Series):
        return self.notes.map(lambda n: n.id).isin(ids).all()

    def add_note(self, id, note, drop_dups=True):
        n = self.parse_note(id, note)
        self.notes = self.notes.append([pd.Series([n], index=[n.id])])
        if drop_dups:
            self.drop_duplicates()

    def drop(self, id):
        self.notes = self.notes.drop(id)

    def drop_duplicates(self):
        self.notes = self.notes[~self.notes.map(repr).duplicated()]

    def load_notes(self, con):
        # Read the whole table of notes
        notes = pd.read_sql_query(sql=f'select * from {self.SQL_NOTE_TABLE}', con=con)

        # Set up the index
        notes.set_index(notes.columns[0], inplace=True)

        rgx = re.compile('id=\'([\d\w]+)\', note=\'([\d\w :,]+)\'')
        def eval_note(input):
            try:
                return eval(input)
            except NameError:
                m = rgx.search(input)
                return self.parse_note(m.group(1), m.group(2))

        try:
            # Select only the first column (should only be one)
            notes = notes.iloc[:, 0].map(eval_note)
        except NameError:
            pass
        # Assign to attribute
        self.notes = notes

    def save_notes(self, con):
        self.notes.map(repr).to_sql(name=self.SQL_NOTE_TABLE, con=con, if_exists='replace')

    def get_notes_by_id(self, ids: List[str]) -> List[Note]:
        return list(self.notes[self.notes.index.isin(ids)].values)

    def get_notes_by_type(self, typ: type) -> List[Note]:
        # doesn't use isinstance() to prevent subtypes from being selected
        return [n for n in self.notes.values if type(n) is typ]

    @property
    def manual_notes(self):
        return self.get_notes_by_type(Category)

    @property
    def split_notes(self):
        return self.get_notes_by_type(SplitNote)

    @property
    def link_notes(self):
        return self.get_notes_by_type(Link)

    def manual_ids(self, cat: str):
        return [n.id for n in self.manual_notes if n.category == cat]

    def split_ids(self, cat: str) -> List[str]:
        return [n.id for n in self.split_notes if cat in n.parts]

    def linked_ids(self, df: pd.DataFrame) -> List[str]:
        return [n.id for n in self.link_notes if n.target in df['id'].values]

    def apply_notes(self, df: pd.DataFrame, cat: str) -> List[str]:
        relevant_notes = self.get_notes_by_id(df['id'].values)
        df = df.reset_index().set_index('id')

        for n in relevant_notes:
            if isinstance(n, SplitNote):
                original_val = df.loc[n.id, 'Amount']
                if cat in n.parts:
                    df.loc[n.id, 'Amount'] = 0
                    for target, s_obj in n.parts.items():
                        mod_val = s_obj.modify(original_val)
                        if target == cat:
                            df.loc[n.id, 'Amount'] += mod_val
                else:
                    for target, s_obj in n.parts.items():
                        mod_val = s_obj.modify(original_val)
                        df.loc[n.id, 'Amount'] -= mod_val

            elif isinstance(n, Link):
                try:
                    df.loc[n.target, 'Amount'] += df.loc[n.id, 'Amount']
                except KeyError:
                    # this happens if a transaction with a Link note attached gets processed, but the transaction it's
                    # targeting is not
                    pass
                df.loc[n.id, 'Amount'] = 0

        df = df.reset_index().set_index(df.columns[0])
        return df

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
