from dataclasses import dataclass

import ipywidgets as widgets
from ipywidgets import Layout as ly
import pandas as pd
import pyperclip
import qgrid

from budget import BudgetData
from .. import utils


@dataclass
class SimpleInterface:
    bd: BudgetData

    def __post_init__(self):

        self.options = widgets.HBox([
            widgets.Button(description='Render', layout=ly(width='80px')),
            widgets.ToggleButton(value=True, description='Unmatched', layout=ly(width='100px')),
            widgets.ToggleButton(value=False, description='Notes', layout=ly(width='80px')),
            widgets.Button(description='Save SQL', layout=ly(width='80px')),
            widgets.Button(description='Reload CSVs', layout=ly(width='100px')),
            widgets.Button(description='Copy ID', layout=ly(width='80px'))
            ],
            layout=ly(justify_content='flex-start')
        )

        self.search = widgets.Text(placeholder='Type a regex here')

        cats = self.bd._sel.columns.tolist()
        self.manual_note = widgets.HBox([
            widgets.Button(description='Manually Categorize'),
            widgets.Dropdown(options=cats, value=cats[0], layout=ly(width='200px')),
        ], layout=ly(flex='1 1 auto'))

        self.custom_note = widgets.HBox([
            widgets.Button(description='Add Custom Note'),
            widgets.Text(placeholder='keyword: data', layout=ly(flex='1 1 auto')),
        ], layout=ly(flex='1 1 auto'))

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
        self.reload_csv_button.on_click(reload)

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

        def copy(b):
            with self.output:
                try:
                    id = utils.hash(self.sel.iloc[0])
                    print(f'Copied ID: {id}')
                    pyperclip.copy(id)
                except:
                    print()
        self.copy_button.on_click(copy)

        def render(b):
            with self.output:
                try:
                    self.render()
                except:
                    print('Error rendering DataFrame')
        self.render_button.on_click(render)
        self.unsel_toggle.observe(render, 'value')
        self.note_toggle.observe(render, 'value')
        self.search.observe(render, 'value')

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
            if self.note_toggle.value:
                self.table.df = self.bd[m][::-1]
            else:
                self.table.df = self.bd.df[m][::-1]

    @property
    def sel(self) -> pd.DataFrame:
        return self.table.get_selected_df()

    @property
    def df(self) -> pd.DataFrame:
        return self.table.get_changed_df()

    @property
    def manual_add_button(self) -> widgets.Button:
        return self.manual_note.children[0]

    @property
    def cat_selection(self) -> widgets.Dropdown:
        return self.manual_note.children[1].value

    @property
    def custom_note_button(self) -> widgets.Button:
        return self.custom_note.children[0]

    @property
    def cust_note_text(self) -> widgets.Text:
        return self.custom_note.children[1].value

    @property
    def render_button(self) -> widgets.Button:
        return self.options.children[0]

    @property
    def unsel_toggle(self) -> widgets.ToggleButton:
        return self.options.children[1]

    @property
    def note_toggle(self) -> widgets.ToggleButton:
        return self.options.children[2]

    @property
    def reload_csv_button(self) -> widgets.Button:
        return self.options.children[-2]

    @property
    def save_button(self) -> widgets.Button:
        return self.options.children[-3]

    @property
    def copy_button(self) -> widgets.Button:
        return self.options.children[-1]
