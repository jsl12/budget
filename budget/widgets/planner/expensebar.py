import re
from pathlib import Path

import ipywidgets as widgets
import yaml

from ..components import freq_dropdown
from ..opts import bar_layout
from ...plan import Expense, SimplePlan

days = {
    'MON': 'Monday',
    'TUE': 'Tuesday',
    'WED': 'Wednesday',
    'THU': 'Thursday',
    'FRI': 'Friday',
    'SAT': 'Saturday',
    'SUN': 'Sunday'
}

freq_regex = re.compile('(?P<mult>\d+)?(?P<freq>[\-\w]+)', re.IGNORECASE)


class ExpenseSection(widgets.VBox):
    @staticmethod
    def from_yaml(yaml_path, key='Plan'):
        with Path(yaml_path).open('r') as file:
            cfg = yaml.load(file, Loader=yaml.SafeLoader)[key]
        return ExpenseSection([Expense.from_plan_str(name, s.upper()) for name, s in cfg.items()])

    def __init__(self, expenses = [], **kwargs):
        if 'layout' not in kwargs:
            kwargs['layout'] = bar_layout

        kwargs['children'] = [ExpenseBar.from_obj(e) for e in expenses]

        super().__init__(**kwargs)

    @property
    def plan(self):
        return SimplePlan([e.exp for e in self.children if hasattr(e, 'exp')])

    def project(self, *args, **kwargs):
        return self.plan.project(*args, **kwargs)


class ExpenseBar(widgets.HBox):
    @staticmethod
    def from_obj(expense: Expense):
        return ExpenseBar(
            name=expense.name,
            value=expense.amount,
            freq=expense.recur,
            compile=expense.compile
        )

    def __init__(self, name:str = '', value:float = 0.0, freq = None, compile = None, **kwargs):
        if 'layout' not in kwargs:
            kwargs['layout'] = bar_layout

        self.name_field = widgets.Text(placeholder='Expense Name', value=name, layout={'width': '150px'})
        self.amount_field = widgets.FloatText(value=value, layout={'width': '75px'})
        self.recur_field = freq_dropdown()
        self.compile_field = freq_dropdown()

        kwargs['children'] = [
            self.name_field,
            self.amount_field,
            self.recur_field,
            self.compile_field,
            widgets.Label(
                layout={
                    'display': 'flex',
                    'flex': '1 1',
                    # 'border': 'solid 1px red'
                }
            )
        ]

        super().__init__(**kwargs)

        self.freq = freq

        if compile is not None:
            self.compile = compile
        else:
            self.compile = freq

        for child in self.children[1:5]:
            child.observe(self.text, 'value')
        self.text()

    @property
    def exp(self):
        return Expense(
            name=self.name,
            amount=self.amount,
            recur=self.freq,
            compile=self.compile
        )

    @property
    def project_children(self):
        return [
            self.name_field,
            self.amount_field,
            self.recur_field,
            self.compile_field
        ]

    @property
    def name(self):
        return self.name_field.value

    @property
    def amount(self):
        return self.amount_field.value

    @property
    def freq(self):
        return self.recur_field.value

    @freq.setter
    def freq(self, f):
        if f not in self.recur_field.options:
            self.recur_field.options = list(self.recur_field.options) + [f]
        self.recur_field.value = f

    @property
    def compile(self):
        return self.compile_field.value

    @compile.setter
    def compile(self, f):
        if f is None:
            f = self.freq

        if f not in self.compile_field.options:
            self.compile_field.options = list(self.compile_field.options) + [f]
        self.compile_field.value = f

    @property
    def label(self):
        return self.children[-1]

    def text(self, *args):
        if self.freq is not None:
            m = freq_regex.match(self.freq)
            freq = m.group('freq')
            if 'Y' in freq:
                period = 'year'
            elif 'M' in freq:
                period = 'month'
            elif 'W' in freq:
                period = 'week'
            elif 'D' in freq:
                period = 'day'

            if m.group('mult') is not None:
                period += 's'
                suffix = f'per {m.group("mult")} {period}'
            else:
                suffix = f'per {period}'

            if self.compile is not None:
                m = freq_regex.match(self.compile)
                cfreq = m.group('freq').upper()
                cmult = m.group('mult')
                if cfreq == 'Y':
                    if cmult is not None:
                        comp = f'every {cmult} years'
                    else:
                        comp = f'every year'
                elif cfreq == 'MS':
                    comp = 'at the start of the month'
                elif cfreq == 'M':
                    comp = 'at the end of the month'
                elif 'W' in cfreq:
                    if len(cfreq) > 1:
                        comp = f'on {days[cfreq[-3:]]}'
                        if 'W' not in freq:
                            comp += 's'
                    elif cmult is not None:
                        comp = f'every {cmult} weeks'
                    else:
                        comp = f'every week'
                elif cfreq == 'D':
                    if cmult is not None:
                        comp = f'every {cmult} days'
                    else:
                        comp = f'every day'
                else:
                    raise ValueError(f'problem parsing compile freq: {cfreq}')

                if comp != '':
                    comp = f', charged {comp}'
            else:
                comp = ''

            self.label.value = f'${self.amount:.02f} {suffix}{comp}'
        else:
            self.label.value = f'${self.amount:.02f} one time expense'

