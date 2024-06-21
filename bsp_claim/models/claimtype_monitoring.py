from datetime import datetime

from dateutil.relativedelta import relativedelta
from odoo import tools
from odoo import models, fields, api


class ClaimTypeMonitoring(models.Model):
    _name = 'bsp.claim.type.monitoring'
    _auto = False
    _rec_name = 'claim_id'
    _description = 'Claim Monitoring by Type view'

    @api.depends('claim_id')
    def _compute_claim_desc(self):
        for record in self:
            record.claim_desc = record.claim_id.name + " - " + record.claim_id.partner_id.ref

    @api.depends('send_date', 'paid_date')
    def _compute_claim_age(self):
        currentDate = datetime.now().date()
        for record in self:
            if record.paid_date:
                currentDate = record.paid_date.date()
            record.claim_age = ''
            initial_aging_date = record.send_date

            if initial_aging_date:
                dy = (currentDate - initial_aging_date).days
                # dy = (currentDate - datetime(initial_aging_date)).days
                # rd = relativedelta(currentDate, initial_aging_date)
                # record.claim_age = '{0:d} years, {1:d}  months, {2:d}  days, {3:d}  hours'.format(rd.years, rd.months,
                #                                                                                   rd.days, rd.hours)
                record.claim_age = '{0:d} days'.format(dy)

    claim_type = fields.Selection(
        [('cncl', 'CNCL'),
         ('discount', 'Discount'),
         ('barang', 'Barang'),
         ('salary', 'Salary Salesman'),
         ('cabang', 'USMUB/Insentif'),
         ('manual', 'Manual OPU')],
        string='Claim Type', readonly=True)
    claim_id = fields.Many2one(
        'bsp.claim.cl', string='Claim Number', readonly=True)
    branch = fields.Many2one(
        'operating.unit', string='branch', readonly=True)
    principal = fields.Many2one(
        'res.partner', domain="[('supplier','=',True)]", string='principal', readonly=True)
    claim_desc = fields.Char(compute="_compute_claim_desc", string="Claim")

    claim_total = fields.Float(string='Claim Amount', readonly=True)
    alloc_total = fields.Float(string='Realisasi Amount', readonly=True)
    unalloc_total = fields.Float(string='Unrealized Amount', readonly=True)
     # alloc_id = fields.Many2one(
    #     'bsp.creditnote.alloc', string='Allocation Number', readonly=True)
    refund_id = fields.Many2one(
        'account.invoice', string='Bill Number', readonly=True)
    refund_total = fields.Float(string='Billing Amount', readonly=True)
    balance_total = fields.Float(string='Total Balance', readonly=True)

    claim_date = fields.Date('Claim Date', readonly=True)
    receive_date = fields.Date('Receive Date', readonly=True)
    send_date = fields.Date('Send Date', readonly=True)
    paid_date = fields.Datetime('Paid Date', readonly=True)
    state = fields.Selection(
        [('current', 'CURRENT'),
         ('pending', 'PENDING'),
         ('incomplete', 'INCOMPLETE'),
         ('post', 'POST'),
         ('paid', 'PAID'),
         ('cancel', 'CANCEL')],
        string='Claim Status', readonly=True)
    claim_age = fields.Char("Aging", compute="_compute_claim_age")



    @api.model_cr
    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            """CREATE or REPLACE VIEW %s as (
            SELECT claim.id,
                   claim.claim_type,
			       claim.id AS claim_id,
			       claim.operating_unit_id as branch,
			       claim.partner_id as principal,            
                   claim.claim_date as claim_date,
                   claim.receive_date,
                   claim.send_date,
                   claim.paid_date,                    
                   claim.net_amount AS claim_total,
                   claim.realization_amount AS alloc_total,
                   claim.unrealized_amount AS unalloc_total,
                   refund.id AS refund_id,
                   (claim.realization_amount + claim.unrealized_amount) as refund_total,
                   claim.net_amount - (claim.realization_amount + claim.unrealized_amount) as balance_total,				   				   
                   claim.state as state	  
            FROM bsp_claim_cl AS claim 
            LEFT JOIN account_invoice AS refund ON claim.invoice_id = refund.id
			order by claim.operating_unit_id,claim.partner_id,claim_date,claim.claim_type
            )"""
            % (self._table)
        )
