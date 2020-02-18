from datetime import datetime

import numpy as np
import pandas as pd

from budget import BudgetData


def gen_bd():
    bd = BudgetData('test')
    bd._df = pd.DataFrame(
        data={
            'Description': [f'Transaction #{i}' for i in range(4)],
            'Amount': [-50.0, -13.50, 500, -200]
        },
        index=pd.Index(
            data=pd.date_range(datetime.today(), periods=4),
            name='Date'
        )
    )
    bd._df = bd.hash_transactions()
    bd._sel = pd.DataFrame(
        data=np.array([
            [True, False, False],
            [False, False, False],
            [False, True, False],
            [False, False, False]
        ]),
        index=bd._df.index,
        columns=[chr(ord('A') + i) for i in range(3)]
    )
    bd._df['Category'] = bd.categorization
    return bd