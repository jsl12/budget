import unittest
import logging
import gen
import pandas as pd
from unittest import TestCase
from pathlib import Path

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