import unittest
from unittest import TestCase

import gen


class SQLTestCase(TestCase):
    def setUp(self) -> None:
        self.bd = gen.gen_bd()

    def test_sql(self):
        attrs = ['_df', '_sel', 'notes']
        attrs = {key: getattr(self.bd, key).copy() for key in attrs}

        self.bd.save_sql('test.db')
        self.bd.load_sql('test.db')

        for key, value in attrs.items():
            self.assertTrue(value.equals(getattr(self.bd, key)))

if __name__ == '__main__':
    unittest.main()