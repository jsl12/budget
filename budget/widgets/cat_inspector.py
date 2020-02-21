import ipywidgets as widgets
import pandas as pd
import qgrid
from IPython.display import clear_output

from .components import freq_dropdown
from .opts import qgrid_opts, bar_layout
from ..data import BudgetData


class CatInspector(widgets.VBox):
    def __init__(self, bd: BudgetData, cats=None, **kwargs):
        self.bd = bd

        if not hasattr(self.bd, '_df'):
            self.bd.load_sql()

        if cats is None:
            cats = bd._sel.columns.tolist()

        qgrid_opts['column_definitions']['Description']['width'] = 150
        qgrid_opts['grid_options']['forceFitColumns'] = True

        kwargs['children'] = [
            widgets.HBox(
                children=[
                    freq_dropdown(),
                    widgets.Dropdown(
                        options=cats,
                        value=cats[0],
                        layout={'width': '300px'}
                    ),
                    widgets.ToggleButton(
                        description='Apply Notes',
                        value=True
                    )
                ]
            ),
            widgets.HBox(
                children=[
                    widgets.Box(
                        children=[
                            qgrid.show_grid(pd.DataFrame(columns=bd.df.columns), **qgrid_opts),
                        ],
                        layout={
                            'display': 'flex',
                            'width': '200px',
                            'padding': '5px'
                        }
                    ),
                    widgets.Box(
                        children=[
                            qgrid.show_grid(pd.DataFrame(columns=bd.df.columns), **qgrid_opts),
                        ],
                        layout={
                            'display': 'flex',
                            'flex': '1 1',
                            'width': 'auto',
                            'padding': '5px'
                        }
                    ),
                ]
            ),
            widgets.Output()
        ]

        if 'layout' not in kwargs:
            bar_layout['flex_flow'] = 'row wrap'
            kwargs['layout'] = bar_layout
        super().__init__(**kwargs)

        for child in self.children[0].children:
            child.observe(self.show_report, 'value')
        self.report.on('selection_changed', self.show_transactions)

        self.show_report()

    @property
    def freq(self):
        return self.children[0].children[0].value

    @property
    def selected_cat(self):
        return self.children[0].children[1].value

    @property
    def note_button(self):
        return self.children[0].children[2].value

    @property
    def report(self):
        return self.children[1].children[0].children[0]

    @property
    def transactions(self):
        return self.children[1].children[1].children[0]

    @property
    def output(self):
        return self.children[-1]

    def show_report(self, *args):
        if self.note_button:
            df = self.bd[self.selected_cat]
        else:
            df = self.bd.df[self.bd._sel[self.selected_cat]]
        grouped = df.groupby(pd.Grouper(freq=self.freq))
        self.groups = {date: df for date, df in grouped}
        self.report.df = grouped.sum().sort_index(ascending=False)
        self.report.change_selection()

    def show_transactions(self, *args):
        idx = self.report.get_selected_df().index
        try:
            res = pd.concat([self.groups[i] for i in idx]).sort_index()
        except ValueError:
            with self.output:
                clear_output()
                print(f'Nothing selected')
        else:
            if 'id' in res.columns:
                res = res.drop('id', axis=1)
            self.transactions.df = res.sort_index(ascending=False)
            with self.output:
                clear_output()
                print(f'Total: {res["Amount"].sum():.2f}')