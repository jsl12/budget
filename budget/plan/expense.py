import re
from dataclasses import dataclass
from datetime import datetime

import pandas as pd

from .utils import parse_date, date_range


@dataclass
class Expense:
    name: str
    amount: float
    date: datetime = datetime.today()
    recur: str = None
    compile: str = None
    offset: int = None

    def __post_init__(self):
        if isinstance(self.date, str):
            self.date = parse_date(self.date)
        elif isinstance(self.date, datetime):
            self.date = datetime.combine(self.date.date(), datetime.min.time())

        if not isinstance(self.amount, float):
            self.amount = float(self.amount)

        if self.recur is not None:
            self.recur = self.recur.upper()

    def project(self, start: datetime = None, end: datetime = None) -> pd.Series:
        """
        Returns a Series of Expenses based on a single, recurring recurring Expense

        :param start:
        :param end:
        :return:
        """
        if self.compile is not None:
            recur = '1D'
        else:
            recur = self.recur
        dates = date_range(
            start=start or self.date,
            end=end,
            freq=recur
        )

        if self.compile is not None:
            data = [self.daily for d in dates]
        else:
            data = [Expense(self.name, self.amount, d.to_pydatetime()) for d in dates]
        res = pd.Series(data=data, index=dates)

        if self.compile is not None:
            res = res.groupby(pd.Grouper(freq=self.compile)).sum()
            data = [Expense(self.name, value, date) for date, value in res.iteritems()]
            res = pd.Series(data=data, index=res.index)

        return res

    @property
    def daily(self):
        if self.recur is not None:
            if 'W' in self.recur:
                period = 7
            elif 'M' in self.recur:
                period = 31
            elif 'Y' in self.recur:
                period = 365
            m = re.match('(\d+)(\w+)', self.recur)
            num = int(m.group(1))
            return round(self.amount / (num * period), 2)

    @staticmethod
    def from_plan_str(name: str, input: str):
        if '+' in input:
            d = input.split('+')
            input = d[0]
            day_offset = d[1]
        else:
            day_offset = None

        input = input.split('/')
        value = input[0]
        period = input[1]
        try:
            compile_period = input[2]
        except:
            compile_period = None

        return Expense(
            name=name,
            amount=round(float(value), 2),
            date=None,
            recur=f'{period}',
            compile=compile_period,
            offset=day_offset,
        )