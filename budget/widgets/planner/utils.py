periods = {
    'Y': 'year',
    'M': 'month',
    'W': 'week',
    'D': 'day'
}

days = {
    'MON': 'Monday',
    'TUE': 'Tuesday',
    'WED': 'Wednesday',
    'THU': 'Thursday',
    'FRI': 'Friday',
    'SAT': 'Saturday',
    'SUN': 'Sunday'
}

def format_text(amount, recur, mult=None, compile=None, c_mult=None, date=None):
    suffix = ''
    if date is not None:
        suffix = f'once, on {date.strftime("%Y-%m-%d")}'
    elif recur is not None:
        for k, p in periods.items():
            if k in recur:
                period = p
                break
        else:
            period = 'NONE'

        if mult is None:
            suffix = f'every {period}'
        else:
            suffix = f'every {mult} {period}s'

        if compile is not None:
            for k, p in periods.items():
                if k in compile:
                    period = p
                    break

            if c_mult is None:
                if 'Y' in compile:
                    c_period = ', on the last day of the year'
                elif 'MS' in compile:
                    c_period = ', on the first day of the month'
                elif 'M' in compile:
                    c_period = ', on the last day of the month'
                elif 'W' in compile:
                    if '-' in compile:
                        c_period = f', weekly on {days[compile[-3:]]}'
                    else:
                        c_period = f', every week'
            else:
                c_period = f', every {c_mult} {period}s'
                if 'Y' in compile:
                    c_period += f' on the last day of the year'
                elif 'MS' in compile:
                    c_period += f' on the first day of the month'
                elif 'M' in compile:
                    c_period += f' on the last day of the month'
                elif 'W' in compile:
                    if '-' in compile:
                        c_period += f' on {days[compile[-3:]]}'
                    else:
                        c_period += f' on Sunday'

            suffix += c_period

    if recur is not None:
        prefix = 'Rate of '
    else:
        prefix = ''
    return f'{prefix}${amount:.02f} {suffix}'