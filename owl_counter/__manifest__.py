{
    'name': 'Owl Counter',
    'version': '16.0.1.0.0',
    'category': 'Tools',
    'summary': 'A simple counter implementation using Owl',
    'sequence': 1,
    'author': 'Your Name',
    'website': 'https://www.yourwebsite.com',
    'depends': ['web'],  # We only need web since we're not using models
    'data': [
        'views/counter_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'owl_counter/static/src/components/counter/counter.js',
            'owl_counter/static/src/components/counter/counter.xml',
            'owl_counter/static/src/components/counter/counter.scss',
            'owl_counter/static/src/components/counter_page.js',
            'owl_counter/static/src/components/counter_page.xml',
        ],
    },
    'application': True,
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}