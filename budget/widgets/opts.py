qgrid_opts = {
    'grid_options': {
        'forceFitColumns': False,
        'autoHeight': False
    },
    'column_definitions': {
        'Date': {
            'minWidth': 80,
            'width': 80
        },
        'Amount': {
            'minWidth': 50,
            'width': 100
        },
        'Account': {
            'minWidth': 50,
            'width': 100
        },
        'Description': {
            'minWidth': 100,
            'width': 300
        },
        'Note': {
            'minWidth': 100,
            'width': 200
        },
        'Linked': {
            'minWidth': 100,
            'width': 200
        },
        'id': {
            'minWidth': 30,
            'width': 50
        },
        'Category': {
            'minWidth': 50,
            'width': 100
        }
    }
}
bar_layout = {
    'display': 'flex',
    'width': 'auto',
    'padding': '5px'
}
field_layout = {
    'display': 'flex',
    'flex': '1 1'
}