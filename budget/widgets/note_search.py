import ipywidgets as widgets
import pandas as pd
import qgrid

from .opts import qgrid_opts, bar_layout
from ..data import BudgetData


class NoteSearch(widgets.VBox):
    def __init__(self, bd: BudgetData, *args, **kwargs):
        self.bd = bd
        kwargs['children'] = [
            widgets.HBox(
                children=[
                    widgets.Label('Search regex'),
                    widgets.Text(placeholder='Type a regex here')
                ],
                layout=bar_layout
            ),
            widgets.Output(),
            qgrid.show_grid(self.bd.df_note_search(''), **qgrid_opts)
        ]
        super().__init__(*args, **kwargs)
        self.children[0].children[-1].observe(self.render, 'value')

    @property
    def search(self):
        return self.children[0].children[-1]

    @property
    def table(self):
        return self.children[-1]

    @property
    def output(self):
        return self.children[1]

    def render(self, *args):
        query = self.search.value
        df = self.bd.df_note_search(query)
        if df is not None:
            self.table.df = df
        else:
            self.table.df = pd.DataFrame(columns=self.bd.df.columns)
