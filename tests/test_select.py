import unittest

import gen
import pandas as pd


class SelectTest(unittest.TestCase):
    def setUp(self) -> None:
        self.bd = gen.gen_bd()

    def test_mask_select(self):
        sel = pd.Series([True, False, True, False], index=self.bd.df.index)
        self.assertIsInstance(self.bd[sel], pd.DataFrame)

    def test_cat_select(self):
        cat = self.bd._sel.columns[0]
        self.assertIsInstance(self.bd[cat], pd.DataFrame)

    def test_int_select(self):
        self.assertEqual(self.bd[0].iloc[0].name, self.bd._df.iloc[0].name)
        self.assertTrue(self.bd[0:2].index.equals(self.bd._df.iloc[0:2].index))

    def test_date_select(self):
        self.assertTrue(self.bd['2019'].index.equals(self.bd.df['2019'].index))

if __name__ == '__main__':
    unittest.main()