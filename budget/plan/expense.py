import re
from dataclasses import dataclass
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from . import utils

import logging

LOGGER = logging.getLogger(__name__)

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
            self.date = utils.parse_date(self.date)
        elif isinstance(self.date, datetime):
            self.date = datetime.combine(self.date.date(), datetime.min.time())

        if not isinstance(self.amount, float):
            self.amount = float(self.amount)

        if self.recur is not None:
            self.recur = self.recur.upper()

    def project(self, end: datetime) -> pd.Series:
        """
        Returns a Series of Expenses based on a single, recurring recurring Expense

        :param start:
        :param end:
        :return:
        """
        if self.recur is not None:
            if self.date is None:
                self.date = datetime.combine(datetime.today(), datetime.min.time())

            if isinstance(end, int):
                end = self.date + timedelta(days=end)

            dates = pd.date_range(
                start=self.date,
                freq=self.recur,
                end=end,
            )
            if len(dates) < 2:
                dates = pd.date_range(
                    start=self.date,
                    freq=self.recur,
                    periods=2
                )
            if dates[0] > self.date:
                try:
                    dates = dates.union(pd.date_range(
                        start=self.date,
                        freq=f'-{dates.freqstr}',
                        periods=2
                    ))
                except ValueError as e:
                    dates = dates.union(pd.date_range(
                        start=self.date,
                        freq=f'-1{dates.freqstr}',
                        periods=2
                    ))

            if self.compile is not None:
                total = self.amount * (dates.shape[0] - 1)
                amt = round(total / dates.to_series().diff().sum().days, 2)
            else:
                amt = self.amount

            res = pd.Series(data=np.full(dates.shape[0], amt), index=dates)
            LOGGER.debug('-' * 50)
            LOGGER.debug(f'Amount: {amt}')
            LOGGER.debug(res.index)

            if self.compile is not None:
                res = res.resample('D').pad()
                LOGGER.debug(f'{res.index[0]} to {res.index[-1]}')
                res = res[self.date:end]
                res = res.resample(self.compile).sum()
                LOGGER.debug(res.index)

            if self.offset > 0:
                freq = self.compile or self.recur
                if freq == 'MS':
                    offset = self.offset - 1
                else:
                    offset = self.offset
                res.index += timedelta(days=offset)
                LOGGER.debug(res.index)

            # prevents dates that are out of range
            res = res[self.date:end]

            # prevents recurring charges compiled based on a number of days from all showing up on the first day
            if 'D' in self.recur or (self.compile is not None and 'D' in self.compile):
                res = res[res.index != self.date]
            return res
        else:
            return pd.Series(data=[self.amount], index=[self.date])

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
        except IndexError:
            compile_period = None

        return Expense(
            name=name,
            amount=round(float(value), 2),
            date=None,
            recur=f'{period}',
            compile=compile_period,
            offset=day_offset,
        )

    def df(self, **kwargs):
        s = self.project(**kwargs)
        df = pd.DataFrame(
            data={
                'Name': np.full(s.shape[0], self.name),
                'Amount': s.values
            },
            index=s.index
        )
        return df

    @property
    def line(self):
        return pd.Series(
            data=[self.name, self.amount],
            index=pd.Index(['Name', 'Amount'], name=self.date)
        )