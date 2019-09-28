import logging
import warnings
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import yaml

from . import utils
from .expense import Expense
from ..data import BudgetData

logger = logging.getLogger(__name__)


class BudgetPlan:
    def __init__(self, yaml_path: str):
        self.yaml_path = Path(yaml_path)
        self.data = BudgetData(yaml_path)
        if self.data.db_path.exists():
            self.data.load_sql()

    @property
    def cfg(self):
        with self.yaml_path.open('r') as file:
            return yaml.load(file, Loader=yaml.SafeLoader)

    @property
    def daily(self):
        p = self.cfg['Plan']
        return round(sum([Expense.from_plan_str(name, p[name]).daily for name in p]), 2)

    @property
    def weekly(self):
        return round(self.daily * 7, 2)

    @property
    def monthly(self):
        return round(self.daily * 31, 2)

    def category_report(self, name: str, date: str = None) -> pd.DataFrame:
        df = self.data[name]

        if date is not None:
            df = df[date:]

        return utils.compare(df, self.get_expense(name).daily)

    def get_expense(self, name: str) -> Expense:
        try:
            return Expense.from_plan_str(name, self.cfg['Plan'][name])
        except KeyError:
            raise KeyError(f'{name} has nothing planned for it')

    def category_plot(self, cat: str, start_date: str = None, end_date: str = None, extend=False, **kwargs) -> plt.Figure:
        df = self.data[cat]

        this_year = datetime.today().strftime('%Y')
        start_date = start_date or this_year
        end_date = end_date or this_year
        df = df[start_date:end_date]

        daily = self.get_expense(cat).daily
        if extend:
            extend = datetime.today()
        else:
            extend = None
        df = utils.prepare_plot_data(df, daily, extend=extend)

        fig, ax = plt.subplots(**kwargs)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            ax.plot(df)
        ax.grid(True)
        ax.legend(df.columns)
        ax.set_title(f'{cat} Expenses, ${daily}/day')
        return fig

    def current(self, cat: str, start_date: str = None) -> float:
        df = self.data[cat]
        df = df[start_date or datetime.today().strftime('%Y'):]

        total = df['Amount'].sum()
        todays_date = datetime.combine(datetime.today(), datetime.min.time())
        elapsed_days = (todays_date - df.index[0]).days
        planned = elapsed_days * self.get_expense(cat).daily
        return round(total - planned, 2)

    def days(self, cat: str, start_date: datetime = None) -> float:
        """
        Find out how many days ahead/behind you are according to the burn rate for that Expense

        :return:
        """
        daily_burn = self.get_expense(cat).daily
        current = self.current(cat, start_date)
        return round(-(current / daily_burn), 1)