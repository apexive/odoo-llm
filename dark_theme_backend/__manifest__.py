# -*- coding: utf-8 -*-

{
    "name": "Dark Mode Backend Theme",
    "description": """Minimalist and elegant backend theme for Odoo 16, Backend Theme, Theme""",
    "summary": "Dark Mode Backend Theme V16 is an attractive theme for backend",
    "category": "Themes/Backend",
    "version": "16.0.1.0.0",
    "author": "Apexive Solutions LLC",
    "website": "https://github.com/apexive/odoo-llm",
    "depends": ['base', 'web', 'mail'],
    "data": [
    ],
    'assets': {

        'web._assets_primary_variables': [
            ('after', 'web/static/src/scss/primary_variables.scss', 'dark_theme_backend/static/src/**/**/*.variables.scss'),
            ('before', 'web/static/src/scss/primary_variables.scss',
             'dark_theme_backend/static/src/scss/primary_variables.scss'),
        ],
        'web._assets_secondary_variables': [
            ('before', 'web/static/src/scss/secondary_variables.scss',
             'dark_theme_backend/static/src/scss/secondary_variables.scss'),
        ],
        'web._assets_backend_helpers': [
            ('before', 'web/static/src/scss/bootstrap_overridden.scss',
             'dark_theme_backend/static/src/scss/bootstrap_overridden.scss'),
        ],
        'web.assets_backend': [
                    'dark_theme_backend/static/src/js/color_scheme_menu_items.js',
                    'dark_theme_backend/static/src/js/color_scheme_service.js',
                    'dark_theme_backend/static/src/scss/domain_selector.dark.scss',
                    'dark_theme_backend/static/src/scss/datepicker.dark.scss',
                ],
        "web.dark_mode_variables": [
            # web._assets_primary_variables
            ('before', 'dark_theme_backend/static/src/scss/primary_variables.scss', 'dark_theme_backend/static/src/scss/primary_variables.dark.scss'),
             # web._assets_secondary_variables
            ('before', 'dark_theme_backend/static/src/scss/secondary_variables.scss', 'dark_theme_backend/static/src/scss/secondary_variables.dark.scss'),
        ],
        "web.dark_mode_assets_common": [
            ('include', 'web.dark_mode_variables'),
        ],
        "web.dark_mode_assets_backend": [
            ('include', 'web.dark_mode_variables'),
            # web._assets_backend_helpers
            ('before', 'dark_theme_backend/static/src/scss/bootstrap_overridden.scss', 'dark_theme_backend/static/src/scss/bootstrap_overridden.dark.scss'),
            ('after', 'web/static/lib/bootstrap/scss/_functions.scss', 'dark_theme_backend/static/src/scss/bs_functions_overridden.dark.scss'),
            # assets_backend
            'dark_theme_backend/static/src/**/**/*.dark.scss',
        ],
    },
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
