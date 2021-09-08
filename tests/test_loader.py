import logging
import unittest
from pathlib import Path
from unittest import TestCase

import pandas as pd

import gen

logging.basicConfig(level=logging.DEBUG)


class LoaderTest(TestCase):
    def setUp(self) -> None:
        self.bd = gen.gen_bd()
        self.bd.yaml_path = Path(r'..\examples\user_config.yaml')

    def test_loader(self):
        self.bd.load_csv()
        self.assertIsInstance(self.bd._df, pd.DataFrame)

if __name__ == '__main__':
    unittest.main()