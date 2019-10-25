import logging
import unittest
from datetime import datetime, timedelta

import pandas as pd

from budget import plan
from budget.plan.utils import date_range, parse_date

logging.basicConfig(level=logging.DEBUG)


class TestSimplePlan(unittest.TestCase):
    def setUp(self) -> None:
        initial = [
            ('Checking', 5000.00),
            ('Credit Card 1', -500.00),
            ('Credit Card 2', -1000.00),
            ('Credit Card 3', -2000.00),
        ]
        self.plan = plan.SimplePlan([plan.Expense(*args) for args in initial])

        exps = {
            'Paycheck': '2000/2w',
            'Rent': '-1000/ms',
            'Food and Drink': '-1000/1m/3d',
            'Clothes': '-1000/1y/1m',
            'Car Loan': '-300/ms+23'
        }
        self.plan.add_cfg(exps)


    def test_add(self):
        self.plan.add_expense(plan.Expense('Burn rate', -250, None, recur='1W'))
        return

    def test_project(self):
        df = self.plan.project(start=datetime.today(), end=100)
        df = self.plan.project(end=750)
        monthly = df[df['Name'] == 'Car Note']
        self.assertEqual(monthly.index[0].month+1, monthly.index[1].month)
        return

    def test_linearize(self):
        res = self.plan.linearize(end=90)
        return

    def test_date_parse(self):
        self.assertIsInstance(parse_date('07/3/2019'), datetime)
        self.assertIsInstance(parse_date('2019-07-13'), datetime)
        self.assertIsInstance(parse_date('7-3'), datetime)
        self.assertIsInstance(parse_date('07/3'), datetime)

    def test_to_df(self):
        self.assertIsInstance(self.plan.df, pd.DataFrame)

    def test_date_range(self):
        today = datetime.combine(datetime.today().date(), datetime.min.time())

        mr = plan.utils.month_range_day(today, 6)
        self.assertIsInstance(mr, pd.DatetimeIndex)

        end = today + timedelta(days=62)
        for f in ['1m', '2w', '4d']:
            mr = date_range(today, end, freq=f)
            self.assertIsInstance(mr, pd.DatetimeIndex)
            self.assertEqual(today.day, mr[0].day)

if __name__ == '__main__':
    unittest.main()