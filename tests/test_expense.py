import logging
import unittest
from datetime import datetime

from budget.plan.expense import Expense

logging.basicConfig(level=logging.DEBUG)

class TestExpense(unittest.TestCase):
    def test_day_of_month(self):
        day = 28
        exp = Expense.from_plan_str('Day of Month Expense', f'-100/MS+{day}')
        exp.date = datetime(year=2020, month=1, day=1)
        df = exp.df(end=90)
        self.assertTrue((df.index[-1] - exp.date).days < 90)
        self.assertTrue((df.index.day.values == day).all())
        return

    def test_biweekly(self):
        exp = Expense.from_plan_str('Biweekly Expense', '-50/2W')
        exp.date = datetime(year=2020, month=1, day=3)
        df = exp.df(end=90)
        self.assertTrue((df.index[-1] - exp.date).days < 90)
        self.assertEqual(df.shape[0], 7)
        return

    def test_int_days(self):
        exp = Expense.from_plan_str('Int Day Expense', '-10/4D')
        exp.date = datetime(year=2020, month=1, day=1)
        df = exp.df(end=90)
        self.assertTrue((df.index[-1] - exp.date).days < 90)
        return

if __name__ == '__main__':
    unittest.main()