{
    'name': 'Task Timer',
    'version': '16.0.1.0.0',
    'category': 'Productivity',
    'summary': 'Track time spent on tasks',
    'sequence': 1,
    'author': 'Your Name',
    'website': 'https://www.yourwebsite.com',
    'depends': ['web'],
    'data': [
        'security/ir.model.access.csv',
        'views/task_views.xml',
        'views/timer_menus.xml',
        
    ],
    'assets': {
        'web.assets_backend': [
            'task_timer/static/src/components/timer/timer.js',
            'task_timer/static/src/components/timer/timer.xml',
            'task_timer/static/src/components/timer/timer.scss',
            'task_timer/static/src/components/task_list/task_list.js',
            'task_timer/static/src/components/task_list/task_list.xml',
            'task_timer/static/src/components/task_form/task_form.js',
            'task_timer/static/src/components/task_form/task_form.xml',
            'task_timer/static/src/components/timer_dashboard/timer_dashboard.js',
            'task_timer/static/src/components/timer_dashboard/timer_dashboard.xml',
            'task_timer/static/src/components/task_timer_widget/task_timer_widget.js',
            'task_timer/static/src/components/task_timer_widget/task_timer_widget.xml',
        ],
    },
    'application': True,
    'installable': True,
    'license': 'LGPL-3',
}