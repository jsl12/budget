import re
from datetime import datetime, timedelta

import numpy as np
import pandas as pd


def prepare_plot_data(df: pd.DataFrame, daily_spending: float, extend: datetime = None) -> pd.DataFrame:
    df['Total'] = df['Amount'].cumsum()
    df = df.select_dtypes('number').drop('Amount', axis=1)
    df = df.reset_index().drop_duplicates(df.index.name, keep='last').set_index(df.index.name)

    if extend is not None:
        df.loc[extend] = 0

    df = df.asfreq('1D', 'pad')
    df['Planned'] = np.nan
    df['Planned'].iloc[0] = 0
    df['Planned'].iloc[-1] = (df.index[-1] - df.index[0]).days * daily_spending
    df['Planned'] = df['Planned'].interpolate()
    df['Difference'] = df['Total'] - df['Planned']
    return df


def compare(df: pd.DataFrame, daily_spending: float) -> pd.DataFrame:
    """
    Compares a planned amount of daily spending to actual transactions

    :param df: DataFrame of transactions
    :param daily_spending: planned amount of spending for each day
    :return: DataFrame with added columns: Total, Planned, and Difference
    """
    df['Total'] = df['Amount'].cumsum()
    df['Planned'] = df.apply(lambda r: round((r.name - df.index[0]).days * daily_spending, 2), axis=1)
    df['Difference'] = df['Total'] - df['Planned']
    return df


def parse_date(input_str: str) -> datetime:
    patterns = [
        '%Y-%m-%d',
        '%m/%d/%Y',
        '%m/%d',
        '%m-%d'
    ]
    for p in patterns:
        try:
            res = datetime.strptime(input_str, p)
            if res.year < 2000:
                res = res.replace(year=datetime.today().year)
        except ValueError:
            pass
        else:
            return res
    raise ValueError(f'input \'{input_str}\' does not match any patterns')


def date_range(start: datetime, end: datetime, freq: str, day_offset: int = None) -> pd.DatetimeIndex:
    if start is None:
        start = datetime.combine(datetime.today(), datetime.min.time())

    if isinstance(end, int):
        end = start + timedelta(days=end)

    if freq == 'MS':
        if start.month <= 1:
            start = start.replace(month=12, year=start.year-1)
        else:
            start = start.replace(month=start.month-1)
        if day_offset > 0:
            day_offset -= 1

    try:
        res = pd.date_range(start=start, end=end, freq=freq)
    except Exception as e:
        raise

    if day_offset is not None:
        res += timedelta(days=day_offset)
    return res


def month_range_day(start: datetime, periods: int, num: int = 1):
    return pd.DatetimeIndex(
        data=[(dt.replace(day=start.day) if dt.day > start.day else dt)
                for dt in pd.date_range(start=start, periods=periods, freq=f'{num}M')]
    )
