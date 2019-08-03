from dataclasses import dataclass
from typing import Dict

import ipywidgets as widgets
import pandas as pd
import qgrid

from budget import BudgetData


@dataclass
class SimpleInterface:
    bd: BudgetData

    def __post_init__(self):
        self.options = widgets.HBox([
            widgets.ToggleButton(value=True, description='Unmatched only'),
            widgets.Button(description='Save SQL'),
            widgets.Button(description='Reload CSVs')
        ])

        self.search = widgets.Text(description='Regex:', placeholder='Type a regex here')

        cats = self.bd._sel.columns.tolist()
        self.manual_note = widgets.HBox([
            widgets.Dropdown(options=cats, value=cats[0], description='Category:'),
            widgets.Button(description='Add Manual Category')
        ])

        self.custom_note = widgets.HBox([
            widgets.Text(description='Custom:', placeholder='Custom note'),
            widgets.Button(description='Add Custom Note')
        ])

        self.connect_handlers()
        self.output = widgets.Output()
        self.table = qgrid.show_grid(self.bd.df[self.bd.unselected][::-1])

    @property
    def interface(self):
        return widgets.VBox([
            self.options,
            self.search,
            self.manual_note,
            self.custom_note,
            self.output,
            self.table
        ])

    def connect_handlers(self):
        def save(b):
            with self.output:
                try:
                    self.bd.save_sql()
                except:
                    print(f'Error saving to {self.bd.db_path}')
                else:
                    print(f'Saved to {self.bd.db_path.name}')
        self.save_button.on_click(save)

        def reload(b):
            with self.output:
                try:
                    print(f'Reloading CSV files...')
                    self.bd.load_csv()
                    print(f'Processing categories')
                    self.bd.process_categories()
                except:
                    print(f'Failed')
                else:
                    print(f'Done')
                    self.render()
        self.reload_button.on_click(reload)

        def manual_note(b):
            with self.output:
                try:
                    n = f'cat: {self.cat_selection}'
                    selection = self.sel
                    self.bd.add_note(selection, n)
                except:
                    print(f'failed to add note: {n}')
                else:
                    print(f'Added \'{n}\' to {selection.shape[0]} transactions')
                    self.render()
        self.manual_add_button.on_click(manual_note)

        def custom_note(b):
            with self.output:
                try:
                    n = self.cust_note_text
                    selection = self.sel
                    self.bd.add_note(selection, n)
                except:
                    print(f'failed to add note: {n}')
                else:
                    print(f'Added \'{n}\' to {selection.shape[0]} transactions')
        self.custom_note_button.on_click(custom_note)

        def simple_handle(change_dict):
            with self.output:
                self.render()
        self.unsel_toggle.observe(simple_handle, names='value')
        self.search.observe(simple_handle, names='value')

    def render(self):
        if self.unsel_toggle.value:
            m = self.bd.unselected
        else:
            m = pd.Series(
                data=[True] * self.bd.df.shape[0],
                index=self.bd.df.index
            )

        try:
            m &= self.bd.search(self.search.value)
        except:
            print(f'error searching')
        else:
            self.table.df = self.bd.df[m][::-1]

    @property
    def sel(self):
        return self.table.get_selected_df()

    @property
    def df(self):
        return self.table.get_changed_df()

    @property
    def cat_selection(self):
        return self.manual_note.children[0].value

    @property
    def manual_add_button(self):
        return self.manual_note.children[1]

    @property
    def custom_note_button(self):
        return  self.custom_note.children[1]

    @property
    def cust_note_text(self):
        return self.custom_note.children[0].value

    @property
    def unsel_toggle(self):
        return self.options.children[0]

    @property
    def save_button(self):
        return self.options.children[1]

    @property
    def reload_button(self):
        return self.options.children[2]