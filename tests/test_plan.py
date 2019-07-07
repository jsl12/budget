import logging
import unittest
import pandas as pd
from budget import plan
from datetime import datetime, timedelta

logging.basicConfig(level=logging.DEBUG)


class TestPlan(unittest.TestCase):
    def setUp(self) -> None:
        initial = [
            ('Checking', 5000.00),
            ('Credit Card 1', -500.00),
            ('Credit Card 2', -1000.00),
            ('Credit Card 3', -2000.00),
            ('Paycheck', 2000.00, datetime.combine(datetime.today().date(), datetime.min.time()), '2W'),
            ('Burn rate', -20, datetime.today(),'1D')
        ]
        self.plan = plan.SimplePlan([plan.Expense(*args) for args in initial])

    def test_add(self):
        self.plan.add_expense(plan.Expense('Burn rate', -250, recur='1W'))
        # self.plan.print_exp()

    def test_project(self):
        self.plan.add_expense(plan.Expense('Burn rate', -250, datetime.today() + timedelta(weeks=1), recur='1W'))
        df = self.plan.project(datetime.today() + timedelta(days=30))
        return

    def test_linearize(self):
        res = self.plan.linearize(datetime.today() + timedelta(days=30))
        return

    def test_date_parse(self):
        self.assertIsInstance(plan.parse_date('07/3/2019'), datetime)
        self.assertIsInstance(plan.parse_date('2019-07-13'), datetime)
        self.assertIsInstance(plan.parse_date('7-3'), datetime)
        self.assertIsInstance(plan.parse_date('07/3'), datetime)

    def test_to_df(self):
        self.assertIsInstance(self.plan.df, pd.DataFrame)

    def test_date_range(self):
        today = datetime.combine(datetime.today().date(), datetime.min.time())

        mr = plan.month_range_day(today, 6)
        self.assertIsInstance(mr, pd.DatetimeIndex)

        end = today + timedelta(days=62)
        for f in ['1m', '2w', '4d']:
            mr = plan.date_range(today, end, freq=f)
            self.assertIsInstance(mr, pd.DatetimeIndex)
            self.assertEqual(today.day, mr[0].day)

if __name__ == '__main__':
    unittest.main()