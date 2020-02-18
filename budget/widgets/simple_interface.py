from dataclasses import dataclass

import ipywidgets as widgets
import numpy as np
import pandas as pd
import qgrid
from ipywidgets import Layout as ly

from . import bars, utils
from .opts import qgrid_opts
from ..data import BudgetData

button_layout = {
    'width':  '100px'
}


@dataclass
class SimpleInterface:
    bd: BudgetData
    col_order = ['Account', 'Amount', 'Category', 'Description', 'id']

    def __post_init__(self):
        self.bd.RENDER_DROP_ID_COL = False

        self.buttons = widgets.HBox([
            widgets.ToggleButton(value=True, description='Unmatched', layout=button_layout),
            widgets.ToggleButton(value=False, description='Apply Notes', layout=button_layout),
            widgets.Button(description='Render', layout=button_layout),
            widgets.Button(description='Save SQL', layout=button_layout),
            widgets.Button(description='Reload CSVs', layout=button_layout),
            ],
            layout=ly(
                display='flex',
                flex_flow='row wrap',
                # border='solid 1px red'
            )
        )

        self.render_button.on_click(
            lambda *args: self.print_output(self.render)
        )
        self.save_button.on_click(
            lambda *args: self.print_output(utils.save, self.bd)
        )
        self.reload_csv_button.on_click(
            lambda *args: self.print_output(utils.reload, self.bd)
        )

        self.search = bars.RegexSearchBar()
        self.search.observe(
            lambda *args: self.print_output(self.render),
            'value'
        )

        self.manual_note = bars.ManualCategoryBar(self.bd)
        self.manual_note.button.on_click(
            lambda *args: self.print_output(self.manual_note.add_note, self.sel)
        )

        self.custom_note = bars.CustomNoteBar(self.bd)
        self.custom_note.button.on_click(
            lambda *args: self.print_output(self.custom_note.add_note, self.sel)
        )

        self.output = widgets.Output()
        self.table = qgrid.show_grid(pd.DataFrame(columns=self.bd._df.columns), **qgrid_opts)
        self.table.on('selection_changed', self.show_relevant_notes)

        self.id_bar = bars.IDBar()
        self.id_bar.button.on_click(
            lambda *args: self.print_output(utils.copy_id, self.sel)
        )
        self.id_bar.children[-1].on_click(
            lambda *args: self.print_output(self.drop_selected_note, self.note_table.get_selected_df())
        )

        self.note_table =   qgrid.show_grid(self.bd.df_note_search('')[self.col_order[:-1] + ['Note']], **qgrid_opts)

        self.interface = widgets.VBox(
            children=[
                self.controls,
                self.output,
                self.table,
                self.id_bar,
                self.note_table
            ],
            layout=ly(display='flex')
        )

        self.render()

    def print_output(self, func, *args):
        """
        Used to wrap callback functions so that they print to the Output object
        :param func:
        :param args:
        :return:
        """
        with self.output:
            func(*args)

    @property
    def bars(self):
        return widgets.VBox(
            children=[
                self.search,
                self.manual_note,
                self.custom_note,
            ],
            layout=ly(
                display='flex',
                flex='0 0 470px',
                align_items='stretch',
                padding='10px'
            )
        )

    @property
    def controls(self):
        return widgets.HBox(
            children=[
                self.bars,
                self.buttons
            ]
        )

    def render(self):
        if self.unsel_toggle.value:
            m = self.bd.unselected
        else:
            m = pd.Series(
                data=np.ones(self.bd.df.shape[0], dtype=bool),
                index=self.bd.df.index
            )

        try:
            if self.search.value != '':
                m &= self.bd.search(self.search.value)
        except:
            print(f'error searching')
        else:
            if self.note_toggle.value:
                df = self.bd[m]
            else:
                df = self.bd._df[m]
            self.table.df = df[::-1][self.col_order].copy()

    def show_relevant_notes(self, *args):
        cols = self.col_order[:]
        cols.insert(-1, 'Note')
        self.note_table.df = self.bd.note_df(self.sel)[cols]

        if self.sel.shape[0] > 0:
            self.id_bar.value = self.sel['id'][0]

    def drop_selected_note(self, df: pd.DataFrame):
        for date, row in df.iterrows():
            self.bd.note_manager.drop(row['id'], row['Note'])
        self.show_relevant_notes()

    @property
    def sel(self) -> pd.DataFrame:
        return self.table.get_selected_df()

    @property
    def df(self) -> pd.DataFrame:
        return self.table.get_changed_df()

    @property
    def unsel_toggle(self) -> widgets.ToggleButton:
        return self.buttons.children[0]

    @property
    def note_toggle(self) -> widgets.ToggleButton:
        return self.buttons.children[1]

    @property
    def render_button(self) -> widgets.Button:
        return self.buttons.children[2]

    @property
    def save_button(self) -> widgets.Button:
        return self.buttons.children[-2]

    @property
    def reload_csv_button(self) -> widgets.Button:
        return self.buttons.children[-1]
