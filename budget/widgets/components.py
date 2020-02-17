import ipywidgets as widgets

def freq_dropdown():
    return widgets.Dropdown(
    options=[
        'Y',
        'MS',
        'M',
        '2W-FRI',
        '10D',
        'W-WED',
        '4D',
    ],
    layout={'width': '80px'}
)
