from odoo import fields, models, api


class Company(models.Model):
    _inherit = 'res.company'

    bank_account_id = fields.Many2one('account.account', string='Bank Account', domain=[('deprecated', '=', False)])
    claim_prepaid_account_id = fields.Many2one('account.account', string='Prepaid Claim Account', domain=[('deprecated', '=', False)])
    ump_account_id = fields.Many2one('account.account', string='UMP Account', domain=[('deprecated', '=', False)])
    ar_account_id = fields.Many2one('account.account', string='AR Account', domain=[('deprecated', '=', False)])
    ar_claim_account_id = fields.Many2one('account.account', string='AR Claim Account', domain=[('deprecated', '=', False)])
    operation_exp_account_id = fields.Many2one('account.account', string='Operational Expense Account', domain=[('deprecated', '=', False)])
    ppn_account_id = fields.Many2one('account.account', string='PPN Account', domain=[('deprecated', '=', False)])
    claim_income_account_id = fields.Many2one('account.account', string='Claim Income Account', domain=[('deprecated', '=', False)])
    pph_prepaid_account_id = fields.Many2one('account.account', string='Prepaid PPh Account', domain=[('deprecated', '=', False)])
    sub_claim_account_id = fields.Many2one('account.account', string='Sub Prepaid Claim Account', domain=[('deprecated', '=', False)])
    add_claim_account_id = fields.Many2one('account.account', string='Add Prepaid Claim Account',
                                           domain=[('deprecated', '=', False)])
    inv_claim_account_id = fields.Many2one('account.account', string='Invoice Prepaid Claim Account',
                                           domain=[('deprecated', '=', False)])