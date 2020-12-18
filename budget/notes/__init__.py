import sqlite3

from .manager import NoteManager
from .note import Note, Link, Category
from .split import SplitNote


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