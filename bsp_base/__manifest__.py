# -*- coding: utf-8 -*-
{
    'name': "BSP Base",

    'summary': """
        Base module for WMS PT Bina San Prima
    """,

    'description': """
        Modul ini digunakan untuk custom modul base dan menyimpan function/method yang akan sering digunakan di modul lain
    """,

    'author': "Miftah",
    'website': "http://gitlab.binasanprima.com/miftah/wms",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Base',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': [
        'base',
        'uom',
        'decimal_precision',
        'product',
        'stock',
        # 'stock_storage_type_extended'
    ],

    # always loaded
    'data': [
        'views/ir_module_module_view.xml',
        'views/ir_config_parameter_view.xml',
        'views/res_partner_views.xml',
        'views/uom_uom_views.xml',
        'wizard/base_wizard.xml',
        'wizard/base_confirmation_wizard.xml',
        'data/decimal_precision.xml',
        'data/ir_config_parameter.xml',
        'data/ir_cron.xml',
        'views/res_users_view.xml',
        'views/res_groups_view.xml',
        'views/fields_view.xml',
        'views/res_config_settings_view.xml'
    ],
    # only loaded in demonstration mode
    'demo': [
        # 'demo/demo.xml',
    ],
}