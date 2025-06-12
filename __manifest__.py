# -*- coding: utf-8 -*-
{
    'name': "Custom Odoo 18 HR module",

    'summary': "Custom Odoo 18 HR module",

    'description': """
Long description of module's purpose
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'hr', 'web', 'mail'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/hr_employee_views.xml',
        'views/res_config_settings.xml',
        'views/hr_onboarding_report_views.xml',
        'views/hr_onboarding_report_menu.xml',
        'views/custom_tabs_and_fields.xml',
        'views/cron_jobs.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'custom_hr_module/static/src/js/hr_onboarding_report.js',
            'custom_hr_module/static/src/css/hr_onboarding_report.css',
            'custom_hr_module/static/src/xml/hr_onboarding_report.xml',
            'https://cdn.jsdelivr.net/npm/chart.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
