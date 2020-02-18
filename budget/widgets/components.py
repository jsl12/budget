import ipywidgets as widgets

def freq_dropdown(**kwargs):
    return widgets.Dropdown(
    options=[
        'Y',
        'MS',
        'M',
        '2W-FRI',
        '10D',
        'W',
        'W-FRI',
        'W-WED',
        '4D',
        None
    ],
    layout={'width': '80px'},
    **kwargs
)
