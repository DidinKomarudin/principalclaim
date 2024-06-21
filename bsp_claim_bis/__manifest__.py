# -*- coding: utf-8 -*-
{
    'name': "BIS CN Import",

    'summary': """
        Synch Creditnote/KL/faktur principal/offset between BIS and odoo
    """,

    'description': """
        Synch Creditnote/KL/faktur principal/offset between BIS and odoo
    """,

    'author': "Didin",
    'website': "http://gitlab.binasanprima.com/miftah/wms",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Claim',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': [
        'base_claim_api',
        'bsp_claim',
    ],

    # always loaded
    'data': [
        'views/claim_bis_synch_views.xml',
        'views/pv_synch_views.xml',
        'data/ir_cron.xml',
        'data/payment_voucher_synch.xml',
        'security/ir.model.access.csv',

    ],
    'installable': True,
    'auto_install': False
}