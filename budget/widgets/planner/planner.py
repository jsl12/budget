from pathlib import Path

import ipywidgets as widgets
import matplotlib.pyplot as plt
import pandas as pd
import qgrid
import yaml
from IPython.display import display, clear_output
from pandas.plotting import register_matplotlib_converters

from .expensebar import ExpenseSection, ExpenseBar
from ..opts import bar_layout
from ...plan import Expense
from ...plan import SimplePlan


class Planner(widgets.VBox):
    @staticmethod
    def from_yaml(yaml_path, key ='Plan', **kwargs):
        with Path(yaml_path).open('r') as file:
            cfg = yaml.load(file, Loader=yaml.SafeLoader)[key]
        return Planner(
            expenses=[Expense.from_plan_str(name, s.upper()) for name, s in cfg.items()]
        )

    def __init__(self, expenses = None, **kwargs):
        if 'layout' not in kwargs:
            kwargs['layout'] = {
                'width': 'auto'
            }

        if expenses is not None and all([isinstance(e, Expense) for e in expenses]):
            self.expense_section = ExpenseSection(expenses=expenses)
        else:
            self.expense_section = ExpenseSection()

        kwargs['children'] = [
            self.expense_section,
            widgets.Button(description='Add Expense'),
            widgets.HBox(
                children=[
                    widgets.Label('Projection Length'),
                    widgets.IntText(value=90, layout={'width': '100px'}),
                    widgets.Button(description='Plot', layout={'width': '60px'})
                ],
                layout=bar_layout
            ),
            qgrid.show_grid(pd.DataFrame()),
            widgets.Output()
        ]

        super().__init__(**kwargs)
        self.project()

        self.setup_expense_bar()
        self.children[1].on_click(self.add_expense)
        self.children[2].children[1].observe(self.project, 'value')
        self.children[2].children[2].on_click(self.plot)

    def project(self, *args):
        if len(self.expense_section.children) > 0:
            self.children[3].df = self.expense_section.project(end=self.projection_length)

    def plot(self, *args):
        if len(self.expense_section.children) > 0:
            with self.output:
                df = self.table.get_changed_df().sort_index()
                df = df.drop('Total', axis=1).sort_index().groupby(level=0).sum()
                df['Total'] = df['Amount'].cumsum()

                if not hasattr(self, 'fig'):
                    register_matplotlib_converters()
                    self.fig, self.ax = plt.subplots(figsize=(19.2, 10.8))
                else:
                    self.ax.clear()
                self.ax.grid(True)
                self.ax.plot(
                    df.index.to_pydatetime(),
                    df['Total'].values
                )

                clear_output()
                display(self.fig)


    @property
    def projection_length(self):
        return self.children[2].children[1].value

    @property
    def plan(self) -> SimplePlan:
        return self.children[0].plan

    @property
    def table(self):
        return self.children[-2]

    @property
    def output(self):
        return self.children[-1]

    def add_expense(self, *args):
        exp = self.expense_section.children
        new = ExpenseBar()
        new.children = [self.remove_button_factory()] + list(new.children)
        for child in new.project_children:
            child.observe(self.project, 'value')
        self.expense_section.children = list(exp) + [new]

    def remove_expense(self, *args):
        self.expense_section.children = [bar for bar in self.expense_section.children if not bar.children[0].value]

    def setup_expense_bar(self):
        for bar in self.expense_section.children:
            bar.children = [self.remove_button_factory()] + list(bar.children)
            for child in bar.project_children:
                child.observe(self.project, 'value')

    def remove_button_factory(self):
        remove_button = widgets.ToggleButton(description='-', layout={'width': '15px'})
        remove_button.observe(self.remove_expense, 'value')
        return remove_button