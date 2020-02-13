import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Dict

import pandas as pd

from .expense import Expense

logger = logging.getLogger(__name__)


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

    def linearize(self, start: datetime = None, end: datetime = None, freq='1D') -> pd.DataFrame:
        return self.project(start, end).reset_index().drop_duplicates(['Date'], keep='last').set_index('Date')['Total'].asfreq(freq, method='pad')

    def project(self, start: datetime = None, end: datetime = None) -> pd.DataFrame:
        if start is None:
            start = datetime.combine(datetime.today().date(), datetime.min.time())

        if isinstance(end, int):
            end = start + timedelta(days=end)

        df = pd.concat([e.df(end=end) for e in self.exp], sort=False).sort_index()[start:end]

        df['Total'] = df['Amount'].cumsum()
        return df

    def add_cfg(self, input: Dict):
        for cat, s in input.items():
            self.add_expense(Expense.from_plan_str(cat, s))
