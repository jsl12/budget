from dataclasses import dataclass

import ipywidgets as widgets
from IPython.display import clear_output

from budget import BudgetPlan


@dataclass
class SimplePlotter:
    bp: BudgetPlan

    def __post_init__(self):
        cats = list(self.bp.cfg['Plan'].keys())
        self.plotter = widgets.HBox([
            widgets.Dropdown(options=cats, value=cats[0], description='Category:'),
            widgets.DatePicker(description='Start Date'),
            widgets.DatePicker(description='End Date')
        ])
        self.output = widgets.Output()

        def plot(change_dict):
            nonlocal self
            with self.output:
                print(f'Loading...')

            with self.output:
                clear_output()
                fig, df = self.bp.category_plot(
                    cat=self.plotter.children[0].value,
                    start_date=self.plotter.children[1].value,
                    end_date=self.plotter.children[2].value,
                    figsize=(9.6, 5.4)
                )
                display(fig)
                self.df = df

        for c in self.plotter.children:
            c.observe(plot, names='value')

    @property
    def interface(self):
        return widgets.VBox([self.plotter, self.output])
