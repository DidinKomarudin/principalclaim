from datetime import datetime

from dateutil.relativedelta import relativedelta
from odoo import tools
from odoo import models, fields, api


class ClaimMonitoring(models.Model):
    _name = 'bsp.claim.monitoring'
    _auto = False
    _rec_name = 'claim_id'
    _description = 'Claim Monitoring view'

    @api.depends('claim_id')
    def _compute_claim_desc(self):
        for record in self:
            record.claim_desc = record.claim_id.name +" - " +  record.claim_id.principal_code

    @api.depends('claim_date')
    def _compute_claim_age(self):
        currentDate = datetime.now()
        for record in self:
            record.claim_age = ''
            initial_aging_date = record.claim_date

            if initial_aging_date:
                rd = relativedelta(currentDate, initial_aging_date)
                record.claim_age = '{0:d} years, {1:d}  months, {2:d}  days, {3:d}  hours'.format(rd.years, rd.months,
                                                                                                  rd.days, rd.hours)

    claim_id = fields.Many2one(
        'bsp.claim.principal', string='Claim Number', readonly=True)
    claim_desc = fields.Char(compute="_compute_claim_desc", string="Claim")
    cn_id = fields.Many2one(
        'bsp.creditnote.other', string='CN Number', readonly=True)
    cn_total = fields.Float(string='CN Amount', readonly=True)
    alloc_total = fields.Float(string='Alloc Amount', readonly=True)
    withdraw_total = fields.Float(string='WithDraw Amount', readonly=True)
    # alloc_id = fields.Many2one(
    #     'bsp.creditnote.alloc', string='Allocation Number', readonly=True)
    refund_id = fields.Many2one(
        'account.invoice', string='Refund', readonly=True)
    refund_total = fields.Float(string='Refund Amount', readonly=True)
    balance_total = fields.Float(string='Payment Balance', readonly=True)
    pay_id = fields.Many2one(
        'account.payment', string='Payment', readonly=True)
    pay_total = fields.Float(string='Payment Amount', readonly=True)
    branch = fields.Char('Branch', size=4, readonly=True)
    principal = fields.Char('Principal', size = 5, readonly=True)
    claim_date = fields.Date('Claim Date', readonly=True)
    state = fields.Selection(
        [('current', 'CURRENT'),
         ('pending', 'PENDING'),
         ('post', 'POST'),
         ('paid', 'PAID'),
         ('cancel', 'CANCEL')],
        string='Claim Status', readonly=True)
    claim_age = fields.Char("Aging by Claim Date", compute="_compute_claim_age")



    @api.model_cr
    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            """CREATE or REPLACE VIEW %s as (
            SELECT  row_number() OVER (PARTITION BY true) AS id,
                claim_id AS claim_id,
				case when type = 'CN' then ref_id else null end as cn_id,
				case when type = 'CN' then total_amount else 0 end as cn_total,
				case when type = 'CN' then total_alloc else 0 end as alloc_total,
				case when type = 'CN' then total_withdraw else 0 end as withdraw_total,
				case when type = 'RF' then ref_id else null end as refund_id,
				case when type = 'RF' then total_amount else 0 end as refund_total,
				case when type = 'RF' then (coalesce(total_amount,0) - coalesce(total_alloc,0)) else 0 end as balance_total,
				case when type = 'PY' then ref_id else null end as pay_id,
				case when type = 'PY' then total_amount else 0 end as pay_total,
				branch as branch,  
                principal as principal,            
                claim_date as claim_date,                
                state                         
            FROM  (SELECT claim.id AS claim_id,
                   claim.branch_code as branch,
			       claim.principal_code as principal,            
                   claim.claim_date as claim_date,
                   cn.id AS ref_id,
                   cn.cn_total AS total_amount,
				   (select sum(allocation_amount) from bsp_creditnote_alloc where allocation_type='AL' and cn_id=cn.id) total_alloc,
				   (select sum(allocation_amount) from bsp_creditnote_alloc where allocation_type='PC' and cn_id=cn.id) total_withdraw,
                   claim.state as state,
				   'CN' as type
            FROM bsp_claim_principal AS claim 
            JOIN bsp_creditnote_other AS cn ON claim.id = cn.claim_id
			union all
			SELECT claim.id AS claim_id,
			       claim.branch_code as branch,
			       claim.principal_code as principal,            
                   claim.claim_date as claim_date,
                   refund.id AS ref_id,
                   refund.amount_total AS total_amount,
				   (select sum(pay.amount) from  account_invoice_payment_rel rel 
							join account_payment pay on rel.payment_id = pay.id where rel.invoice_id=refund.id) total_alloc,
				   0 total_withdraw,
                   claim.state as state,
				   'RF' as type				  
            FROM bsp_claim_principal AS claim 
            join account_invoice AS refund ON claim.id = refund.claim_id
			union all
			SELECT claim.id AS claim_id,
			       claim.branch_code as branch,
			       claim.principal_code as principal,            
                   claim.claim_date as claim_date,
                   pay.id AS ref_id,
                   pay.amount AS total_amount,
				   0 total_alloc,
				   0 total_withdraw,
                   claim.state as state,
				   'PY' as type				  
            FROM bsp_claim_principal AS claim 
            join account_invoice AS refund ON claim.id = refund.claim_id
			join account_invoice_payment_rel rel on rel.invoice_id = refund.id
			join account_payment pay on rel.payment_id = pay.id) as xx
			order by claim_id,cn_id,refund_id
            )"""
            % (self._table)
        )
