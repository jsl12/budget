import logging
import warnings
from datetime import datetime, timedelta
from math import ceil
from pathlib import Path

import matplotlib.dates as dates
import matplotlib.pyplot as plt
import numpy as np
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

    def category_report(self, name: str, start_date: datetime = None) -> pd.DataFrame:
        df = self.data[name][start_date or datetime.today().strftime('%Y'):]
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
        fig = self.linear_plot(df, title=f'{cat} Expenses, ${daily}/day', **kwargs)
        return fig, df

    def current(self, cat: str, start_date: str = None) -> float:
        df = self.data[cat]
        df = df[start_date or datetime.today().strftime('%Y'):]

        total = df['Amount'].sum()
        todays_date = datetime.combine(datetime.today(), datetime.min.time())
        elapsed_days = (todays_date - df.index[0]).days
        planned = elapsed_days * self.get_expense(cat).daily
        return round(total - planned, 2)

    def days(self, cat: str, start_date: datetime = None, add: float = 0) -> float:
        """
        Find out how many days ahead/behind you are according to the burn rate for that Expense

        :return:
        """
        daily_burn = self.get_expense(cat).daily
        current = self.current(cat, start_date) + add
        return round(-(current / daily_burn), 1)

    def zero_day(self, cat: str, start_date: datetime = None, add: float = 0) -> datetime:
        return datetime.now() - timedelta(days=self.days(cat, start_date, add))

    def since_last_zero(self, cat:str, start_date: datetime = None) -> pd.DataFrame:
        df = self.data[cat][start_date or datetime.today().strftime('%Y'):]
        daily = self.get_expense(cat).daily
        df = utils.prepare_plot_data(
            df=df,
            daily_spending=daily
        )

        i = df[df['Difference'] >= 0].index[-1]
        return self.data[cat][i:]

    def last_zero_plot(self, cat:str, start_date: datetime = None, extend=False, **kwargs) -> plt.Figure:
        df = self.since_last_zero(cat, start_date)

        if extend:
            extend = self.zero_day(cat, start_date)
        else:
            extend = None

        df = utils.prepare_plot_data(
            df=df,
            daily_spending=self.get_expense(cat).daily,
            extend=extend
        )
        return self.linear_plot(df, title=f'{cat} Spending, ${self.get_expense(cat).daily:.2f}/day', **kwargs)

    @staticmethod
    def linear_plot(df: pd.DataFrame, title:str = None, **kwargs) -> plt.Figure:
        fig, ax = plt.subplots(**kwargs)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            ax.plot(df)

        ax.grid(True)
        ax.legend(df.columns)

        if title is not None:
            ax.set_title(title)

        return fig

    def cat_stat_plot(self, df: pd.DataFrame, freq:str = '1M', title:str = None, **kwargs) -> plt.Figure:
        grouper = pd.Grouper(freq=freq)
        res = df.groupby(grouper).sum()
        res['Count'] = df.groupby(grouper).count().iloc[:, 0]
        res['Mean'] = df.groupby(grouper).mean()
        res['Median'] = df.groupby(grouper).median()
        res = res.applymap(lambda v: abs(round(v, 2)))

        with warnings.catch_warnings():
            warnings.simplefilter('ignore')

            x = np.arange(res.shape[0])
            w = .5

            fig, ax1 = plt.subplots(**kwargs)
            ax2 = ax1.twinx()
            offset = (w / 8) - (w / 2)
            ax1.bar(x + offset, res.iloc[:, 0].values, color='r', width=w/4)
            ax2.bar(x + 1*(w / 4) + offset, res['Count'].values, width=w/4)
            ax2.bar(x + 2*(w / 4) + offset, res['Mean'].values, width=w/4)
            ax2.bar(x + 3*(w / 4) + offset, res['Median'].values, width=w/4)
            ax1.legend(['Amount'], loc='upper left')
            ax2.legend(['Count', 'Mean', 'Median'], loc='upper right')

            ax1.set_xticks(x)
            ax1.set_xticklabels(res.index.to_series().map(lambda v: v.strftime('%B')).values)
            if title is not None:
                ax1.set_title(title)

            ax1.set_ylim(0, ceil(res['Amount'].max() / 500) * 500)
            ax2.set_ylim(0, ceil(res.iloc[:,1:].max().max() / 100) * 100)
            return fig, res

    def cat_bar_plot(self, data: pd.Series, **kwargs) -> plt.Figure:
        data = data.abs()
        fig, ax = plt.subplots(**kwargs)

        ax.grid(True)
        ax.xaxis.set_major_formatter(dates.DateFormatter('%B'))

        total_w = 6
        if isinstance(data, pd.Series):
            ax.set_ylim(0, ceil(data.max() / 100) * 100)
            ax.bar(data.index, data.values, width=total_w)
        elif isinstance(data, pd.DataFrame):
            ax.set_ylim(0, ceil(data.max().max() / 100) * 100)
            for i, c in enumerate(data):
                w = total_w/data.shape[1]
                # offset = -(total_w / (data.shape[1] * 2)) + (i * w)
                offset = 0
                ax.bar(data.index + timedelta(days=int(offset)), data[c].values, width=w)
        return fig