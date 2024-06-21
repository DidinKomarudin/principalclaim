# -*- coding: utf-8 -*-
{
    'name': "CLAIM Base API Configuration",

    'summary': """
        API configuration to sync with other system
    """,

    'description': """
        
    """,

    'author': "Miftah",
    'website': "http://gitlab.binasanprima.com/miftah/wms",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Claim Configuration',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': [
        'base',
        'bsp_claim_base',
        'operating_unit',
        'operating_unit_extend',
    ],

    # always loaded
    'data': [
        'views/operating_unit_view.xml',
    ],
    # only loaded in demonstration mode
    'demo': [

    ],
}