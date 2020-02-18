import unittest
from pathlib import Path
from unittest import TestCase

import gen

import budget


class NoteTestCase(TestCase):
    def setUp(self) -> None:
        self.bd: budget.BudgetData = gen.gen_bd()

    def test_link_notes(self):
        self.bd.add_note(self.bd.df.iloc[-1], f'link: {self.bd.id[0]}')
        self.bd.add_note(self.bd.df.iloc[-2], f'link: {self.bd.id[0]}')
        self.assertEqual(self.bd['A'].iloc[0]['Amount'], 250.0, 'Link note failed')
        self.assertEqual(self.bd['B'].iloc[0]['Amount'], 0.0, 'Link note failed')
        self.assertEqual(self.bd[-1].iloc[0]['Amount'], 0.0, 'Link note failed')

    def test_split(self):
        self.bd.add_note(self.bd.df.iloc[0], 'split: 50% B, 10% C')
        self.bd.add_note(self.bd.df.iloc[1], 'split: $10 C')
        self.bd.add_note(self.bd.df.iloc[2], 'split: 1/5 C')
        self.bd.add_note(self.bd.df.iloc[-1], 'split: 50% B, 50% C')
        self.assertEqual(self.bd['A'].iloc[0]['Amount'], -20.0, 'Indirect note failed')
        self.assertEqual(self.bd['B'].iloc[0]['Amount'], -25.0, 'Indirect note failed')
        self.assertEqual(self.bd['B'].iloc[-1]['Amount'], -100.0, 'Indirect note failed')
        self.assertEqual(self.bd['C'].iloc[1]['Amount'], 10.0, 'Indirect note failed')
        self.assertEqual(self.bd['C'].iloc[2]['Amount'], 100.0, 'Indirect note failed')

    def test_get_notes(self):
        self.bd.add_note(self.bd.df.iloc[0], 'test note')
        n = self.bd.note_manager.get_notes_by_id([self.bd.id[0]])[0]
        self.assertIsInstance(n, budget.notes.Note)

    def test_save_load_sql(self):
        self.bd.add_note(self.bd.df.iloc[0], 'asdf')
        self.bd.add_note(self.bd.df.iloc[0], 'music: asdf')
        self.bd.add_note(self.bd.df.iloc[0], 'gift: asdf')
        self.bd.add_note(self.bd.df.iloc[0], 'split: 25%, 50% BA')
        self.bd.add_note(self.bd.df.iloc[0], f'link: {self.bd.id[-1]}')
        self.bd.add_note(self.bd.df.iloc[0], 'trip: snowboarding')

        original_df = self.bd._df.copy()
        original_sel = self.bd._sel.copy()
        original_notes = self.bd._notes.copy()

        path = Path('test.db')
        self.bd.save_sql(path)
        self.bd.load_sql(path)

        self.assertTrue(original_df.equals(self.bd._df))
        self.assertTrue(original_sel.equals(self.bd._sel))
        self.assertTrue(original_notes.equals(self.bd._notes))

    def test_note_df(self):
        self.bd.add_note(self.bd.df.iloc[-1], f'link: {self.bd.id[0]}')
        self.bd.add_note(self.bd.df.iloc[-2], f'link: {self.bd.id[0]}')
        self.bd.add_note(self.bd.df.iloc[-1], f'custom note')
        df = self.bd.note_df(self.bd._df)
        self.assertEqual(3, df.shape[0])
        df = self.bd.note_df(self.bd._df.iloc[:1])
        self.assertEqual(0, df.shape[0])

if __name__ == '__main__':
    unittest.main()
