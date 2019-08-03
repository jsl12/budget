from dataclasses import dataclass

import ipywidgets as widgets
import pandas as pd
import qgrid

from budget import BudgetData


@dataclass
class NoteSearch:
    bd: BudgetData

    def __post_init__(self):
        self.interface = widgets.VBox([
            widgets.Text(description='Regex: ', placeholder='Type a regex here'),
            widgets.Output(),
            qgrid.show_grid(self.bd.df_note_search(''))
        ])

        def render_wrapper(change_dict):
            self.render()

        self.interface.children[0].observe(render_wrapper, names='value')

    @property
    def table(self):
        return self.interface.children[-1]

    def render(self):
        df = self.bd.df_note_search(self.interface.children[0].value)
        if df is not None:
            self.table.df = df
        else:
            self.table.df = pd.DataFrame(columns=self.bd.df.columns)
