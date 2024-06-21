{
    'name': 'BSP Principal Claim Reports',
    'version': '12.0.2.0.0',
    'development_status': "Ready for LIVE!",
    'category': 'AR Claim',
    'summary': "BSP Principal Claim Reports",
    'author': 'didin.komarudin@gmail.com',
    'website': '',
    'license': 'AGPL-3',
    'depends': [
        'bsp_claim',
        'report_xlsx_helper',
    ],
    'data': [
        'data/paper_format.xml',
        'data/report_data.xml',
        'reports/budget_card_report.xml',
        'reports/aging_claim_report.xml',
        'reports/cl_recap_report.xml',
        'reports/claim_journal_report.xml',
        'reports/claim_monitoring_report.xml',
        'reports/claim_bmbk_report.xml',
        'reports/bmbk_allocation_report.xml',
        'wizards/budget_card_report_wizard_view.xml',
        'reports/claim_balance_report.xml',
    ],
    'installable': True,
    'auto_install': False
}
