import re
import warnings
from dataclasses import dataclass
from typing import List

import pandas as pd

from .note import Note, Link
from .split import SplitNote, Split


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
        return list(self.notes[self.notes.map(lambda n: type(n) is typ)])

    def find_splits(self, cat=None) -> List[Split]:
        res = []
        for n in self.notes[self.notes.map(lambda note: isinstance(note, SplitNote))].values:
            try:
                res.append(n.parts[cat])
            except KeyError:
                pass
        return res

    def apply_splits(self, render_df: pd.DataFrame, category: str) -> pd.DataFrame:
        splits = self.find_splits(category)

        res_vals = render_df.set_index('id')['Amount'].copy()
        base_vals = res_vals.copy()

        for s in splits:
            if s.id in res_vals.index:
                res_vals.loc[s.id] = 0

        for s in splits:
            try:
                res_vals.loc[s.id] += s.modify(base_vals.loc[s.id])
            except KeyError:
                pass

        render_df['Amount'] = res_vals.values
        return render_df

    def find_linked(self, id: str) -> List[Link]:
        '''
        Get a list of Link notes that target the input id
        '''
        return [n for n in self.notes[self.notes.map(lambda n: isinstance(n, Link))].values
            if n.target == id]

    def apply_linked(self, render_df: pd.DataFrame, full_df: pd.DataFrame) -> pd.DataFrame:
        amt_col = 'Amount'
        id_col = 'id'
        assert id_col in render_df.columns
        render_vals: pd.Series = render_df.set_index(id_col)[amt_col].copy()
        original_vals: pd.Series = full_df.set_index(id_col)[amt_col]

        # For each transaction in the input DataFrame
        for id in render_vals.index.values:
            # For each note associated with it
            for note in self.find_linked(id):
                # Add the value of the linked transaction to the target
                render_vals.loc[id] += original_vals.loc[note.id]
                # Set the value of the linked transaction to 0 if it appears in the result
                if note.id in render_vals.index:
                    render_vals.loc[note.id] = 0

        # Throws an error for setting values on view, which is actually what we're trying to do
        # render_df should just be a view of the full_df and the underlying values shouldn't get modified
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            render_df[amt_col] = render_vals.to_numpy()

        return render_df

    @staticmethod
    def parse_note(id: str, input: str, add_note_types=None):
        note_types = [SplitNote, Link]
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