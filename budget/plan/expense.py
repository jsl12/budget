import re
from dataclasses import dataclass
from datetime import datetime, timedelta

import pandas as pd

from .utils import parse_date, date_range


@dataclass
class Expense:
    name: str
    amount: float
    date: datetime = datetime.today()
    recur: str = None
    compile: str = None
    offset: int = 0

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
        start = start or self.date

        if self.compile is not None:
            dates = date_range(start=start, end=end, freq='1D')
            res = pd.Series(
                data=[self.daily for d in dates],
                index=dates
            )

            res = res.resample(
                rule=self.compile,
                label='right'
            ).sum()
            res = pd.Series(
                data=[Expense(self.name, value, date) for date, value in res.iteritems()],
                index=res.index
            )
        else:
            dates = date_range(start=start, end=end, freq=self.recur)
            res = pd.Series(
                data=[Expense(self.name, self.amount, d.to_pydatetime()) for d in dates],
                index=dates
            )

            res.index += timedelta(days=self.offset)
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
            try:
                m = re.match('(\d+)(\w+)', self.recur)
                num = int(m.group(1))
            except AttributeError:
                num = 1
            return round(self.amount / (num * period), 2)

    @staticmethod
    def from_plan_str(name: str, input: str):
        if '+' in input:
            d = input.split('+')
            input = d[0]
            day_offset = int(d[1])
        else:
            day_offset = 0

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