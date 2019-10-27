import pandas as pd
import pyperclip

from ..data import BudgetData
from ..utils import hash


def try_dec(func):
    def wrapper_try_dec(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except:
            print('Fail')
        else:
            print('Success')
    return wrapper_try_dec


@try_dec
def reload(bd: BudgetData):
    print(f'Loading CSV files')
    bd.load_csv()

    print('Processing categories')
    bd.process_categories()


@try_dec
def save(bd: BudgetData):
    print('Saving to SQL file')
    bd.save_sql()


@try_dec
def copy_id(df: pd.DataFrame):
    if df.shape[0] == 1:
        try:
            id = hash(df.iloc[0])
            pyperclip.copy(id)
        except Exception as e:
            print(repr(e))
        else:
            print(f'Copied ID: {id}')
    else:
        print(f'{df.shape[0]} rows selected. Select 1 and only 1')
