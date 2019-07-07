import budget
import datetime
import numpy as np
import pandas as pd

def gen_bd():
    bd = budget.BudgetData('test')
    bd._df = pd.DataFrame(
        data={
            'Description': [f'Transaction #{i}' for i in range(4)],
            'Amount': [-50.0, -13.50, 500, -200]
        },
        index=pd.Index(
            data=pd.date_range(datetime.datetime.today(), periods=4),
            name='Date'
        )
    )
    bd._df = bd.hash_transactions()
    bd._sel = pd.DataFrame(
        data=np.array([
            [True, False],
            [False, False],
            [False, True],
            [False, False]
        ]),
        index=bd._df.index,
        columns=[chr(ord('A') + i) for i in range(2)]
    )
    return bd