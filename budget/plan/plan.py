import logging
import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import yaml

from .expense import Expense
from .utils import compare
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

    def category_report(self, name: str, date: str = None) -> pd.DataFrame:
        df = self.data[name]

        if date is not None:
            df = df[date]

        try:
            exp = Expense.from_plan_str(name, self.cfg['Plan'][name])
        except KeyError:
            raise KeyError(f'{name} has nothing planned for it')

        return compare(df, exp.daily)

    def category_plot(self, name: str, date: str = None) -> plt.Figure:
        df = self.category_report(name, date)
        to_plot = df.select_dtypes('number').drop('Amount', axis=1)

        fig, ax = plt.subplots(figsize=(16, 8))
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            ax.plot(to_plot)
        ax.grid(True)
        ax.legend(to_plot.columns)
        return fig
