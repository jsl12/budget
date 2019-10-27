import ipywidgets as widgets
import pandas as pd

from ..data import BudgetData

bar_layout = {
    'display': 'flex',
    'width': 'auto',
    'padding': '5px'
}

field_layout = {
    'display': 'flex',
    'flex': '1 1'
}


class RegexSearchBar(widgets.Text):
    def __init__(self, **kwargs):
        kwargs['placeholder'] = 'Type a regex here'

        if 'layout' not in kwargs:
            kwargs['layout'] = {
                'display': 'flex',
                'width': 'auto',
            }

        super().__init__(**kwargs)


class ButtonBar(widgets.HBox):
    def __init__(self, **kwargs):
        if 'layout' not in kwargs:
            kwargs['layout'] = bar_layout
        super().__init__(**kwargs)

    @property
    def button(self):
        return self.children[0]

    @property
    def value(self):
        return self.children[-1].value

    def add_note(self, selected_df: pd.DataFrame):
        size = selected_df.shape[0]
        if size == 0:
            print('No transactions selected')
        else:
            note = self.note if hasattr(self, 'note') else self.value
            try:
                self.bd.add_note(selected_df, note)
            except Exception as e:
                print(f"Failed to add '{note}' to {size} transactions")
            else:
                print(f"Addded '{note}' to {size} transactions")


class ManualCategoryBar(ButtonBar):
    def __init__(self, bd: BudgetData, **kwargs):
        self.bd = bd
        categories = bd._sel.columns.tolist()

        kwargs['children'] = [
            widgets.Button(description='Manually Categorize'),
            widgets.Dropdown(
                options=categories,
                value=categories[0],
                layout=field_layout
            )
        ]

        super().__init__(**kwargs)

    @property
    def note(self):
        return f'cat: {self.value}'


class CustomNoteBar(ButtonBar):
    def __init__(self, bd: BudgetData, **kwargs):
        self.bd = bd

        kwargs['children'] = [
            widgets.Button(description='Add Custom Note'),
            widgets.Text(
                placeholder='keyword: data',
                layout=field_layout
            )
        ]

        super().__init__(**kwargs)


class IDBar(ButtonBar):
    def __init__(self, **kwargs):
        kwargs['children'] = [
            widgets.Text(
                description='Selected ID',
                placeholder='None selected',
                layout={'width': '350px'}
            ),
            widgets.Button(description='Copy', layout={'width': '100px'}),
            widgets.Button(description='Delete Note', layout={'width': '100px'})
        ]

        super().__init__(**kwargs)

    @property
    def button(self):
        return self.children[1]

    @property
    def value(self):
        return self.children[0].value

    @value.setter
    def value(self, val):
        self.children[0].value = val