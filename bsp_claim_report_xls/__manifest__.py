# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) 2019 BSP,LLC <info@grimmette.com>

{
    'name': 'Claim Recapitulation Report (XLSX)',
    'version': '1.0.0',
    'category': 'Extra Tools',
    'summary': 'Claim Recapitulation Report (XLSX)',
    'price': 0.00,
    'currency': 'IDR',
    "license": "OPL-1",     
    'description': """
Claim Recapitulation Report.
====================================
Claim Recapitulation Report in MS Excel format (XLSX)
Generate the Excel Report from a Template.
Report for Report Designer (XLSX, XLSM) """,
    'author': 'DK',
    'support': 'info@binasanprima.com',
    'depends': ['bsp_claim', 'account'],
    'images': ['static/description/banner_rep.png'],
    'data': ['data/claim_recap.xml',],
    'qweb': [],
    'demo': [],
    'installable': True,
    'auto_install': False,
    "pre_init_hook": "pre_init_check",
}



