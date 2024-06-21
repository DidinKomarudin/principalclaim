from odoo import  api, fields, models, _
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

class ClaimToPrincipal(models.Model):
    _name = 'bsp.claim.principal'
    _description = "Claim Principal from BSP"

    @api.depends('invoice_ids')
    def _compute_invoice(self):
        for record in self:
            record.invoice_count = len(record.invoice_ids)

    @api.depends('claim_date')
    def _compute_claim_age(self):
        currentDate = datetime.now()
        for record in self:
            record.claim_age = ''
            initial_aging_date = record.claim_date

            if initial_aging_date:
                rd = relativedelta(currentDate, initial_aging_date)
                record.claim_age = '{0:d} years, {1:d}  months, {2:d}  days, {3:d}  hours'.format(rd.years, rd.months, rd.days, rd.hours)

    @api.depends('remark')
    def _compute_program(self):
        for record in self:
            st = str(record.remark)
            record.program = st.split()[0] + '...'

    # @api.depends('branch_code')
    # def _compute_get_operating_unit_id(self):
    #     for record in self:
    #         operating_unit_id = self.env['operating.unit'].search([('code', '=', record.branch_code)], limit=1)
    #         record.operating_unit_id = operating_unit_id.id

    name = fields.Char("KX No.", size=30)
    empty = fields.Char(string="empty", size=4)
    claim_date = fields.Date("KX Date")
    state = fields.Selection(
                  [('current', 'CURRENT'),
                   ('pending', 'PENDING'),
                   ('post', 'POST'),
                   ('paid', 'PAID'),
                   ('cancel', 'CANCEL')],
        string='Status', default='current')
    branch_code = fields.Char("Branch", size=4)
    principal_code = fields.Char("Principal", size=4)
    # operating_unit_id = fields.Integer("ID", compute="_compute_get_operating_unit_id", store=True)
    isclaim_in_budget = fields.Boolean("In budget")
    remark = fields.Char("Program")
    program = fields.Char("Program", compute='_compute_program')
    customer_ref = fields.Char("Outlet Ref.", size=30,oldname="outlet_reference")
    claim_letter = fields.Char("Claim letter", size=30)
    claim_amount = fields.Float("Claim amount")
    realization_amount = fields.Float("Realization")
    exim_status = fields.Char("Exim status", size=3)
    cn_ids = fields.One2many('bsp.creditnote.other', 'claim_id', string="Credit Notes")
    invoice_ids = fields.One2many('account.invoice', 'claim_id', string="Claim Items", readonly=True,
                                    copy=False)
    invoice_count = fields.Integer(compute="_compute_invoice", string='Bill Count', copy=False, default=0, store=True)
    payment_term_id = fields.Many2one(
        'account.payment.term', string='Payment Terms', readonly=True,
        states={'current': [('readonly', False)]})
    tax_id = fields.Many2one('account.tax', string='PPN', ondelete='restrict')
    pending_date = fields.Date("Pending Date", readonly=True)
    post_date = fields.Date("Post Date", readonly=True)
    paid_date = fields.Date("Paid Date", readonly=True)
    claim_age = fields.Char("Aging by Claim Date", compute="_compute_claim_age")
    cc_id = fields.Many2one('bsp.claim.cl', 'CC No')

    def action_invoice_in_refund(self):
        action = self.env.ref('account.action_invoice_in_refund')
        result = action.read()[0]
        result['domain'] = [('claim_id', '=', self.id)]
        return result


    @api.multi
    def write(self, vals):
        result = super(ClaimToPrincipal, self).write(vals)
        return result

    @api.multi
    def button_draft(self):
        return self.write({'state': 'current'})

    @api.multi
    def button_pending(self):
        return self.write({'state': 'pending'})

    @api.multi
    def button_post(self):
        return self.write({'state': 'post'})

    @api.multi
    def button_cancel(self):
        return self.write({'state': 'cancel'})


    @api.model
    def _common_action_keys(self):
        """ Call it in your own child module
        """
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'bsp.creditnote.other',
            'target': 'current',
            'context': {'parent_id': self.id, 'parent_model': self._name},
            'view_mode': 'tree',
        }



    @api.multi
    def button_paid(self):
        data_final = []

        product_name = 'CN Customer for Principal: ' + self.principal_code
        partner_id = self.env['res.partner'].search([('ref', '=', self.principal_code)], limit=1)
        product_id = self.env['product.product'].search([('name', '=', product_name)], limit=1)
        journal_id = self.env['account.invoice'].with_context(type='in_refund')._default_journal()
        account_id = self.env['account.invoice.line'].with_context(journal_id=journal_id.id)._default_account()
        if not product_id:
            product_id = self.env['product.product'].create({
                'name': product_name,
                'type': 'service',
            })

        for line in self.cn_ids:
            invoice_line_vals = (0, 0, {
                'product_id': product_id.id,
                'name': product_id.name + ': ' + line.name,
                'quantity': 1,
                'account_id': account_id,
                'price_unit': line.cn_total,
                # 'invoice_line_tax_ids': [(6, 0, line.taxes_id.ids)],
            })
            data_final.append(invoice_line_vals)

        vendor_bills_id = self.env['account.invoice'].create({
            'type': 'in_refund',
            'claim_id': self.id,
            'move_name': self.name,
            'date': self.claim_date,
            'date_invoice': date.today(),
            'date_due': date.today() + relativedelta(days=10),
            'partner_id': partner_id.id,
            'company_id': self.env.user.company_id.id,
            'journal_id': journal_id.id,
            # 'account_id': account_id.id,
            'invoice_line_ids': data_final,
            'amount_total': self.claim_amount,
        })

        if vendor_bills_id:
            self.write({'state': 'paid'})

        result = self.action_invoice_in_refund()
        return result





