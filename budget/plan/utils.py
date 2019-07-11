import re
from datetime import datetime

import pandas as pd


def compare(df: pd.DataFrame, daily_spending: float) -> pd.DataFrame:
    df['Total'] = df['Amount'].cumsum()
    df['Planned'] = df.apply(lambda r: round((r.name - df.index[0]).days * daily_spending, 2), axis=1)
    df['Difference'] = df['Total'] - df['Planned']
    return df


def parse_date(input: str) -> datetime:
    patterns = [
        '%Y-%m-%d',
        '%m/%d/%Y',
        '%m/%d',
        '%m-%d'
    ]
    for p in patterns:
        try:
            res = datetime.strptime(input, p)
            if res.year < 2000:
                res = res.replace(year=datetime.today().year)
        except ValueError:
            pass
        else:
            return res
    raise ValueError(f'input \'{input}\' does not match any patterns')


def date_range(start: datetime, end: datetime, freq: str) -> pd.DatetimeIndex:
    m = re.match('^(?P<num>\d+)(?P<unit>[MWY])$', freq.upper())
    if m is None:
        try:
            return pd.date_range(
                start=start,
                end=end,
                freq=freq
            )
        except:
            raise ValueError(f'invalid freq: {freq}')
    elif m.group('unit') == 'Y':
        return month_range_day(
            start=start,
            periods=int((end - start).days / 365)+1,
            num=int(m.group('num'))*12
        )
    elif m.group('unit') == 'M':
        return month_range_day(
            start=start,
            periods=int((end - start).days / 30)+1,
            num=int(m.group('num'))
        )
    elif m.group('unit') == 'W':
        return pd.date_range(
            start=start,
            end=end,
            freq=f'{int(m.group("num"))*7}D'
        )


def month_range_day(start: datetime, periods: int, num: int = 1):
    return pd.DatetimeIndex(
        data=[(dt.replace(day=start.day) if dt.day > start.day else dt)
                for dt in pd.date_range(start=start, periods=periods, freq=f'{num}M')]
    )
