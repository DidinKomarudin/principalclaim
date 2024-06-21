from datetime import datetime

from dateutil.relativedelta import relativedelta
from odoo import tools
from odoo import models, fields, api


class ClaimCLMonitoring(models.Model):
    _name = 'bsp.claim.cl.monitoring'
    _auto = False
    _rec_name = 'claim_id'
    _description = 'Claim Monitoring view'

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

    def get_types(self):
        types = self.env['bsp.claim.type'].search([])
        lst = []
        for tp in types:
            lst.append((tp.code, tp.name))
        return lst

    claim_type = fields.Selection(selection='get_types', string='Claim Type')

    # claim_type = fields.Selection(
    #     [('cncl', 'CNCL'),
    #      ('discount', 'Discount'),
    #      ('barang', 'Barang'),
    #      ('salary', 'Salary Salesman'),
    #      ('cabang', 'USMUB/Insentif'),
    #      ('manual', 'Manual OPU')],
    #     string='Claim Type', readonly=True)
    claim_id = fields.Many2one(
        'bsp.claim.cl', string='CC Number', readonly=True)
    claim_desc = fields.Char(compute="_compute_claim_desc", string="Claim")
    cn_id = fields.Many2one(
        'bsp.creditnote.other', string='CL Number', readonly=True)
    customer_code = fields.Char(related="cn_id.customer_code", string="Customer Code")
    cn_total = fields.Float(string='CL Amount', readonly=True)
    alloc_total = fields.Float(string='Alloc Amount', readonly=True)
    withdraw_total = fields.Float(string='WithDraw Amount', readonly=True)
    paid_total = fields.Float(string='Paid Amount', readonly=True)
    # alloc_id = fields.Many2one(
    #     'bsp.creditnote.alloc', string='Allocation Number', readonly=True)
    refund_id = fields.Many2one(
        'account.invoice', string='Refund', readonly=True)
    refund_total = fields.Float(string='Claim Amount', readonly=True)
    balance_total = fields.Float(string='Payment Balance', readonly=True)
    # pay_id = fields.Many2one(
    #     'account.payment', string='Payment', readonly=True)
    pay_total = fields.Float(string='Payment Amount', readonly=True)
    branch = fields.Many2one(
        'operating.unit', string='branch', readonly=True)
    principal = fields.Many2one(
        'res.partner', domain="[('supplier','=',True)]", string='principal', readonly=True)
    claim_date = fields.Date('Claim Date', readonly=True)
    receive_date = fields.Date('Receive Date', readonly=True)
    send_date = fields.Date('Send Date', readonly=True)
    paid_date = fields.Datetime('Paid Date', readonly=True)
    state = fields.Selection(
        [('draft', 'DRAFT'),
         ('pending', 'PENDING'),
         ('post', 'POST'),
         ('paid', 'PAID'),
         ('done', 'DONE'),
         ('reject', 'REJECTED'),
         ('cancel', 'CANCELED')],
        string='Claim Status', readonly=True)
    claim_age = fields.Char("Aging", compute="_compute_claim_age")



    @api.model_cr
    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            """CREATE or REPLACE VIEW %s as (
            SELECT  row_number() OVER (PARTITION BY true) AS id,claim_type,
                claim_id AS claim_id,
				case when type = 'CN' then ref_id else null end as cn_id,
				case when type = 'CN' then total_amount else 0 end as cn_total,
				case when type = 'CN' then total_alloc else 0 end as alloc_total,
				case when type = 'CN' then total_withdraw else 0 end as withdraw_total,
				case when type = 'CN' then total_paid else 0 end as paid_total,
				case when type = 'RF' then ref_id else null end as refund_id,
				case when type = 'RF' then total_amount else 0 end as refund_total,
				case when type = 'RF' then (coalesce(total_amount,0) - coalesce(total_alloc,0)) else 0 end as balance_total,
				case when type = 'RF' then total_alloc else 0 end as pay_total,
				branch as branch,  
                principal as principal,            
                claim_date as claim_date,
                receive_date,
                send_date,  
                paid_date,              
                state                         
            FROM  
            (
            SELECT  claim.claim_type,
                    claim.id AS claim_id,
                   claim.operating_unit_id as branch,
			       claim.partner_id as principal,            
                   claim.claim_date as claim_date,
                   claim.receive_date,
                   claim.send_date, 
                   claim.paid_date, 
                   cn.cn_id AS ref_id,
                   cn.actual_claim_amount AS total_amount,
				   (select sum(allocation_amount) from bsp_creditnote_alloc where allocation_type='AL' and cn_id=cn.id) total_alloc,
				   (select sum(allocation_amount) from bsp_creditnote_alloc where allocation_type='PC' and cn_id=cn.id) total_withdraw,
                   cn.paid_total AS total_paid,
                   claim.state as state,
				   'CN' as type
            FROM bsp_claim_cl AS claim 
            LEFT JOIN bsp_claim_cl_line AS cn ON claim.id = cn.claimcl_id
			union all
			SELECT claim.claim_type,
			       claim.id AS claim_id,
			       claim.operating_unit_id as branch,
			       claim.partner_id as principal,            
                   claim.claim_date as claim_date,
                   claim.receive_date,
                   claim.send_date,
                   claim.paid_date, 
                   refund.id AS ref_id,
                   claim.claim_amount AS total_amount,
                   claim.realization_amount AS total_alloc,
				   0 AS total_withdraw,
				   0 AS total_paid,
                   claim.state as state,
				   'RF' as type				  
            FROM bsp_claim_cl AS claim 
            LEFT JOIN account_invoice AS refund ON claim.invoice_id = refund.id) as xx
			order by claim_id,cn_id,refund_id
            )"""
            % (self._table)
        )
