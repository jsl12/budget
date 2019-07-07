import logging
import re
import pandas as pd
from dataclasses import dataclass
from typing import List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

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
            # self.date = self.date.replace(hour=0, minute=0, second=0, microsecond=0)

    def project(self, future_date):
        try:
            dates = pd.date_range(
                start=self.date,
                end=future_date,
                freq=self.recur,
                closed='left'
            )
            res = pd.Series(
                data=[Expense(self.name, self.amount, d.to_pydatetime()) for d in dates],
                index=dates
            )
        except AttributeError:
            return
        else:
            logger.debug(f'projected {res.shape[0]} {self.name} expenses')
            return res


@dataclass
class SimplePlan:
    initial_expenses: List[Expense]

    def __post_init__(self):
        self.exp = pd.Series(
            data=self.initial_expenses,
            index=pd.Index(
                data=[e.date for e in self.initial_expenses],
                name='Date'
            )
        ).sort_index()

    @property
    def df(self) -> pd.DataFrame:
        return pd.DataFrame(
            data=[{
                'Name': e.name,
                'Amount': float(e.amount),
                'Freq': getattr(e, 'recur', '')
            } for e in self.exp],
            index=pd.Index(
                data=[e.date for e in self.exp],
                name='Date'
            )
        )

    def add_expense(self, exp: Expense) -> None:
        try:
            self.exp = self.exp.append(pd.Series([exp], index=pd.Index([exp.date]))).sort_index()
        except:
            print(f'failed to add expense: {exp}')
        return

    def print_exp(self):
        for e in self.exp:
            print(f' {e.name} '.center(50, '-'))
            s = f'{e.date.strftime("%Y-%m-%d"):15}{str(e.amount):10}'
            if e.recur is not None:
                s += e.recur
            print(s)

    def linearize(self, future_date: datetime, freq='1D') -> pd.DataFrame:
        return self.project(future_date).reset_index().drop_duplicates(['Date'], keep='last').set_index('Date')['Total'].asfreq(freq, method='pad')

    def project(self, future_date: datetime) -> pd.Series:
        todays_date = datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
        relevant = self.exp[todays_date:future_date]
        recurring = relevant.apply(lambda e: e.recur is not None)
        all_expenses = pd.concat([relevant[~recurring]] + [e.project(future_date) for e in relevant[recurring]]).sort_index()

        df = pd.DataFrame(
            data={
                'Name': all_expenses.map(lambda e: e.name).values,
                'Amount': all_expenses.map(lambda e: e.amount).values,
                'Total': all_expenses.map(lambda e: e.amount).cumsum().values,
            },
            index=pd.Index(
                data=all_expenses.map(lambda e: e.date).values,
                name='Date'
            )
        )
        return df

def parse_date(input: str) -> datetime:
    patterns = [
        '%Y-%m-%d',
        '%m/%d/%Y',
        '%m/%d',
        '%m-%d'
    ]
    for p in patterns:
        try:
            res = datetime.strptime(input, p)
            if res.year < 2000:
                res = res.replace(year=datetime.today().year)
        except ValueError:
            pass
        else:
            return res
    raise ValueError(f'input \'{input}\' does not match any patterns')

def date_range(start: datetime, end: datetime, freq: str) -> pd.DatetimeIndex:
    m = re.match('^(?P<num>\d+)(?P<unit>[MWD])$', freq.upper())
    if m is None:
        raise ValueError(f'invalid freq: {freq}')
    elif m.group('unit') == 'M':
        return month_range_day(
            start=start,
            periods=int((end - start).days / 30)+1,
            num=int(m.group('num'))
        )
    elif m.group('unit') == 'W':
        return pd.date_range(
            start=start,
            end=end,
            freq=f'{int(m.group("num"))*7}D'
        )
    elif m.group('unit') == 'D':
        return pd.date_range(
            start=start,
            end=end,
            freq=freq
        )

def month_range_day(start: datetime, periods: int, num: int = 1):
    return pd.DatetimeIndex(
        data=[(dt.replace(day=start.day) if dt.day > start.day else dt)
                for dt in pd.date_range(start=start, periods=periods, freq=f'{num}M')]
    )
