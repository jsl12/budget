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
            start = datetime.today()
        start = datetime.combine(start, datetime.min.time())

        if isinstance(end, int):
            end = start + timedelta(days=end)

        repeating = [e for e in self.exp
            if e.date is None or e.recur is not None]
        within_dates = self.exp[~self.exp.index.isna()][start:end].tolist()
        all_expenses = []
        for e in (repeating + within_dates):
            if e.recur is not None:
                all_expenses.extend(e.project(e.date or start, end))
            else:
                all_expenses.append(e)

        df = pd.DataFrame(
            data={
                'Name': [e.name for e in all_expenses],
                'Amount': [e.amount for e in all_expenses],
                'Date': [e.date for e in all_expenses]
            }
        ).drop_duplicates()
        df = df.set_index('Date').sort_index()
        df['Total'] = df['Amount'].cumsum()
        return df

    def add_cfg(self, input: Dict):
        for cat, s in input.items():
            self.add_expense(Expense.from_plan_str(cat, s))
