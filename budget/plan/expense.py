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
        try:
            dates = date_range(
                start=start or self.date,
                end=end,
                freq=self.recur
            )
            res = pd.Series(
                data=[Expense(self.name, self.amount, d.to_pydatetime()) for d in dates],
                index=dates
            )
        except AttributeError:
            return
        else:
            if self.date is None:
                return res[1:]
            else:
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
        value, period = (input.split('/'))
        return Expense(
            name=name,
            amount=round(-float(value), 2),
            date=None,
            recur=f'1{period}'
        )