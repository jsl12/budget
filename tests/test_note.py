import unittest
import budget
import gen
from unittest import TestCase
from pathlib import Path

class NoteTestCase(TestCase):
    def setUp(self) -> None:
        self.bd = gen.gen_bd()

    def test_link_notes(self):
        # add some links
        self.bd.add_note(self.bd[-1], f'link: {self.bd.id[0]}')
        self.bd.add_note(self.bd[-2], f'link: {self.bd.id[0]}')

        # Add another transaction to the 'A' category
        self.bd._sel['A'].iloc[-2] = True

        # df = self.bd._df[self.bd._sel['A']].copy()
        df = self.bd._df[self.bd._sel['A']]
        res = self.bd.note_manager.apply_linked(
            df, self.bd._df
        )

        self.assertEqual(df.shape, res.shape)
        self.assertTrue(df.index.equals(res.index))
        self.assertEqual(res.iloc[0]['Amount'], 250.0)
        self.assertEqual(res.iloc[-1]['Amount'], 0)

    def test_direct_notes(self):
        self.bd.add_note(self.bd[0], 'split: 50%, 25% B')
        self.assertEqual(self.bd['A'].iloc[0]['Amount'], -25.0, 'Direct note failed')

    def test_indirect_notes(self):
        self.bd.add_note(self.bd.df.iloc[0], 'split: 50% A, 20% B')
        self.bd.add_note(self.bd.df.iloc[0], 'split: 25% B')
        self.bd.add_note(self.bd.df.iloc[-1], 'split: 30% B')
        self.assertEqual(self.bd['A'].iloc[0]['Amount'], -25.0, 'Indirect note failed')
        self.assertEqual(self.bd['B'].iloc[0]['Amount'], -22.5, 'Indirect note failed')
        self.assertEqual(self.bd['B'].iloc[-1]['Amount'], -60.0, 'Indirect note failed')

    def test_get_notes(self):
        self.bd.add_note(self.bd[0], 'test note')
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

if __name__ == '__main__':
    unittest.main()
