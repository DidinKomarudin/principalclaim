from odoo import tools
from odoo import api, fields, models


class ClaimReport(models.Model):
    _name = "claim.analysis"
    _description = "Claim Analysis Report"
    _auto = False
    _rec_name = 'coll_date'
    _order = 'coll_date desc'

    # @api.model
    # def _get_done_states(self):
    #     return ['sale', 'done', 'paid']
    def get_types(self):
        types = self.env['bsp.claim.type'].search([])
        lst = []
        for tp in types:
            lst.append((tp.code, tp.name))
        return lst

    claim_type = fields.Selection(selection='get_types', string='Claim Type', readonly=True)
    # claim_type = fields.Selection(
    #     [('cncl', 'CNCL'),
    #      ('discount', 'Discount'),
    #      ('barang', 'Barang'),
    #      ('salary', 'Salary Salesman'),
    #      ('cabang', 'USMUB/Insentif'),
    #      ('manual', 'Manual OPU')],
    #     string='Claim Type', readonly=True)
    claimcl_id = fields.Many2one('bsp.claim.cl', 'Claim Coll Number', readonly=True)
    # claim_id = fields.Many2one('bsp.creditnote.other', 'Claim Reference', readonly=True)
    # branch = fields.Char("Branch", readonly=True)
    branch_id = fields.Many2one('operating.unit', 'Branch', readonly=True)
    partner_id = fields.Many2one('res.partner', 'Principal', readonly=True)
    coll_date = fields.Date("Claim Coll.Date", readonly=True)
    claim_amount = fields.Float("Claim Amount", readonly=True)
    ppn_amount = fields.Float("PPN Amount", readonly=True)
    pph1_amount = fields.Float("PPH Amount", readonly=True)
    discount_amount = fields.Float("Share Principal Amount", readonly=True)
    net_amount = fields.Float("NET Amount", readonly=True)
    realization_amount = fields.Float("Realisasi Amount", readonly=True)
    correction_amount = fields.Float("Correction Amount", readonly=True)
    balance_amount = fields.Float('Balance Amount', readonly=True)
    invoice_ids = fields.One2many('account.invoice', compute='_get_invoice',search='_invoice_search',string="Payment Vouchers")
    # @api.depends('claimcl_id')
    def _get_invoice(self):
       for claim in self:
           query = f""" select ai.id invoice_id
                     from account_invoice ai 
                     join account_invoice_line ail on ai.id=ail.invoice_id 
                     join bsp_claim_cl cl on cl.id=ail.claimcl_id 
                     where cl.id = {claim.claimcl_id}"""

           self._cr.execute(query)
           records = self._cr.fetchall()
           if not records:
               continue
           invoices = self.env['account.invoice']
           for invid in records:
               invoices = self.env['account.invoice'].browse(invid[0])
               invoices |= invoices
           claim.invoice_ids = invoices

    @api.multi
    def _invoice_search(self, operator, operand):
        query = f""" select cl.id claimcl_id
                                            from account_invoice ai 
                                            join account_invoice_line ail on ai.id=ail.invoice_id 
                                            join bsp_claim_cl cl on cl.id=ail.claimcl_id 
                                            where ai.number like '%{operand.upper()}%'"""

        self._cr.execute(query)
        records = self._cr.fetchall()
        return [('claimcl_id', 'in', [p[0] for p in records])]

    @api.model_cr
    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            """CREATE or REPLACE VIEW %s as (
            SELECT
                row_number() OVER (PARTITION BY true) AS id,
                col.claim_type,
                col.operating_unit_id As branch_id,                            
                col.partner_id AS partner_id,  
                col.id AS claimcl_id,                  
                col.claim_date As coll_date,
                col.claim_amount,
                col.tax_amount AS tax_amount,
                col.pph1_amount,
                col.discount_amount,
                col.net_amount AS net_amount, 
                col.realization_amount,
                col.correction_amount,
                col.net_amount -col.realization_amount-col.correction_amount AS balance_amount 
            FROM bsp_claim_cl col 
            )"""
            % (self._table)
        )
